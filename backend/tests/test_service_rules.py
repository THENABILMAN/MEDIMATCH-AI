"""Offline regression tests for service rules, using a stubbed Supabase client."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.models.enums import UserRole
from app.schemas.doctor import DoctorProfileCreateOrUpdate
from app.services import account_service, admin_service, chat_service, doctor_service

SPECIALTY_ID = "11111111-0000-0000-0000-000000000001"


class FakeQuery:
    """Chainable stand-in for a Supabase query that records inserts and updates."""

    def __init__(self, rows, log, table):
        self.rows = rows
        self.log = log
        self.table = table

    def __getattr__(self, _name):
        return lambda *_args, **_kwargs: self

    def insert(self, data):
        self.log.append((self.table, "insert", data))
        return self

    def update(self, data):
        self.log.append((self.table, "update", data))
        return self

    def delete(self):
        self.log.append((self.table, "delete", None))
        return self

    def execute(self):
        return SimpleNamespace(data=self.rows, count=len(self.rows))


def fake_client(tables):
    log = []
    client = MagicMock()
    client.table = lambda name: FakeQuery(tables.get(name, []), log, name)
    client.log = log
    return client


DOCTOR_ROW = {
    "id": "d1",
    "user_id": "u1",
    "bio": "Bio",
    "qualifications": ["MBBS"],
    "years_experience": 5,
    "consultation_fee": 500.0,
    "clinic_name": "Clinic",
    "city": "Dhaka",
}


def profile_payload(**overrides):
    fields = {
        "bio": "Bio",
        "qualifications": ["MBBS"],
        "years_experience": 5,
        "consultation_fee": 500.0,
        "clinic_name": "Clinic",
        "city": "Dhaka",
        "specialty_ids": [SPECIALTY_ID],
    }
    return DoctorProfileCreateOrUpdate(**{**fields, **overrides})


def test_suspended_doctor_cannot_clear_suspension_by_editing(monkeypatch):
    client = fake_client({"doctor_profiles": [{**DOCTOR_ROW, "verification_status": "suspended"}]})
    monkeypatch.setattr(doctor_service, "get_supabase_admin_client", lambda: client)

    with pytest.raises(HTTPException) as exc:
        doctor_service.upsert_doctor_profile("u1", profile_payload(bio="New bio"))

    assert exc.value.status_code == 403
    assert client.log == []


def test_saving_without_changes_keeps_doctor_approved(monkeypatch):
    client = fake_client(
        {
            "doctor_profiles": [{**DOCTOR_ROW, "verification_status": "approved"}],
            "doctor_specialties": [{"specialty_id": SPECIALTY_ID}],
        }
    )
    monkeypatch.setattr(doctor_service, "get_supabase_admin_client", lambda: client)
    monkeypatch.setattr(doctor_service, "get_doctor_profile_by_user_id", lambda _id: "profile")

    assert doctor_service.upsert_doctor_profile("u1", profile_payload()) == "profile"
    assert client.log == []


def test_specialty_search_resolves_to_matching_doctors():
    client = fake_client(
        {
            "specialties": [{"id": "s1", "name": "Neurology"}, {"id": "s2", "name": "Cardiology"}],
            "doctor_specialties": [{"doctor_id": "d2"}, {"doctor_id": "d1"}, {"doctor_id": "d1"}],
        }
    )

    assert doctor_service._doctor_ids_with_specialty(client, " neuro ") == ["d1", "d2"]


def test_unknown_specialty_returns_an_empty_page(monkeypatch):
    client = fake_client({"specialties": [{"id": "s1", "name": "Neurology"}]})
    monkeypatch.setattr(doctor_service, "get_supabase_admin_client", lambda: client)

    result = doctor_service.search_public_doctors(specialty="Dermatology")

    assert result.items == []
    assert result.total == 0


@pytest.fixture
def chat_client(monkeypatch):
    client = fake_client(
        {
            "conversations": [{"id": "c1", "patient_id": "p1"}],
            "messages": [{"sender": "patient", "content": "hello"}],
        }
    )
    monkeypatch.setattr(chat_service, "get_supabase_admin_client", lambda: client)
    return client


def stub_graph(monkeypatch, state):
    graph = SimpleNamespace(invoke=lambda *_args, **_kwargs: state)
    monkeypatch.setattr(chat_service, "get_symptom_graph", lambda: graph)


def test_emergency_flag_is_stored_with_the_reply(chat_client, monkeypatch):
    stub_graph(
        monkeypatch,
        {"assistant_reply": "Call 999", "safety_status": "emergency", "current_step": "emergency"},
    )

    chat_service.send_patient_message("c1", "p1", "chest pain")

    saved = [d for t, op, d in chat_client.log if t == "messages" and d["sender"] == "assistant"]
    assert saved[0]["metadata"] == {"is_emergency": True, "recommendations": []}


def test_followup_field_is_returned_for_suggested_answers(chat_client, monkeypatch):
    stub_graph(
        monkeypatch,
        {
            "assistant_reply": "How long?",
            "current_step": "ask_followup",
            "asking_about": "duration",
        },
    )

    assert chat_service.send_patient_message("c1", "p1", "headache")["followup_field"] == "duration"


def test_reply_text_does_not_repeat_recommendation_cards(chat_client, monkeypatch):
    stub_graph(
        monkeypatch,
        {
            "assistant_reply": "Here is your search.",
            "current_step": "completed",
            "search_criteria": {"candidate_specialties": ["Neurology"], "city": "Dhaka"},
        },
    )
    doctor = MagicMock()
    doctor.model_dump.return_value = {"id": "d1", "full_name": "Dr. A"}
    monkeypatch.setattr(
        "app.search.recommend.recommend_doctors",
        lambda *_args, **_kwargs: SimpleNamespace(recommendations=[doctor]),
    )

    result = chat_service.send_patient_message("c1", "p1", "headache in Dhaka")

    assert result["assistant_reply"] == "Here is your search."
    assert result["recommendations"] == [{"id": "d1", "full_name": "Dr. A"}]


@pytest.fixture
def account_client(monkeypatch):
    def build(tables):
        client = fake_client(tables)
        monkeypatch.setattr(account_service, "get_supabase_admin_client", lambda: client)
        monkeypatch.setattr(account_service, "log_audit_event", lambda **_kwargs: None)
        return client

    return build


def test_doctors_cannot_close_accounts_here(account_client):
    account_client({})

    with pytest.raises(HTTPException) as exc:
        account_service.anonymize_patient_account("u1", UserRole.DOCTOR)
    assert exc.value.status_code == 403


def test_upcoming_appointment_blocks_account_closure(account_client):
    client = account_client(
        {
            "appointments": [
                {"id": "a1", "availability_slots": {"start_time": "2999-01-01T00:00:00+00:00"}}
            ]
        }
    )

    with pytest.raises(HTTPException) as exc:
        account_service.anonymize_patient_account("u1", UserRole.PATIENT)

    assert exc.value.status_code == 409
    client.auth.admin.update_user_by_id.assert_not_called()


def test_closing_account_clears_identity_and_chat_but_not_appointments(account_client):
    client = account_client(
        {
            "appointments": [
                {"id": "a1", "availability_slots": {"start_time": "2001-01-01T00:00:00+00:00"}}
            ],
            "conversations": [{"id": "c1"}],
        }
    )

    account_service.anonymize_patient_account("u1", UserRole.PATIENT)

    assert "invalid" in client.auth.admin.update_user_by_id.call_args.args[1]["email"]
    profile_update = next(d for t, op, d in client.log if t == "profiles" and op == "update")
    assert profile_update["full_name"] == "Deleted Patient"
    assert profile_update["phone"] is None
    assert ("conversations", "delete", None) in client.log
    assert not any(t == "appointments" and op == "delete" for t, op, _d in client.log)


def test_failed_identity_update_erases_nothing(account_client):
    client = account_client({})
    client.auth.admin.update_user_by_id.side_effect = ConnectionError("auth down")

    with pytest.raises(HTTPException) as exc:
        account_service.anonymize_patient_account("u1", UserRole.PATIENT)

    assert exc.value.status_code == 502
    assert client.log == []


def test_only_the_owner_or_an_admin_can_open_a_credential(monkeypatch):
    client = fake_client(
        {
            "doctor_credentials": [
                {"file_path": "owner/a.pdf", "doctor_profiles": {"user_id": "owner"}}
            ]
        }
    )
    client.storage.from_.return_value.create_signed_url.return_value = {
        "signedURL": "https://signed"
    }
    monkeypatch.setattr(doctor_service, "get_supabase_admin_client", lambda: client)

    with pytest.raises(HTTPException) as exc:
        doctor_service.get_credential_url("c1", "someone-else", is_admin=False)
    assert exc.value.status_code == 403

    assert (
        doctor_service.get_credential_url("c1", "owner", is_admin=False)["url"] == "https://signed"
    )
    assert (
        doctor_service.get_credential_url("c1", "admin", is_admin=True)["url"] == "https://signed"
    )


def test_admin_tables_reject_unknown_sort_columns(monkeypatch):
    monkeypatch.setattr(admin_service, "get_supabase_admin_client", lambda: fake_client({}))

    with pytest.raises(HTTPException) as exc:
        admin_service.list_patients_for_admin(sort="phone")
    assert exc.value.status_code == 400


def test_patch_profile_cannot_skip_re_verification(monkeypatch):
    from app.schemas.profile import DoctorProfileRead, ProfileUpdate, UserMeResponse
    from app.services import profile_service

    client = fake_client({})
    monkeypatch.setattr(profile_service, "get_supabase_admin_client", lambda: client)
    monkeypatch.setattr(profile_service, "log_audit_event", lambda **_kwargs: None)
    synced = []
    monkeypatch.setattr(profile_service, "on_doctor_updated", lambda *args: synced.append(args))
    current = UserMeResponse(
        id="u1",
        role=UserRole.DOCTOR,
        full_name="Dr. A",
        doctor_profile=DoctorProfileRead(
            id="d1", user_id="u1", city="Dhaka", verification_status="approved"
        ),
    )
    monkeypatch.setattr(profile_service, "get_user_profile", lambda *_args: current)

    profile_service.update_user_profile(
        "u1", ProfileUpdate(doctor_profile={"consultation_fee": 9000})
    )

    update = next(d for t, op, d in client.log if t == "doctor_profiles" and op == "update")
    assert update["verification_status"] == "pending"
    assert synced
