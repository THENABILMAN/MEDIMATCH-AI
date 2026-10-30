import concurrent.futures
from datetime import datetime, timedelta, timezone
import uuid
import pytest
from fastapi import status
from fastapi.testclient import TestClient
from conftest import create_mock_jwt
from app.core.supabase import get_supabase_admin_client
from app.main import app
from app.models.enums import AppointmentStatus, UserRole, VerificationStatus

DEMO_DOCTOR_USER_ID = "a0000000-0000-0000-0000-000000000003"
DEMO_DOCTOR_PROFILE_ID = "d0000000-0000-0000-0000-000000000000"
DEMO_PATIENT_USER_ID = "a0000000-0000-0000-0000-000000000002"


@pytest.fixture
def doctor_headers() -> dict:
    token = create_mock_jwt(
        DEMO_DOCTOR_USER_ID,
        "doctor@medimatch.test",
        UserRole.DOCTOR,
        "Dr. Tanvir Hasan",
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def patient_headers() -> dict:
    token = create_mock_jwt(
        DEMO_PATIENT_USER_ID,
        "patient@medimatch.test",
        UserRole.PATIENT,
        "Demo Patient",
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def cleanup_test_slots():
    admin_client = get_supabase_admin_client()
    now_utc = datetime.now(timezone.utc)
    if admin_client:
        admin_client.table("availability_slots").delete().eq(
            "doctor_id", DEMO_DOCTOR_PROFILE_ID
        ).gte("start_time", (now_utc + timedelta(days=15)).isoformat()).execute()
    yield
    if admin_client:
        admin_client.table("availability_slots").delete().eq(
            "doctor_id", DEMO_DOCTOR_PROFILE_ID
        ).gte("start_time", (now_utc + timedelta(days=15)).isoformat()).execute()



def test_doctor_create_list_and_delete_slot(client: TestClient, doctor_headers: dict):
    """Doctor can create an availability slot, list it, and delete it."""
    now_utc = datetime.now(timezone.utc)
    start_time = now_utc + timedelta(days=20, hours=9)
    end_time = start_time + timedelta(minutes=30)

    # 1. Create slot
    payload = {
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
    }
    create_res = client.post("/doctors/me/slots", headers=doctor_headers, json=payload)
    assert create_res.status_code == status.HTTP_201_CREATED
    slot_data = create_res.json()
    slot_id = slot_data["id"]
    assert slot_data["doctor_id"] == DEMO_DOCTOR_PROFILE_ID
    assert slot_data["is_booked"] is False

    # 2. List slots
    list_res = client.get("/doctors/me/slots", headers=doctor_headers)
    assert list_res.status_code == status.HTTP_200_OK
    slots = list_res.json()
    assert any(s["id"] == slot_id for s in slots)

    # 3. Delete slot
    del_res = client.delete(f"/doctors/me/slots/{slot_id}", headers=doctor_headers)
    assert del_res.status_code == status.HTTP_204_NO_CONTENT

    # Verify deleted
    list_res_after = client.get("/doctors/me/slots", headers=doctor_headers)
    assert not any(s["id"] == slot_id for s in list_res_after.json())


def test_slot_validation_rules(client: TestClient, doctor_headers: dict):
    """Slots in the past, duration < 15 min, or end <= start must be rejected."""
    now_utc = datetime.now(timezone.utc)

    # In the past
    past_payload = {
        "start_time": (now_utc - timedelta(days=1)).isoformat(),
        "end_time": (now_utc - timedelta(days=1, minutes=-30)).isoformat(),
    }
    res_past = client.post("/doctors/me/slots", headers=doctor_headers, json=past_payload)
    assert res_past.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # Duration < 15 min
    short_payload = {
        "start_time": (now_utc + timedelta(days=2)).isoformat(),
        "end_time": (now_utc + timedelta(days=2, minutes=10)).isoformat(),
    }
    res_short = client.post("/doctors/me/slots", headers=doctor_headers, json=short_payload)
    assert res_short.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # End before start
    inv_payload = {
        "start_time": (now_utc + timedelta(days=2, minutes=30)).isoformat(),
        "end_time": (now_utc + timedelta(days=2)).isoformat(),
    }
    res_inv = client.post("/doctors/me/slots", headers=doctor_headers, json=inv_payload)
    assert res_inv.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_overlapping_slots_prevented(client: TestClient, doctor_headers: dict):
    """Doctor cannot create overlapping availability slots."""
    now_utc = datetime.now(timezone.utc)
    base_start = now_utc + timedelta(days=22, hours=10)
    base_end = base_start + timedelta(minutes=45)

    # 1. Create first slot
    payload1 = {
        "start_time": base_start.isoformat(),
        "end_time": base_end.isoformat(),
    }
    res1 = client.post("/doctors/me/slots", headers=doctor_headers, json=payload1)
    assert res1.status_code == status.HTTP_201_CREATED
    slot1_id = res1.json()["id"]

    try:
        # 2. Try creating overlapping slot (e.g. starting 15 min into slot 1)
        overlap_payload = {
            "start_time": (base_start + timedelta(minutes=15)).isoformat(),
            "end_time": (base_end + timedelta(minutes=15)).isoformat(),
        }
        res2 = client.post("/doctors/me/slots", headers=doctor_headers, json=overlap_payload)
        assert res2.status_code == status.HTTP_400_BAD_REQUEST
        assert "overlap" in res2.json()["detail"].lower()
    finally:
        client.delete(f"/doctors/me/slots/{slot1_id}", headers=doctor_headers)


def test_patient_cannot_create_doctor_slot(client: TestClient, patient_headers: dict):
    """Patients cannot access doctor slot management endpoints."""
    now_utc = datetime.now(timezone.utc)
    payload = {
        "start_time": (now_utc + timedelta(days=5)).isoformat(),
        "end_time": (now_utc + timedelta(days=5, minutes=30)).isoformat(),
    }
    res = client.post("/doctors/me/slots", headers=patient_headers, json=payload)
    assert res.status_code == status.HTTP_403_FORBIDDEN


def test_public_doctor_slots_listing(client: TestClient):
    """Public can view upcoming unbooked slots of an approved doctor, but not unapproved."""
    # Seeded approved doctor
    res = client.get(f"/doctors/{DEMO_DOCTOR_PROFILE_ID}/slots")
    assert res.status_code == status.HTTP_200_OK
    slots = res.json()
    assert isinstance(slots, list)
    assert all(s["is_booked"] is False for s in slots)

    # Unapproved doctor
    unapproved_id = "d2000000-0000-0000-0000-000000000007"  # Dr. Mehedi (pending)
    res_unapp = client.get(f"/doctors/{unapproved_id}/slots")
    assert res_unapp.status_code == status.HTTP_404_NOT_FOUND


def test_atomic_booking_lifecycle_and_cancellation(
    client: TestClient,
    doctor_headers: dict,
    patient_headers: dict,
):
    """Test full booking lifecycle: book -> duplicate reject -> cancel -> slot freed."""
    now_utc = datetime.now(timezone.utc)
    start_time = now_utc + timedelta(days=25, hours=14)
    end_time = start_time + timedelta(minutes=30)

    # 1. Doctor creates slot
    slot_res = client.post(
        "/doctors/me/slots",
        headers=doctor_headers,
        json={"start_time": start_time.isoformat(), "end_time": end_time.isoformat()},
    )
    assert slot_res.status_code == status.HTTP_201_CREATED
    slot_id = slot_res.json()["id"]

    try:
        # 2. Patient books slot
        book_res = client.post(
            "/appointments",
            headers=patient_headers,
            json={"slot_id": slot_id},
        )
        assert book_res.status_code == status.HTTP_201_CREATED
        app_data = book_res.json()
        appointment_id = app_data["id"]
        assert app_data["slot_id"] == slot_id
        assert app_data["status"] == AppointmentStatus.BOOKED.value
        assert "Dr. Tanvir Hasan" in app_data["doctor"]["full_name"]

        # 3. Doctor cannot delete a booked slot
        del_res = client.delete(f"/doctors/me/slots/{slot_id}", headers=doctor_headers)
        assert del_res.status_code == status.HTTP_400_BAD_REQUEST

        # 4. Immediate second booking attempt fails with 409 Conflict
        book_again_res = client.post(
            "/appointments",
            headers=patient_headers,
            json={"slot_id": slot_id},
        )
        assert book_again_res.status_code == status.HTTP_409_CONFLICT

        # 5. Patient checks their appointments
        my_apps = client.get("/appointments/me", headers=patient_headers)
        assert my_apps.status_code == status.HTTP_200_OK
        assert any(a["id"] == appointment_id for a in my_apps.json())

        # 6. Patient cancels appointment
        cancel_res = client.post(
            f"/appointments/{appointment_id}/cancel",
            headers=patient_headers,
            json={"reason": "Schedule conflict"},
        )
        assert cancel_res.status_code == status.HTTP_200_OK
        assert cancel_res.json()["status"] == AppointmentStatus.CANCELLED.value

        # 7. Slot is now freed (is_booked is false)
        slots_after = client.get("/doctors/me/slots", headers=doctor_headers).json()
        target_slot = next(s for s in slots_after if s["id"] == slot_id)
        assert target_slot["is_booked"] is False

    finally:
        admin_client = get_supabase_admin_client()
        if admin_client:
            admin_client.table("appointments").delete().eq("slot_id", slot_id).execute()
            admin_client.table("availability_slots").delete().eq("id", slot_id).execute()


def test_doctor_complete_appointment(client: TestClient, doctor_headers: dict, patient_headers: dict):
    """Doctor can complete an appointment; patient cannot."""
    now_utc = datetime.now(timezone.utc)
    start_time = now_utc + timedelta(days=26, hours=11)
    end_time = start_time + timedelta(minutes=30)

    # Doctor creates slot
    slot_res = client.post(
        "/doctors/me/slots",
        headers=doctor_headers,
        json={"start_time": start_time.isoformat(), "end_time": end_time.isoformat()},
    )
    assert slot_res.status_code == status.HTTP_201_CREATED
    slot_id = slot_res.json()["id"]

    try:
        # Patient books
        book_res = client.post("/appointments", headers=patient_headers, json={"slot_id": slot_id})
        assert book_res.status_code == status.HTTP_201_CREATED
        app_id = book_res.json()["id"]

        # Patient attempts to complete -> 403 Forbidden
        p_comp = client.post(f"/appointments/{app_id}/complete", headers=patient_headers)
        assert p_comp.status_code == status.HTTP_403_FORBIDDEN

        # Doctor completes -> 200 OK
        d_comp = client.post(f"/appointments/{app_id}/complete", headers=doctor_headers)
        assert d_comp.status_code == status.HTTP_200_OK
        assert d_comp.json()["status"] == AppointmentStatus.COMPLETED.value

        # Cannot cancel completed appointment
        cancel_res = client.post(f"/appointments/{app_id}/cancel", headers=doctor_headers)
        assert cancel_res.status_code == status.HTTP_400_BAD_REQUEST

    finally:
        admin_client = get_supabase_admin_client()
        if admin_client:
            admin_client.table("appointments").delete().eq("slot_id", slot_id).execute()
            admin_client.table("availability_slots").delete().eq("id", slot_id).execute()


def test_unauthorized_user_cannot_cancel_appointment(client: TestClient, doctor_headers: dict, patient_headers: dict):
    """A user who is neither the patient nor the doctor cannot cancel the appointment."""
    now_utc = datetime.now(timezone.utc)
    start_time = now_utc + timedelta(days=27, hours=10)
    end_time = start_time + timedelta(minutes=30)

    slot_res = client.post(
        "/doctors/me/slots",
        headers=doctor_headers,
        json={"start_time": start_time.isoformat(), "end_time": end_time.isoformat()},
    )
    assert slot_res.status_code == status.HTTP_201_CREATED
    slot_id = slot_res.json()["id"]

    try:
        book_res = client.post("/appointments", headers=patient_headers, json={"slot_id": slot_id})
        app_id = book_res.json()["id"]

        # Random user token
        other_token = create_mock_jwt(
            "99999999-0000-0000-0000-000000000099",
            "intruder@medimatch.test",
            UserRole.PATIENT,
            "Intruder Patient",
        )
        intruder_headers = {"Authorization": f"Bearer {other_token}"}

        cancel_res = client.post(f"/appointments/{app_id}/cancel", headers=intruder_headers)
        assert cancel_res.status_code == status.HTTP_403_FORBIDDEN

        # Clean cancel with legitimate patient
        client.post(f"/appointments/{app_id}/cancel", headers=patient_headers)
    finally:
        admin_client = get_supabase_admin_client()
        if admin_client:
            admin_client.table("appointments").delete().eq("slot_id", slot_id).execute()
            admin_client.table("availability_slots").delete().eq("id", slot_id).execute()


def test_concurrency_20_simultaneous_bookings(client: TestClient, doctor_headers: dict, patient_headers: dict):
    """Concurrency test: fires 20 simultaneous booking requests for 1 slot.
    
    Guarantees:
      - Exactly 1 request succeeds with 201 Created.
      - Exactly 19 requests fail with 409 Conflict.
      - Exactly 1 appointment row exists in PostgreSQL.
    """
    admin_client = get_supabase_admin_client()
    assert admin_client is not None

    # 1. Doctor creates 1 slot
    now_utc = datetime.now(timezone.utc)
    start_time = now_utc + timedelta(days=29, hours=9)
    end_time = start_time + timedelta(minutes=30)

    slot_res = client.post(
        "/doctors/me/slots",
        headers=doctor_headers,
        json={"start_time": start_time.isoformat(), "end_time": end_time.isoformat()},
    )
    assert slot_res.status_code == status.HTTP_201_CREATED
    slot_id = slot_res.json()["id"]

    try:
        # 2. Fire 20 simultaneous booking requests concurrently
        def book_worker(_):
            with TestClient(app) as local_client:
                return local_client.post("/appointments", headers=patient_headers, json={"slot_id": slot_id})

        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(book_worker, i) for i in range(20)]
            responses = [f.result() for f in concurrent.futures.as_completed(futures)]

        status_codes = [r.status_code for r in responses]

        # Verify atomic locking outcome
        success_count = status_codes.count(status.HTTP_201_CREATED)
        conflict_count = status_codes.count(status.HTTP_409_CONFLICT)

        assert success_count == 1, f"Expected exactly 1 booking success, got {success_count}. Codes: {status_codes}"
        assert conflict_count == 19, f"Expected exactly 19 conflicts, got {conflict_count}. Codes: {status_codes}"

        # 3. Verify database state
        db_apps = admin_client.table("appointments").select("*").eq("slot_id", slot_id).eq("status", "booked").execute()
        assert len(db_apps.data) == 1

        db_slot = admin_client.table("availability_slots").select("*").eq("id", slot_id).execute()
        assert db_slot.data[0]["is_booked"] is True

    finally:
        # Cleanup appointment and slot
        admin_client.table("appointments").delete().eq("slot_id", slot_id).execute()
        admin_client.table("availability_slots").delete().eq("id", slot_id).execute()


