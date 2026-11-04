"""Attacks proven against the API during the audit. Each must stay closed."""

import uuid
from typing import Any

import httpx
import psycopg2
import pytest
from conftest import STACK, create_mock_jwt, ensure_user
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.rate_limit import limiter
from app.models.enums import UserRole

PDF = b"%PDF-1.4 test document"
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 32


def headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def sql(query: str, params: tuple = ()) -> Any:
    conn = psycopg2.connect(STACK["DB_URL"])
    try:
        with conn, conn.cursor() as cur:
            cur.execute(query, params)
            return cur.fetchone() if cur.description else None
    finally:
        conn.close()


@pytest.fixture
def doctor() -> dict[str, str]:
    """A fresh pending doctor."""
    user_id = str(uuid.uuid4())
    token = create_mock_jwt(user_id, "doc@tests.invalid", UserRole.DOCTOR, "Dr. Original")
    doctor_id = sql(
        "INSERT INTO public.doctor_profiles (user_id, city) VALUES (%s, 'Dhaka') RETURNING id",
        (user_id,),
    )[0]
    return {"user_id": user_id, "doctor_id": str(doctor_id), "token": token}


def upload(
    client: TestClient,
    token: str,
    content: bytes,
    name: str = "doc.pdf",
    kind: str = "application/pdf",
):
    return client.post(
        "/doctors/me/credentials",
        headers=headers(token),
        data={"document_type": "bmdc_license"},
        files={"file": (name, content, kind)},
    )


def test_credential_path_cannot_be_supplied_by_the_caller(client, doctor):
    res = client.post(
        "/doctors/me/credentials",
        headers=headers(doctor["token"]),
        data={
            "document_type": "bmdc_license",
            "file_path": f"{doctor['user_id']}/../victim/nid.pdf",
        },
    )
    assert res.status_code in (400, 422)


def test_uploaded_name_never_reaches_the_storage_path(client, doctor):
    res = upload(client, doctor["token"], PDF, name="../../../evil name.pdf")
    assert res.status_code == 200
    path = res.json()["file_path"]
    assert path.startswith(f"{doctor['user_id']}/")
    assert ".." not in path and "evil" not in path and path.endswith(".pdf")


@pytest.mark.parametrize(
    "content, name, kind",
    [
        (b"MZ\x90\x00 an executable", "cv.pdf", "application/pdf"),
        (b"<script>alert(1)</script>", "cv.png", "image/png"),
    ],
)
def test_disguised_files_are_refused(client, doctor, content, name, kind):
    assert upload(client, doctor["token"], content, name, kind).status_code == 415


def test_real_image_is_stored_with_its_true_type(client, doctor):
    res = upload(client, doctor["token"], PNG, name="scan.pdf", kind="application/pdf")
    assert res.status_code == 200
    assert res.json()["file_path"].endswith(".png")


def test_oversized_upload_is_refused(client, doctor):
    big = PDF + b"0" * (settings.MAX_UPLOAD_BYTES + 1)
    assert upload(client, doctor["token"], big).status_code == 413


def test_document_type_must_be_a_plain_identifier(client, doctor):
    res = client.post(
        "/doctors/me/credentials",
        headers=headers(doctor["token"]),
        data={"document_type": "x" * 500},
        files={"file": ("a.pdf", PDF, "application/pdf")},
    )
    assert res.status_code == 422


def test_admin_opening_a_credential_is_audited(client, doctor, admin_token):
    credential = upload(client, doctor["token"], PDF).json()
    res = client.get(f"/doctors/credentials/{credential['id']}/url", headers=headers(admin_token))
    assert res.status_code == 200
    count = sql(
        "SELECT count(*) FROM public.audit_logs WHERE action = 'VIEW_CREDENTIAL' AND target_id = %s",
        (credential["id"],),
    )[0]
    assert count == 1


def test_renaming_an_approved_doctor_needs_review_again(client, doctor):
    sql(
        "UPDATE public.doctor_profiles SET verification_status = 'approved' WHERE id = %s",
        (doctor["doctor_id"],),
    )
    res = client.patch(
        "/me", headers=headers(doctor["token"]), json={"full_name": "Prof. Famous Surgeon"}
    )
    assert res.status_code == 200
    status = sql(
        "SELECT verification_status::text FROM public.doctor_profiles WHERE id = %s",
        (doctor["doctor_id"],),
    )
    assert status[0] == "pending"


def test_suspended_doctor_cannot_rename(client, doctor):
    sql(
        "UPDATE public.doctor_profiles SET verification_status = 'suspended' WHERE id = %s",
        (doctor["doctor_id"],),
    )
    res = client.patch("/me", headers=headers(doctor["token"]), json={"full_name": "Someone Else"})
    assert res.status_code == 403
    name = sql("SELECT full_name FROM public.profiles WHERE id = %s", (doctor["user_id"],))[0]
    assert name == "Dr. Original"


def test_profile_audit_entries_hold_no_personal_details(client, patient_token, patient_user_id):
    res = client.patch("/me", headers=headers(patient_token), json={"phone": "01712345678"})
    assert res.status_code == 200
    metadata = sql(
        """SELECT metadata::text FROM public.audit_logs
           WHERE action = 'UPDATE_PROFILE' AND actor_id = %s
           ORDER BY created_at DESC LIMIT 1""",
        (patient_user_id,),
    )[0]
    assert "01712345678" not in metadata


def register_body(**overrides: Any) -> dict[str, Any]:
    body = {
        "email": f"{uuid.uuid4().hex}@example.com",
        "password": "long-enough-1",
        "full_name": "New Person",
    }
    return {**body, **overrides}


def test_short_password_is_refused(client):
    res = client.post("/auth/register-patient", json=register_body(password="abcdef"))
    assert res.status_code == 422


def test_unknown_registration_fields_are_refused(client):
    res = client.post("/auth/register-patient", json=register_body(role="admin"))
    assert res.status_code == 422


def test_duplicate_email_error_does_not_reveal_the_account(client):
    body = register_body()
    assert client.post("/auth/register-patient", json=body).status_code == 201
    res = client.post("/auth/register-patient", json=body)
    assert res.status_code == 400
    assert "already been" not in res.text.lower()


def test_registration_audit_does_not_store_the_email(client):
    body = register_body()
    user_id = client.post("/auth/register-patient", json=body).json()["user_id"]
    metadata = sql(
        "SELECT metadata::text FROM public.audit_logs WHERE action = 'REGISTER_PATIENT' AND actor_id = %s",
        (user_id,),
    )[0]
    assert body["email"] not in metadata


@pytest.fixture
def rate_limited(monkeypatch):
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", True)
    limiter.reset()
    yield
    limiter.reset()


def test_login_attempts_are_throttled(client, rate_limited):
    body = {"email": "nobody@example.com", "password": "wrong-password"}
    limit = settings.RATE_LIMIT_LOGIN
    codes = [client.post("/auth/login", json=body).status_code for _ in range(limit + 1)]
    assert codes[:-1] == [401] * limit
    assert codes[-1] == 429


def test_registration_is_throttled(client, rate_limited):
    codes = [
        client.post("/auth/register-patient", json=register_body()).status_code
        for _ in range(settings.RATE_LIMIT_REGISTER + 1)
    ]
    assert codes[-1] == 429


def test_chat_is_throttled_per_user(client, rate_limited, patient_token, other_patient_token):
    conversation = client.post(
        "/chat/conversations", headers=headers(patient_token), json={}
    ).json()["id"]
    url = f"/chat/conversations/{conversation}/messages"
    last = None
    for _ in range(settings.RATE_LIMIT_CHAT + 1):
        last = client.post(
            url, headers=headers(patient_token), json={"content": "severe chest pain"}
        )
    assert last.status_code == 429
    assert "retry-after" in {k.lower() for k in last.headers}

    other = client.post(
        "/chat/conversations", headers=headers(other_patient_token), json={}
    ).json()["id"]
    res = client.post(
        f"/chat/conversations/{other}/messages",
        headers=headers(other_patient_token),
        json={"content": "severe chest pain"},
    )
    assert res.status_code == 200


def rest(method: str, path: str, token: str, **kwargs: Any) -> httpx.Response:
    auth = {
        "apikey": STACK["ANON_KEY"],
        "Authorization": f"Bearer {token}",
        "Prefer": "return=representation",
    }
    return httpx.request(method, f"{STACK['API_URL']}/rest/v1/{path}", headers=auth, **kwargs)


def session_token() -> tuple:
    """A real Supabase session, since these checks go straight to PostgREST."""
    email = f"real{uuid.uuid4().hex}@example.com"
    service = STACK["SERVICE_ROLE_KEY"]
    created = httpx.post(
        f"{STACK['API_URL']}/auth/v1/admin/users",
        headers={"apikey": service, "Authorization": f"Bearer {service}"},
        json={"email": email, "password": "long-enough-1", "email_confirm": True},
    )
    created.raise_for_status()
    token = httpx.post(
        f"{STACK['API_URL']}/auth/v1/token?grant_type=password",
        headers={"apikey": STACK["ANON_KEY"]},
        json={"email": email, "password": "long-enough-1"},
    )
    token.raise_for_status()
    return created.json()["id"], token.json()["access_token"]


@pytest.mark.parametrize("column", ["ai_consent_at", "deleted_at"])
def test_clients_cannot_forge_their_own_timestamps(column):
    user_id, token = session_token()
    rest("PATCH", f"profiles?id=eq.{user_id}", token, json={column: "2026-01-01T00:00:00Z"})
    assert sql(f"SELECT {column} FROM public.profiles WHERE id = %s", (user_id,))[0] is None


def test_clients_cannot_change_their_own_name_directly():
    user_id, token = session_token()
    rest("PATCH", f"profiles?id=eq.{user_id}", token, json={"full_name": "Forged"})
    assert sql("SELECT full_name FROM public.profiles WHERE id = %s", (user_id,))[0] != "Forged"


def test_user_without_a_profile_cannot_create_an_admin_row():
    user_id, token = session_token()
    sql("DELETE FROM public.profiles WHERE id = %s", (user_id,))
    rest("POST", "profiles", token, json={"id": user_id, "role": "admin", "full_name": "x"})
    assert sql("SELECT count(*) FROM public.profiles WHERE id = %s", (user_id,))[0] == 0


def test_admin_client_cannot_forge_audit_entries():
    user_id, token = session_token()
    ensure_user(user_id, UserRole.ADMIN, "Admin")
    action = f"FORGED_{uuid.uuid4().hex}"
    rest("POST", "audit_logs", token, json={"action": action, "target_type": "x"})
    assert sql("SELECT count(*) FROM public.audit_logs WHERE action = %s", (action,))[0] == 0


def doctor_body(**overrides: Any) -> dict[str, Any]:
    return register_body(
        bio="Consultant neurologist",
        qualifications=["MBBS"],
        years_experience=9,
        consultation_fee=1200,
        clinic_name="Clinic",
        city="Dhaka",
        specialty_ids=["11111111-0000-0000-0000-000000000001"],
        **overrides,
    )


def test_doctor_registration_starts_pending_and_is_not_public(client):
    res = client.post("/auth/register-doctor", json=doctor_body())
    assert res.status_code == 201
    assert res.json()["verification_status"] == "pending"

    user_id = res.json()["user_id"]
    role, status = sql(
        """SELECT p.role::text, d.verification_status::text FROM public.profiles p
           JOIN public.doctor_profiles d ON d.user_id = p.id WHERE p.id = %s""",
        (user_id,),
    )
    assert (role, status) == ("doctor", "pending")
    doctor_id = sql("SELECT id FROM public.doctor_profiles WHERE user_id = %s", (user_id,))[0]
    assert client.get(f"/doctors/{doctor_id}").status_code == 404


def test_doctor_cannot_register_as_approved(client):
    res = client.post("/auth/register-doctor", json=doctor_body(verification_status="approved"))
    assert res.status_code == 422


def test_failed_doctor_setup_leaves_no_account_behind(client):
    body = doctor_body()
    body["specialty_ids"] = ["00000000-0000-0000-0000-00000000dead"]
    assert client.post("/auth/register-doctor", json=body).status_code == 400
    assert sql("SELECT count(*) FROM auth.users WHERE email = %s", (body["email"],))[0] == 0


def test_real_login_returns_a_session_and_role(client):
    body = register_body()
    client.post("/auth/register-patient", json=body)
    res = client.post("/auth/login", json={"email": body["email"], "password": body["password"]})
    assert res.status_code == 200
    assert res.json()["role"] == "patient" and res.json()["access_token"]


def test_a_real_token_works_end_to_end_without_the_test_shortcut(client, monkeypatch):
    from app.api import deps
    from app.core.security import verify_supabase_token

    monkeypatch.setattr(deps, "verify_supabase_token", verify_supabase_token)
    body = register_body()
    client.post("/auth/register-patient", json=body)
    token = client.post(
        "/auth/login", json={"email": body["email"], "password": body["password"]}
    ).json()["access_token"]

    assert client.get("/me", headers=headers(token)).json()["email"] == body["email"]
    assert client.get("/me", headers=headers(token + "x")).status_code == 401
    forged = create_mock_jwt(str(uuid.uuid4()), "x@tests.invalid", UserRole.ADMIN, "Forged")
    assert client.get("/admin/doctors", headers=headers(forged)).status_code == 401
