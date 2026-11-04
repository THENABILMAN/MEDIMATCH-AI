"""Booking rules, database integrity and timezone handling."""

import concurrent.futures
import uuid
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import psycopg2
import pytest
from conftest import STACK, create_mock_jwt
from psycopg2 import errors

from app.core.config import settings
from app.models.enums import UserRole
from app.run_migrations import apply_migrations
from app.search.recommend import _generate_safe_explanation

DOCTOR_USER = "a0000000-0000-0000-0000-000000000003"
DOCTOR_ID = "d0000000-0000-0000-0000-000000000000"


def sql(query: str, params: tuple = ()):
    conn = psycopg2.connect(STACK["DB_URL"])
    try:
        with conn, conn.cursor() as cur:
            cur.execute(query, params)
            return cur.fetchall() if cur.description else None
    finally:
        conn.close()


def headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def doctor_headers() -> dict:
    return headers(
        create_mock_jwt(DOCTOR_USER, "d@tests.invalid", UserRole.DOCTOR, "Dr. Tanvir Hasan")
    )


@pytest.fixture
def patient() -> dict:
    user_id = str(uuid.uuid4())
    return {
        "id": user_id,
        "headers": headers(create_mock_jwt(user_id, "p@tests.invalid", UserRole.PATIENT, "Pat")),
    }


def make_slot(days_ahead: float = 400, minutes: int = 30) -> str:
    """Far enough ahead to miss the demo slots, with a random offset to avoid overlaps."""
    start = datetime.now(UTC) + timedelta(days=days_ahead, minutes=uuid.uuid4().int % 500000)
    return str(
        sql(
            "INSERT INTO public.availability_slots (doctor_id, start_time, end_time) VALUES (%s, %s, %s) RETURNING id",
            (DOCTOR_ID, start, start + timedelta(minutes=minutes)),
        )[0][0]
    )


def book(client, who: dict, slot: str):
    return client.post("/appointments", headers=who["headers"], json={"slot_id": slot})


def backdate(appointment_id: str) -> None:
    past = datetime.now(UTC) - timedelta(hours=2)
    sql(
        "UPDATE public.appointments SET scheduled_start = %s, scheduled_end = %s WHERE id = %s",
        (past, past + timedelta(minutes=30), appointment_id),
    )


def test_cannot_complete_an_appointment_before_it_starts(client, doctor_headers, patient):
    appointment = book(client, patient, make_slot()).json()
    res = client.post(f"/appointments/{appointment['id']}/complete", headers=doctor_headers)
    assert res.status_code == 400


def test_cannot_complete_twice(client, doctor_headers, patient):
    appointment = book(client, patient, make_slot()).json()
    backdate(appointment["id"])
    url = f"/appointments/{appointment['id']}/complete"
    assert client.post(url, headers=doctor_headers).status_code == 200
    assert client.post(url, headers=doctor_headers).status_code == 400


def test_cannot_cancel_an_appointment_that_has_started(client, patient):
    appointment = book(client, patient, make_slot()).json()
    backdate(appointment["id"])
    res = client.post(
        f"/appointments/{appointment['id']}/cancel", headers=patient["headers"], json={}
    )
    assert res.status_code == 400


def test_stranger_learns_nothing_from_a_finished_appointment(client, doctor_headers, patient):
    appointment = book(client, patient, make_slot()).json()
    backdate(appointment["id"])
    client.post(f"/appointments/{appointment['id']}/complete", headers=doctor_headers)

    stranger = headers(
        create_mock_jwt(str(uuid.uuid4()), "s@tests.invalid", UserRole.PATIENT, "Str")
    )
    res = client.post(f"/appointments/{appointment['id']}/cancel", headers=stranger, json={})
    assert res.status_code == 403


def test_simultaneous_cancels_succeed_only_once(patient):
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    appointment = book(client, patient, make_slot()).json()
    url = f"/appointments/{appointment['id']}/cancel"
    with concurrent.futures.ThreadPoolExecutor(8) as pool:
        codes = list(
            pool.map(
                lambda _: client.post(url, headers=patient["headers"], json={}).status_code,
                range(8),
            )
        )
    assert codes.count(200) == 1
    assert set(codes) == {200, 400}


def test_cancel_frees_the_slot_for_rebooking(client, patient):
    slot = make_slot()
    appointment = book(client, patient, slot).json()
    client.post(f"/appointments/{appointment['id']}/cancel", headers=patient["headers"], json={})
    other = {
        "headers": headers(
            create_mock_jwt(str(uuid.uuid4()), "o@tests.invalid", UserRole.PATIENT, "O")
        )
    }
    assert book(client, other, slot).status_code == 201


def test_active_bookings_are_limited_per_patient(client, patient):
    codes = [
        book(client, patient, make_slot()).status_code
        for _ in range(settings.MAX_ACTIVE_BOOKINGS + 1)
    ]
    assert codes[:-1] == [201] * settings.MAX_ACTIVE_BOOKINGS
    assert codes[-1] == 409


def test_patient_cannot_hold_two_overlapping_appointments(client, patient):
    start = datetime.now(UTC) + timedelta(days=900, minutes=uuid.uuid4().int % 500000)
    ids = []
    for offset in (0, 10):
        begin = start + timedelta(minutes=offset)
        doctor = "d0000000-0000-0000-0000-000000000000" if offset == 0 else None
        if doctor is None:
            doctor = sql(
                """SELECT id FROM public.doctor_profiles
                   WHERE verification_status = 'approved' AND id <> %s LIMIT 1""",
                (DOCTOR_ID,),
            )[0][0]
        ids.append(
            str(
                sql(
                    "INSERT INTO public.availability_slots (doctor_id, start_time, end_time) VALUES (%s, %s, %s) RETURNING id",
                    (doctor, begin, begin + timedelta(minutes=30)),
                )[0][0]
            )
        )
    assert book(client, patient, ids[0]).status_code == 201
    assert book(client, patient, ids[1]).status_code == 409


def test_deleting_a_free_slot_keeps_past_appointment_times(client, doctor_headers, patient):
    slot = make_slot()
    appointment = book(client, patient, slot).json()
    start_time = appointment["start_time"]
    client.post(f"/appointments/{appointment['id']}/cancel", headers=patient["headers"], json={})
    assert client.delete(f"/doctors/me/slots/{slot}", headers=doctor_headers).status_code == 204

    listed = client.get("/appointments/me", headers=patient["headers"]).json()
    match = next(row for row in listed if row["id"] == appointment["id"])
    assert match["start_time"] == start_time


def test_naive_slot_times_are_refused(client, doctor_headers):
    start = (datetime.now(UTC) + timedelta(days=500)).replace(tzinfo=None)
    res = client.post(
        "/doctors/me/slots",
        headers=doctor_headers,
        json={
            "start_time": start.isoformat(),
            "end_time": (start + timedelta(minutes=30)).isoformat(),
        },
    )
    assert res.status_code == 422


def test_dhaka_offset_is_stored_as_the_same_instant(client, doctor_headers):
    dhaka = timezone(timedelta(hours=6))
    start = (datetime.now(dhaka) + timedelta(days=800, minutes=uuid.uuid4().int % 500000)).replace(
        microsecond=0
    )
    res = client.post(
        "/doctors/me/slots",
        headers=doctor_headers,
        json={
            "start_time": start.isoformat(),
            "end_time": (start + timedelta(minutes=30)).isoformat(),
        },
    )
    assert res.status_code == 201
    stored = datetime.fromisoformat(res.json()["start_time"].replace("Z", "+00:00"))
    assert stored == start


def test_patients_see_times_in_dhaka_not_utc():
    text = _generate_safe_explanation(
        ["Neurology"], "Dhaka", 10, 1000.0, "2030-01-01T18:30:00+00:00"
    )
    assert "UTC" not in text
    assert "Jan 02" in text and "12:30 AM" in text and "Dhaka time" in text


def test_short_slots_are_refused_by_the_database():
    start = datetime.now(UTC) + timedelta(days=1000, minutes=uuid.uuid4().int % 500000)
    with pytest.raises(errors.CheckViolation):
        sql(
            "INSERT INTO public.availability_slots (doctor_id, start_time, end_time) VALUES (%s, %s, %s)",
            (DOCTOR_ID, start, start + timedelta(minutes=5)),
        )


def test_audit_logs_cannot_be_changed_even_by_the_service_role():
    row = sql("INSERT INTO public.audit_logs (action, target_type) VALUES ('T', 't') RETURNING id")[
        0
    ][0]
    with pytest.raises(psycopg2.Error):
        sql("UPDATE public.audit_logs SET action = 'X' WHERE id = %s", (row,))
    with pytest.raises(psycopg2.Error):
        sql("DELETE FROM public.audit_logs WHERE id = %s", (row,))


def test_a_patient_with_appointments_cannot_be_hard_deleted(client, patient):
    book(client, patient, make_slot())
    with pytest.raises(psycopg2.Error):
        sql("DELETE FROM auth.users WHERE id = %s", (patient["id"],))


def test_updated_at_moves_when_a_row_changes(client, patient):
    appointment = book(client, patient, make_slot()).json()
    client.post(f"/appointments/{appointment['id']}/cancel", headers=patient["headers"], json={})
    created, updated = sql(
        "SELECT created_at, updated_at FROM public.appointments WHERE id = %s", (appointment["id"],)
    )[0]
    assert updated > created


@pytest.fixture
def scratch_db():
    name = f"migrations_{uuid.uuid4().hex[:8]}"
    admin = psycopg2.connect(STACK["DB_URL"])
    admin.autocommit = True
    admin.cursor().execute(f"CREATE DATABASE {name}")
    yield STACK["DB_URL"].rsplit("/", 1)[0] + f"/{name}"
    admin.cursor().execute(f"DROP DATABASE {name} WITH (FORCE)")
    admin.close()


def write(folder: Path, name: str, content: str) -> None:
    (folder / name).write_text(content, encoding="utf-8")


def versions(url: str) -> list:
    conn = psycopg2.connect(url)
    with conn, conn.cursor() as cur:
        cur.execute("SELECT version FROM public.schema_migrations ORDER BY version")
        rows = [r[0] for r in cur.fetchall()]
    conn.close()
    return rows


def test_each_migration_runs_once(scratch_db, tmp_path):
    write(tmp_path, "00001_a.sql", "CREATE TABLE a (id int);")
    write(tmp_path, "00002_b.sql", "CREATE TABLE b (id int);")
    assert apply_migrations(scratch_db, tmp_path) == ["00001_a.sql", "00002_b.sql"]
    assert apply_migrations(scratch_db, tmp_path) == []

    write(tmp_path, "00003_c.sql", "CREATE TABLE c (id int);")
    assert apply_migrations(scratch_db, tmp_path) == ["00003_c.sql"]
    assert versions(scratch_db) == ["00001_a.sql", "00002_b.sql", "00003_c.sql"]


def test_a_failed_migration_leaves_nothing_behind(scratch_db, tmp_path):
    write(tmp_path, "00001_good.sql", "CREATE TABLE good (id int);")
    write(tmp_path, "00002_bad.sql", "CREATE TABLE half (id int); SELECT broken FROM nowhere;")
    with pytest.raises(psycopg2.Error):
        apply_migrations(scratch_db, tmp_path)

    assert versions(scratch_db) == ["00001_good.sql"]
    conn = psycopg2.connect(scratch_db)
    with conn, conn.cursor() as cur:
        cur.execute("SELECT to_regclass('public.half')")
        assert cur.fetchone()[0] is None
    conn.close()


def test_baseline_marks_old_files_without_running_them(scratch_db, tmp_path):
    write(tmp_path, "00001_old.sql", "SELECT broken FROM nowhere;")
    write(tmp_path, "00002_new.sql", "CREATE TABLE fresh (id int);")
    assert apply_migrations(scratch_db, tmp_path, baseline="00001") == ["00002_new.sql"]
    assert versions(scratch_db) == ["00001_old.sql", "00002_new.sql"]


def test_an_existing_database_needs_a_baseline(scratch_db, tmp_path):
    conn = psycopg2.connect(scratch_db)
    with conn, conn.cursor() as cur:
        cur.execute("CREATE TABLE public.profiles (id int)")
    conn.close()
    write(tmp_path, "00001_a.sql", "CREATE TABLE a (id int);")
    with pytest.raises(RuntimeError):
        apply_migrations(scratch_db, tmp_path)


MISSING = "00000000-0000-0000-0000-000000000000"


def test_booking_a_missing_slot_is_404(client, patient):
    assert book(client, patient, MISSING).status_code == 404


def test_booking_a_past_slot_is_refused(client, patient):
    start = datetime.now(UTC) - timedelta(days=30, minutes=uuid.uuid4().int % 500000)
    slot = sql(
        "INSERT INTO public.availability_slots (doctor_id, start_time, end_time) VALUES (%s, %s, %s) RETURNING id",
        (DOCTOR_ID, start, start + timedelta(minutes=30)),
    )[0][0]
    assert book(client, patient, str(slot)).status_code == 400


def test_booking_an_unapproved_doctor_is_refused(client, patient):
    suspended = "d2000000-0000-0000-0000-000000000009"
    start = datetime.now(UTC) + timedelta(days=700, minutes=uuid.uuid4().int % 500000)
    slot = sql(
        "INSERT INTO public.availability_slots (doctor_id, start_time, end_time) VALUES (%s, %s, %s) RETURNING id",
        (suspended, start, start + timedelta(minutes=30)),
    )[0][0]
    assert book(client, patient, str(slot)).status_code == 400


def test_the_unique_index_answers_409_if_the_row_lock_is_ever_bypassed(monkeypatch):
    from unittest.mock import MagicMock

    from fastapi import HTTPException
    from postgrest import APIError

    from app.services import appointment_service

    broken = MagicMock()
    broken.rpc.return_value.execute.side_effect = APIError(
        {"code": "23505", "message": "duplicate"}
    )
    monkeypatch.setattr(appointment_service, "_get_client", lambda: broken)

    with pytest.raises(HTTPException) as exc:
        appointment_service.book_slot_atomic("p", "s")
    assert exc.value.status_code == 409


def test_other_database_errors_are_not_reported_as_conflicts(monkeypatch):
    from unittest.mock import MagicMock

    from postgrest import APIError

    from app.services import appointment_service

    broken = MagicMock()
    broken.rpc.return_value.execute.side_effect = APIError({"code": "XX000", "message": "boom"})
    monkeypatch.setattr(appointment_service, "_get_client", lambda: broken)

    with pytest.raises(APIError):
        appointment_service.book_slot_atomic("p", "s")


def test_an_empty_procedure_result_is_an_error(monkeypatch):
    from unittest.mock import MagicMock

    from fastapi import HTTPException

    from app.services import appointment_service

    empty = MagicMock()
    empty.rpc.return_value.execute.return_value.data = None
    monkeypatch.setattr(appointment_service, "_get_client", lambda: empty)

    with pytest.raises(HTTPException) as exc:
        appointment_service.book_slot_atomic("p", "s")
    assert exc.value.status_code == 500


def test_cancelling_a_missing_appointment_is_404(client, patient):
    res = client.post(f"/appointments/{MISSING}/cancel", headers=patient["headers"], json={})
    assert res.status_code == 404


def test_completing_a_missing_appointment_is_404(client, doctor_headers):
    assert (
        client.post(f"/appointments/{MISSING}/complete", headers=doctor_headers).status_code == 404
    )


def test_only_the_assigned_doctor_can_complete(client, patient):
    appointment = book(client, patient, make_slot()).json()
    backdate(appointment["id"])

    other_id = str(uuid.uuid4())
    token = create_mock_jwt(other_id, "o@tests.invalid", UserRole.DOCTOR, "Dr. Other")
    sql("INSERT INTO public.doctor_profiles (user_id, city) VALUES (%s, 'Dhaka')", (other_id,))
    res = client.post(f"/appointments/{appointment['id']}/complete", headers=headers(token))
    assert res.status_code == 403


def test_the_doctor_can_cancel_their_appointment(client, doctor_headers, patient):
    appointment = book(client, patient, make_slot()).json()
    res = client.post(
        f"/appointments/{appointment['id']}/cancel", headers=doctor_headers, json={"reason": "Away"}
    )
    assert res.status_code == 200
    assert res.json()["status"] == "cancelled"


def test_another_doctor_cannot_cancel(client, patient):
    appointment = book(client, patient, make_slot()).json()
    other_id = str(uuid.uuid4())
    token = create_mock_jwt(other_id, "o@tests.invalid", UserRole.DOCTOR, "Dr. Other")
    sql("INSERT INTO public.doctor_profiles (user_id, city) VALUES (%s, 'Dhaka')", (other_id,))
    res = client.post(f"/appointments/{appointment['id']}/cancel", headers=headers(token), json={})
    assert res.status_code == 403


def test_an_admin_can_cancel_any_appointment(client, admin_token, patient):
    appointment = book(client, patient, make_slot()).json()
    res = client.post(
        f"/appointments/{appointment['id']}/cancel", headers=headers(admin_token), json={}
    )
    assert res.status_code == 200


def test_cancelling_twice_is_refused(client, patient):
    appointment = book(client, patient, make_slot()).json()
    url = f"/appointments/{appointment['id']}/cancel"
    assert client.post(url, headers=patient["headers"], json={}).status_code == 200
    assert client.post(url, headers=patient["headers"], json={}).status_code == 400


def test_a_booked_slot_cannot_be_deleted(client, doctor_headers, patient):
    slot = make_slot()
    book(client, patient, slot)
    assert client.delete(f"/doctors/me/slots/{slot}", headers=doctor_headers).status_code == 400


def test_a_doctor_cannot_delete_another_doctors_slot(client, patient):
    slot = make_slot()
    other_id = str(uuid.uuid4())
    token = create_mock_jwt(other_id, "o@tests.invalid", UserRole.DOCTOR, "Dr. Other")
    sql("INSERT INTO public.doctor_profiles (user_id, city) VALUES (%s, 'Dhaka')", (other_id,))
    assert client.delete(f"/doctors/me/slots/{slot}", headers=headers(token)).status_code == 403


def test_deleting_a_missing_slot_is_404(client, doctor_headers):
    assert client.delete(f"/doctors/me/slots/{MISSING}", headers=doctor_headers).status_code == 404


def test_unapproved_doctor_cannot_create_slots(client):
    other_id = str(uuid.uuid4())
    token = create_mock_jwt(other_id, "o@tests.invalid", UserRole.DOCTOR, "Dr. Pending")
    sql("INSERT INTO public.doctor_profiles (user_id, city) VALUES (%s, 'Dhaka')", (other_id,))
    start = datetime.now(UTC) + timedelta(days=10)
    res = client.post(
        "/doctors/me/slots",
        headers=headers(token),
        json={
            "start_time": start.isoformat(),
            "end_time": (start + timedelta(minutes=30)).isoformat(),
        },
    )
    assert res.status_code == 400


def test_public_slots_of_an_unapproved_doctor_are_hidden(client):
    assert client.get("/doctors/d2000000-0000-0000-0000-000000000009/slots").status_code == 404


def test_a_doctor_lists_their_open_slots(client, doctor_headers):
    res = client.get("/doctors/me/slots?include_booked=false", headers=doctor_headers)
    assert res.status_code == 200
    assert all(not slot["is_booked"] for slot in res.json())


def test_admin_sees_all_appointments_and_doctor_sees_their_own(
    client, admin_token, doctor_headers, patient
):
    appointment = book(client, patient, make_slot()).json()
    assert client.get("/appointments/me", headers=headers(admin_token)).status_code == 200
    rows = client.get("/appointments/me?status=booked", headers=doctor_headers).json()
    assert appointment["id"] in [row["id"] for row in rows]


class FakeSlotTable:
    """Passes the overlap check, then fails or returns nothing on insert."""

    def __init__(self, insert_error=None):
        self.insert_error = insert_error

    def __getattr__(self, _name):
        return lambda *args, **kwargs: self

    def insert(self, _row):
        if self.insert_error:
            raise self.insert_error
        return self

    def execute(self):
        from types import SimpleNamespace

        return SimpleNamespace(data=[])


def create_slot_with(monkeypatch, table):
    from types import SimpleNamespace

    from app.models.enums import VerificationStatus
    from app.services import appointment_service

    doctor = SimpleNamespace(id="d", verification_status=VerificationStatus.APPROVED)
    monkeypatch.setattr(appointment_service, "get_doctor_profile_by_user_id", lambda _user: doctor)
    monkeypatch.setattr(
        appointment_service, "_get_client", lambda: SimpleNamespace(table=lambda _name: table)
    )
    start = datetime.now(UTC) + timedelta(days=1)
    return appointment_service.create_availability_slot("u", start, start + timedelta(minutes=30))


def test_the_overlap_constraint_catches_a_race_past_the_check(monkeypatch):
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        create_slot_with(monkeypatch, FakeSlotTable(RuntimeError("violates no_overlapping_slots")))
    assert exc.value.status_code == 400


def test_a_failed_slot_insert_reveals_nothing(monkeypatch):
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        create_slot_with(monkeypatch, FakeSlotTable(RuntimeError("secret database detail")))
    assert exc.value.status_code == 500
    assert "secret" not in exc.value.detail


def test_an_empty_slot_insert_is_an_error(monkeypatch):
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        create_slot_with(monkeypatch, FakeSlotTable())
    assert exc.value.status_code == 500


def test_no_service_key_means_503(monkeypatch):
    from fastapi import HTTPException

    from app.services import appointment_service

    monkeypatch.setattr(appointment_service, "get_supabase_admin_client", lambda: None)
    with pytest.raises(HTTPException) as exc:
        appointment_service._get_client()
    assert exc.value.status_code == 503


def test_public_slots_need_a_database(monkeypatch):
    from fastapi import HTTPException

    from app.services import appointment_service

    monkeypatch.setattr(appointment_service, "get_supabase_client", lambda: None)
    with pytest.raises(HTTPException) as exc:
        appointment_service.list_public_doctor_slots(DOCTOR_ID)
    assert exc.value.status_code == 503


def test_fetching_a_missing_appointment_is_404():
    from fastapi import HTTPException

    from app.services import appointment_service

    with pytest.raises(HTTPException) as exc:
        appointment_service.get_appointment_by_id(MISSING)
    assert exc.value.status_code == 404
