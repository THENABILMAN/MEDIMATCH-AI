"""Consent, retention, and how the API behaves as a service."""

import json
import logging
import uuid
from datetime import UTC, datetime, timedelta

import psycopg2
import pytest
from conftest import STACK, create_mock_jwt
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.logging import JsonFormatter, configure_logging
from app.main import app
from app.models.enums import UserRole
from app.services.account_service import purge_expired_chats


def sql(query: str, params: tuple = ()):
    conn = psycopg2.connect(STACK["DB_URL"])
    try:
        with conn, conn.cursor() as cur:
            cur.execute(query, params)
            return cur.fetchall() if cur.description else None
    finally:
        conn.close()


@pytest.fixture
def patient() -> dict:
    user_id = str(uuid.uuid4())
    token = create_mock_jwt(user_id, "p@tests.invalid", UserRole.PATIENT, "Pat")
    return {"id": user_id, "headers": {"Authorization": f"Bearer {token}"}}


def conversation(client, patient) -> str:
    return client.post("/chat/conversations", headers=patient["headers"], json={}).json()["id"]


def withdraw_consent(client, patient) -> None:
    assert (
        client.patch("/me", headers=patient["headers"], json={"ai_consent": False}).status_code
        == 200
    )


def test_no_consent_means_no_symptoms_are_stored(client, patient):
    chat = conversation(client, patient)
    withdraw_consent(client, patient)

    res = client.post(
        f"/chat/conversations/{chat}/messages",
        headers=patient["headers"],
        json={"content": "itchy rash for a week"},
    )
    assert res.status_code == 403
    assert (
        sql(
            "SELECT count(*) FROM messages WHERE conversation_id = %s AND sender = 'patient'",
            (chat,),
        )[0][0]
        == 0
    )


def test_an_emergency_still_gets_the_alert_without_consent_and_stores_nothing(client, patient):
    chat = conversation(client, patient)
    withdraw_consent(client, patient)

    res = client.post(
        f"/chat/conversations/{chat}/messages",
        headers=patient["headers"],
        json={"content": "my chest hurts"},
    )
    assert res.status_code == 200
    assert res.json()["is_emergency"] is True
    assert (
        sql(
            "SELECT count(*) FROM messages WHERE conversation_id = %s AND sender = 'patient'",
            (chat,),
        )[0][0]
        == 0
    )
    assert (
        sql(
            "SELECT count(*) FROM patient_symptom_sessions WHERE patient_id = %s", (patient["id"],)
        )[0][0]
        == 0
    )


def test_old_chats_are_purged_and_recent_ones_stay(client, patient):
    old_chat = conversation(client, patient)
    new_chat = conversation(client, patient)
    past = datetime.now(UTC) - timedelta(days=settings.CHAT_RETENTION_DAYS + 1)
    # The trigger keeps updated_at honest, so backdating needs it out of the way
    sql(
        """ALTER TABLE conversations DISABLE TRIGGER tr_conversations_updated_at;
           UPDATE conversations SET updated_at = %s WHERE id = %s;
           ALTER TABLE conversations ENABLE TRIGGER tr_conversations_updated_at;""",
        (past, old_chat),
    )
    sql(
        "INSERT INTO patient_symptom_sessions (patient_id, raw_symptoms, created_at) VALUES (%s, 'x', %s)",
        (patient["id"], past),
    )

    assert purge_expired_chats() >= 1
    assert sql("SELECT count(*) FROM conversations WHERE id = %s", (old_chat,))[0][0] == 0
    assert sql("SELECT count(*) FROM conversations WHERE id = %s", (new_chat,))[0][0] == 1
    assert (
        sql(
            "SELECT count(*) FROM patient_symptom_sessions WHERE patient_id = %s", (patient["id"],)
        )[0][0]
        == 0
    )


def test_closing_an_account_removes_chat_and_identity(client):
    email = f"{uuid.uuid4().hex}@example.com"
    body = {
        "email": email,
        "password": "long-enough-1",
        "full_name": "Real Person",
        "phone": "01712345678",
    }
    user_id = client.post("/auth/register-patient", json=body).json()["user_id"]
    patient = {
        "id": user_id,
        "headers": {
            "Authorization": f"Bearer {create_mock_jwt(user_id, email, UserRole.PATIENT, 'Real Person')}"
        },
    }

    chat = conversation(client, patient)
    assert client.delete("/me", headers=patient["headers"]).status_code == 200
    assert sql("SELECT count(*) FROM conversations WHERE id = %s", (chat,))[0][0] == 0
    name, phone, consent = sql(
        "SELECT full_name, phone, ai_consent_at FROM profiles WHERE id = %s", (user_id,)
    )[0]
    assert (name, phone, consent) == ("Deleted Patient", None, None)

    # The sign-in identity is gone too, so the old password no longer works
    assert email not in sql("SELECT email FROM auth.users WHERE id = %s", (user_id,))[0][0]
    assert (
        client.post("/auth/login", json={"email": email, "password": body["password"]}).status_code
        == 401
    )


def test_every_response_has_a_request_id(client):
    res = client.get("/health")
    assert uuid.UUID(res.headers["x-request-id"])


def test_a_sensible_caller_request_id_is_kept(client):
    res = client.get("/health", headers={"X-Request-ID": "abc-123"})
    assert res.headers["x-request-id"] == "abc-123"


def test_a_hostile_request_id_is_replaced(client):
    res = client.get("/health", headers={"X-Request-ID": "x" * 500})
    assert res.headers["x-request-id"] != "x" * 500


def test_errors_keep_detail_and_add_code_and_request_id(client):
    res = client.get("/doctors/00000000-0000-0000-0000-000000000000")
    assert res.status_code == 404
    body = res.json()
    assert isinstance(body["detail"], str)
    assert body["code"] == "not_found"
    assert body["request_id"] == res.headers["x-request-id"]


def test_validation_errors_keep_the_list_the_web_app_reads(client):
    res = client.get("/doctors/not-a-uuid")
    assert res.status_code == 422
    body = res.json()
    assert isinstance(body["detail"], list) and body["detail"][0]["msg"]
    assert body["code"] == "validation_error"


def test_validation_errors_do_not_echo_what_was_sent(client):
    res = client.post(
        "/auth/login", json={"email": "not-an-email", "password": "my-secret-password" + "x" * 80}
    )
    assert res.status_code == 422
    assert "my-secret-password" not in res.text


def test_unexpected_errors_reveal_nothing(monkeypatch):
    def explode():
        raise RuntimeError("database password is hunter2")

    monkeypatch.setattr("app.api.v1.health.settings", None)
    client = TestClient(app, raise_server_exceptions=False)
    monkeypatch.setattr("app.main.list_specialties", explode)
    res = client.get("/specialties")
    assert res.status_code == 500
    assert "hunter2" not in res.text
    body = res.json()
    assert body["code"] == "internal_error"
    assert body["request_id"]


def test_security_headers_are_set(client):
    headers = client.get("/health").headers
    assert headers["x-content-type-options"] == "nosniff"
    assert headers["x-frame-options"] == "DENY"
    assert "strict-origin" in headers["referrer-policy"]


def test_ready_reports_the_database(client):
    res = client.get("/ready")
    assert res.status_code == 200
    assert res.json()["checks"]["database"] == "ok"


def test_ready_fails_when_the_database_is_down(client, monkeypatch):
    monkeypatch.setattr("app.api.v1.health.get_supabase_client", lambda: None)
    res = client.get("/ready")
    assert res.status_code == 503
    assert res.json()["checks"]["database"] == "unavailable"


def test_health_does_not_reveal_the_environment(client):
    assert "environment" not in client.get("/health").json()


def test_docs_are_off_in_production():
    from app.main import create_app

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(settings, "ENVIRONMENT", "production")
        production = TestClient(create_app())
        assert production.get("/docs").status_code == 404
        assert production.get("/openapi.json").status_code == 404


def test_oversized_request_is_refused_before_it_is_read(client):
    res = client.post(
        "/auth/login",
        content=b"{}",
        headers={
            "content-length": str(settings.MAX_UPLOAD_BYTES * 2),
            "content-type": "application/json",
        },
    )
    assert res.status_code == 413


@pytest.mark.parametrize(
    "path, key",
    [("/chat/conversations", None), ("/appointments/me", None)],
)
def test_lists_accept_limit_and_offset(client, patient, path, key):
    assert client.get(f"{path}?limit=1&offset=0", headers=patient["headers"]).status_code == 200
    assert client.get(f"{path}?limit=100000", headers=patient["headers"]).status_code == 422


def test_conversation_list_honours_the_limit(client, patient):
    conversation(client, patient)
    conversation(client, patient)
    rows = client.get("/chat/conversations?limit=1", headers=patient["headers"]).json()
    assert len(rows) == 1


def test_logs_are_json_with_the_request_id():
    record = logging.LogRecord("t", logging.INFO, "f", 1, "hello %s", ("world",), None)
    line = json.loads(JsonFormatter().format(record))
    assert line["message"] == "hello world"
    assert line["level"] == "INFO"
    assert "request_id" in line


def test_request_logs_hold_no_query_strings_or_bodies(client, caplog):
    with caplog.at_level("INFO", logger="medimatch.request"):
        client.get("/doctors/search?city=Dhaka&specialty=secretword")
    lines = [r.getMessage() for r in caplog.records if r.name == "medimatch.request"]
    assert any("/doctors/search" in line for line in lines)
    assert not any("secretword" in line for line in lines)


def test_http_client_logs_are_off_because_they_hold_full_urls():
    configure_logging()
    assert logging.getLogger("httpx").getEffectiveLevel() >= logging.WARNING
