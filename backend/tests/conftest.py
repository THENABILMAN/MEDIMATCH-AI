"""Test setup. Integration tests only ever run against the local Supabase stack.

These settings are applied before the app is imported, so values in .env cannot reach the
suite: a real project once picked up approved fake doctors from these tests.
"""

import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlsplit

import jwt
import psycopg2
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
LOCAL_HOSTS = {"127.0.0.1", "localhost"}
INTEGRATION_FILES = {
    "test_access_rules.py",
    "test_abuse_rules.py",
    "test_admin.py",
    "test_appointments.py",
    "test_auth.py",
    "test_booking_rules.py",
    "test_chat_api.py",
    "test_conversation_state.py",
    "test_data_access.py",
    "test_doctors.py",
    "test_recommendations.py",
    "test_retrieval_rules.py",
    "test_rls.py",
    "test_sync.py",
}


def assert_local(url: str) -> None:
    """Stops the suite before it can touch anything but this machine."""
    if urlsplit(url).hostname not in LOCAL_HOSTS:
        raise RuntimeError(f"Tests only run against local Supabase, not {urlsplit(url).hostname}")


def _local_stack() -> Optional[Dict[str, str]]:
    """Reads connection details from the environment (CI) or the Supabase CLI."""
    if os.environ.get("TEST_SUPABASE_URL"):
        return {
            "API_URL": os.environ["TEST_SUPABASE_URL"],
            "DB_URL": os.environ["TEST_DATABASE_URL"],
            "ANON_KEY": os.environ["TEST_SUPABASE_ANON_KEY"],
            "SERVICE_ROLE_KEY": os.environ["TEST_SUPABASE_SERVICE_ROLE_KEY"],
            "JWT_SECRET": os.environ["TEST_SUPABASE_JWT_SECRET"],
        }

    npx = shutil.which("npx")
    if not npx:
        return None
    try:
        result = subprocess.run(
            [npx, "-y", "supabase@latest", "status", "-o", "json"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=60,
        )
        return json.loads(result.stdout) if result.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return None


STACK = _local_stack()
if STACK:
    assert_local(STACK["API_URL"])
    assert_local(STACK["DB_URL"])

os.environ.update(
    {
        "ENVIRONMENT": "development",
        "SUPABASE_URL": STACK["API_URL"] if STACK else "",
        "SUPABASE_ANON_KEY": STACK["ANON_KEY"] if STACK else "",
        "SUPABASE_SERVICE_ROLE_KEY": STACK["SERVICE_ROLE_KEY"] if STACK else "",
        "DATABASE_URL": STACK["DB_URL"] if STACK else "",
        "PINECONE_API_KEY": "",
        "OPENROUTER_API_KEY": "",
        "EMBEDDING_PROVIDER": "fake",
        "RATE_LIMIT_ENABLED": "false",
        "SYNC_IN_BACKGROUND": "false",
    }
)

from fastapi import HTTPException  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.api import deps  # noqa: E402
from app.main import app  # noqa: E402
from app.models.enums import UserRole  # noqa: E402


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        if item.path.name in INTEGRATION_FILES:
            item.add_marker(pytest.mark.integration)


def pytest_collection_finish(session: pytest.Session) -> None:
    """A missing database must stop the run, not look like a pile of failures."""
    if not any(item.get_closest_marker("integration") for item in session.items):
        return
    if session.config.option.collectonly:
        return
    if not STACK:
        pytest.exit(
            "Local Supabase is not running. Run `npx supabase start`, "
            "or use `-m 'not integration'` for offline tests.",
            returncode=2,
        )

    from scripts.seed import run_seed

    run_seed()


def _decode_test_token(token: str) -> Dict[str, Any]:
    try:
        payload = jwt.decode(token, options={"verify_signature": False})
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc
    return {"sub": payload["sub"], "email": payload.get("email")}


@pytest.fixture(scope="session", autouse=True)
def _trust_test_tokens():
    """Replaces token verification for the suite. Production code has no such path."""
    patcher = pytest.MonkeyPatch()
    patcher.setattr(deps, "verify_supabase_token", _decode_test_token)
    yield
    patcher.undo()


@pytest.fixture(scope="session")
def client() -> TestClient:
    return TestClient(app)


def ensure_user(user_id: str, role: UserRole, full_name: str) -> None:
    """Gives a test identity a real row, since roles only ever come from profiles."""
    if not STACK:
        return
    conn = psycopg2.connect(STACK["DB_URL"])
    try:
        with conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO auth.users (id, aud, role, email)
                VALUES (%s, 'authenticated', 'authenticated', %s)
                ON CONFLICT DO NOTHING
                """,
                (user_id, f"{user_id}@tests.invalid"),
            )
            cur.execute(
                """
                INSERT INTO public.profiles (id, role, full_name) VALUES (%s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET role = EXCLUDED.role, full_name = EXCLUDED.full_name
                """,
                (user_id, role.value, full_name),
            )
    finally:
        conn.close()


def create_mock_jwt(user_id: str, email: str, role: UserRole, full_name: str = "Test User") -> str:
    """Builds a token for a test user and makes sure that user exists."""
    ensure_user(user_id, role, full_name)
    claims = {
        "sub": user_id,
        "email": email,
        "role": "authenticated",
        "aud": "authenticated",
        "exp": int(time.time()) + 3600,
    }
    return jwt.encode(claims, STACK["JWT_SECRET"] if STACK else "x" * 32, algorithm="HS256")


@pytest.fixture
def patient_user_id() -> str:
    return "11111111-1111-1111-1111-111111111111"


@pytest.fixture
def other_patient_user_id() -> str:
    return "22222222-2222-2222-2222-222222222222"


@pytest.fixture
def doctor_user_id() -> str:
    return "33333333-3333-3333-3333-333333333333"


@pytest.fixture
def admin_user_id() -> str:
    return "99999999-9999-9999-9999-999999999999"


@pytest.fixture
def patient_token(patient_user_id: str) -> str:
    return create_mock_jwt(patient_user_id, "patient@tests.invalid", UserRole.PATIENT, "Patient Alice")


@pytest.fixture
def other_patient_token(other_patient_user_id: str) -> str:
    return create_mock_jwt(other_patient_user_id, "other@tests.invalid", UserRole.PATIENT, "Patient Bob")


@pytest.fixture
def doctor_token(doctor_user_id: str) -> str:
    return create_mock_jwt(doctor_user_id, "doctor@tests.invalid", UserRole.DOCTOR, "Dr. Sarah Khan")


@pytest.fixture
def admin_token(admin_user_id: str) -> str:
    return create_mock_jwt(admin_user_id, "admin@tests.invalid", UserRole.ADMIN, "System Admin")
