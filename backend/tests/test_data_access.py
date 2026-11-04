"""RLS is a second layer inside the API, not only for direct PostgREST access.

These tests ask for one user's data using another user's session. The route checks are skipped on
purpose: the point is what the database returns if one of them is ever wrong.
"""

import uuid

import httpx
import pytest
from conftest import STACK, create_mock_jwt
from fastapi import HTTPException

from app.core.supabase import create_user_client, get_supabase_client
from app.models.enums import UserRole
from app.services import appointment_service, chat_service, doctor_service


def new_user(role: UserRole) -> tuple:
    user_id = str(uuid.uuid4())
    return user_id, create_mock_jwt(user_id, "user@tests.invalid", role, "Test Person")


@pytest.fixture
def owner() -> tuple:
    return new_user(UserRole.PATIENT)


@pytest.fixture
def stranger_db():
    client = create_user_client(new_user(UserRole.PATIENT)[1])
    yield client
    client.aclose()


def test_user_session_reads_own_rows_only(owner, stranger_db):
    user_id, token = owner
    conversation = chat_service.create_conversation(user_id)
    own_db = create_user_client(token)
    try:
        listed = chat_service.list_patient_conversations(user_id, own_db)
        assert [row["id"] for row in listed] == [conversation["id"]]
        assert len(chat_service.read_messages(conversation["id"], own_db)) == 1
    finally:
        own_db.aclose()

    assert chat_service.list_patient_conversations(user_id, stranger_db) == []
    assert chat_service.read_messages(conversation["id"], stranger_db) == []


def test_a_wrong_route_check_still_cannot_expose_appointments(stranger_db, client):
    patient_id, _ = new_user(UserRole.PATIENT)
    doctor_user = "a0000000-0000-0000-0000-000000000003"
    admin = appointment_service._get_client()
    doctor_id = admin.table("doctor_profiles").select("id").eq("user_id", doctor_user).execute().data[0]["id"]
    admin.table("appointments").insert({"patient_id": patient_id, "doctor_id": doctor_id}).execute()

    rows = appointment_service.get_user_appointments(patient_id, UserRole.PATIENT, None, stranger_db)
    assert rows == []
    # The row exists, so the empty list above is RLS at work
    assert admin.table("appointments").select("id").eq("patient_id", patient_id).execute().data


def test_a_wrong_route_check_still_cannot_expose_credentials(client, stranger_db):
    user_id, token = new_user(UserRole.DOCTOR)
    doctor_service.get_supabase_admin_client().table("doctor_profiles").insert(
        {"user_id": user_id, "city": "Dhaka"}
    ).execute()
    res = client.post(
        "/doctors/me/credentials",
        headers={"Authorization": f"Bearer {token}"},
        data={"document_type": "bmdc_license"},
        files={"file": ("a.pdf", b"%PDF-1.4 x", "application/pdf")},
    )
    assert res.status_code == 200
    assert doctor_service.list_my_credentials(user_id, stranger_db) == []


def test_no_silent_fallback_when_the_service_key_is_missing(monkeypatch):
    monkeypatch.setattr(chat_service, "get_supabase_admin_client", lambda: None)
    with pytest.raises(HTTPException) as exc:
        chat_service.create_conversation(str(uuid.uuid4()))
    assert exc.value.status_code == 503


def anon_get(path: str) -> httpx.Response:
    anon = STACK["ANON_KEY"]
    return httpx.get(
        f"{STACK['API_URL']}/rest/v1/{path}",
        headers={"apikey": anon, "Authorization": f"Bearer {anon}"},
    )


def test_public_doctor_view_lists_approved_doctors_only():
    rows = anon_get("public_doctors?select=id,full_name,verification_status").json()
    assert rows
    assert {row["verification_status"] for row in rows} == {"approved"}


@pytest.mark.parametrize("column", ["phone", "user_id", "sync_status"])
def test_public_doctor_view_hides_private_columns(column):
    assert anon_get(f"public_doctors?select={column}").status_code == 400


def test_public_doctor_view_cannot_be_written():
    anon = STACK["ANON_KEY"]
    res = httpx.delete(
        f"{STACK['API_URL']}/rest/v1/public_doctors?id=not.is.null",
        headers={"apikey": anon, "Authorization": f"Bearer {anon}"},
    )
    assert res.status_code >= 400


def test_login_does_not_change_the_shared_client(client):
    email = f"{uuid.uuid4().hex}@example.com"
    body = {"email": email, "password": "long-enough-1"}
    assert client.post("/auth/register-patient", json={**body, "full_name": "New"}).status_code == 201
    assert client.post("/auth/login", json=body).status_code == 200

    # A session left on the shared client would make this return that user's profile
    assert get_supabase_client().table("profiles").select("id").execute().data == []
