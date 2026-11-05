"""Role boundaries and input rules on the real API."""

import pytest
from conftest import create_mock_jwt
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings
from app.models.enums import UserRole

NOT_A_UUID = "not-a-uuid"


def headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def conversation_id(client: TestClient, patient_token: str) -> str:
    res = client.post("/chat/conversations", headers=headers(patient_token), json={})
    assert res.status_code == 201
    return res.json()["id"]


def test_test_environment_is_not_a_valid_setting():
    with pytest.raises(ValidationError):
        Settings(ENVIRONMENT="test", _env_file=None)


def test_admin_cannot_read_a_patient_conversation(client, admin_token, conversation_id):
    res = client.get(f"/chat/conversations/{conversation_id}", headers=headers(admin_token))
    assert res.status_code == 403


def test_admin_cannot_use_doctor_routes(client, admin_token):
    assert client.get("/doctors/me/profile", headers=headers(admin_token)).status_code == 403


def test_doctor_cannot_book_an_appointment(client, doctor_token):
    slot = "00000000-0000-0000-0000-000000000000"
    res = client.post("/appointments", headers=headers(doctor_token), json={"slot_id": slot})
    assert res.status_code == 403


def test_only_patients_can_request_recommendations(client, doctor_token):
    res = client.post("/recommendations", headers=headers(doctor_token), json={})
    assert res.status_code == 403


@pytest.mark.parametrize(
    "method, path",
    [
        ("get", f"/doctors/{NOT_A_UUID}"),
        ("get", f"/doctors/{NOT_A_UUID}/slots"),
        ("get", f"/doctors/credentials/{NOT_A_UUID}/url"),
        ("get", f"/chat/conversations/{NOT_A_UUID}"),
        ("post", f"/appointments/{NOT_A_UUID}/cancel"),
    ],
)
def test_malformed_ids_are_rejected(client, patient_token, method, path):
    res = getattr(client, method)(path, headers=headers(patient_token))
    assert res.status_code == 422


def test_malformed_slot_id_is_rejected(client, patient_token):
    res = client.post("/appointments", headers=headers(patient_token), json={"slot_id": NOT_A_UUID})
    assert res.status_code == 422


@pytest.mark.parametrize(
    "query", ["page=999999999999", "sort_by=bad", "max_fee=1e300", "min_experience=99999"]
)
def test_out_of_range_search_input_is_rejected(client, query):
    assert client.get(f"/doctors/search?{query}").status_code == 422


@pytest.mark.parametrize("city", ["%", "*", "_haka"])
def test_search_treats_wildcards_as_text(client, city):
    res = client.get("/doctors/search", params={"city": city})
    assert res.status_code == 200
    assert res.json()["total"] == 0


def test_oversized_doctor_profile_is_rejected(client):
    token = create_mock_jwt(
        "b0000000-0000-0000-0000-00000000000a", "cap@tests.invalid", UserRole.DOCTOR, "Dr. Cap"
    )
    body = {"qualifications": ["MBBS"] * 500, "city": "Dhaka"}
    res = client.put("/doctors/me/profile", headers=headers(token), json=body)
    assert res.status_code == 422


def test_recommendations_refuse_an_emergency(client, patient_token):
    res = client.post(
        "/recommendations", headers=headers(patient_token), json={"keywords": ["my chest hurts"]}
    )
    assert res.status_code == 200
    assert res.json()["recommendations"] == []
    assert res.json()["retrieval_mode"] == "emergency_blocked"


def test_a_stranger_gets_no_access_through_an_emergency_message(
    client, other_patient_token, conversation_id
):
    res = client.post(
        f"/chat/conversations/{conversation_id}/messages",
        headers=headers(other_patient_token),
        json={"content": "severe chest pain"},
    )
    assert res.status_code == 403
