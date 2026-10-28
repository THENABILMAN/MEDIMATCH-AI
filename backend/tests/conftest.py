import os
import pytest
import jwt
from fastapi.testclient import TestClient

# Ensure test environment settings
os.environ["ENVIRONMENT"] = "test"

from app.core.config import settings
from app.main import app
from app.models.enums import UserRole
from app.schemas.profile import UserMeResponse


@pytest.fixture(scope="session")
def client() -> TestClient:
    return TestClient(app)


def create_mock_jwt(user_id: str, email: str, role: UserRole, full_name: str = "Test User") -> str:
    """Helper to generate mock JWTs for unit and integration testing."""
    payload = {
        "sub": user_id,
        "email": email,
        "role": "authenticated",
        "app_metadata": {"role": role.value},
        "user_metadata": {
            "full_name": full_name,
            "role": role.value,
        },
    }
    return jwt.encode(payload, "secret-test-key", algorithm="HS256")


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
    return create_mock_jwt(patient_user_id, "patient@medimatch.test", UserRole.PATIENT, "Patient Alice")


@pytest.fixture
def other_patient_token(other_patient_user_id: str) -> str:
    return create_mock_jwt(other_patient_user_id, "other_patient@medimatch.test", UserRole.PATIENT, "Patient Bob")


@pytest.fixture
def doctor_token(doctor_user_id: str) -> str:
    return create_mock_jwt(doctor_user_id, "doctor@medimatch.test", UserRole.DOCTOR, "Dr. Sarah Khan")


@pytest.fixture
def admin_token(admin_user_id: str) -> str:
    return create_mock_jwt(admin_user_id, "admin@medimatch.test", UserRole.ADMIN, "System Admin")

