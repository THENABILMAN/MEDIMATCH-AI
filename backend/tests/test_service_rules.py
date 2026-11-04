"""Offline regression tests for service rules, using a stubbed Supabase client."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.schemas.doctor import DoctorProfileCreateOrUpdate
from app.services import chat_service, doctor_service


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
        "specialty_ids": ["s1"],
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
            "doctor_specialties": [{"specialty_id": "s1"}],
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


def test_empty_assistant_reply_gets_a_fallback(chat_client, monkeypatch):
    stub_graph(monkeypatch, {"assistant_reply": None, "current_step": "classify_intent"})

    result = chat_service.send_patient_message("c1", "p1", "hello")

    assert result["assistant_reply"]
    saved = [d for t, op, d in chat_client.log if t == "messages" and d["sender"] == "assistant"]
    assert saved[0]["content"] == result["assistant_reply"]


def test_emergency_flag_is_stored_with_the_reply(chat_client, monkeypatch):
    stub_graph(
        monkeypatch,
        {"assistant_reply": "Call 999", "safety_status": "emergency", "current_step": "emergency"},
    )

    chat_service.send_patient_message("c1", "p1", "chest pain")

    saved = [d for t, op, d in chat_client.log if t == "messages" and d["sender"] == "assistant"]
    assert saved[0]["metadata"] == {"is_emergency": True, "recommendations": []}
