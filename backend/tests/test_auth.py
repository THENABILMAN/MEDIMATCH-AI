import pytest
from fastapi import APIRouter, Depends, status
from fastapi.testclient import TestClient
from app.api.deps import get_current_user, require_admin, require_doctor, require_patient
from app.main import app
from app.models.enums import UserRole
from app.schemas.profile import UserMeResponse

# Test-specific router to test role-based enforcement
test_router = APIRouter(prefix="/test-rbac")


@test_router.get("/admin-only")
def admin_only_route(current_user: UserMeResponse = Depends(require_admin)):
    return {"message": "Welcome Admin", "user_id": current_user.id}


@test_router.get("/doctor-only")
def doctor_only_route(current_user: UserMeResponse = Depends(require_doctor)):
    return {"message": "Welcome Doctor", "user_id": current_user.id}


@test_router.get("/patient-only")
def patient_only_route(current_user: UserMeResponse = Depends(require_patient)):
    return {"message": "Welcome Patient", "user_id": current_user.id}


app.include_router(test_router)


def test_unauthenticated_request_returns_401(client: TestClient):
    """Unauthenticated requests must return 401 Unauthorized."""
    response = client.get("/me")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_invalid_token_returns_401(client: TestClient):
    """Invalid token format must return 401 Unauthorized."""
    headers = {"Authorization": "Bearer invalid.token.value"}
    response = client.get("/me", headers=headers)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_patient_can_access_me(client: TestClient, patient_token: str, patient_user_id: str):
    """Authenticated patient can retrieve their own profile."""
    headers = {"Authorization": f"Bearer {patient_token}"}
    response = client.get("/me", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == patient_user_id
    assert data["role"] == UserRole.PATIENT.value


def test_role_escalation_prevention_via_patch_me(client: TestClient, patient_token: str):
    """A user attempting to escalate their role to admin via PATCH /me must be rejected.
    
    Pydantic config extra='forbid' strictly rejects extra fields like 'role'.
    """
    headers = {"Authorization": f"Bearer {patient_token}"}
    response = client.patch(
        "/me",
        headers=headers,
        json={"full_name": "Hacker Alice", "role": "admin"},
    )
    # Pydantic extra='forbid' returns 422 Unprocessable Entity
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_role_escalation_prevention_verification_status(client: TestClient, doctor_token: str):
    """A doctor attempting to self-approve verification_status must be rejected."""
    headers = {"Authorization": f"Bearer {doctor_token}"}
    response = client.patch(
        "/me",
        headers=headers,
        json={"doctor_profile": {"verification_status": "approved"}},
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_rbac_patient_cannot_access_admin_route(client: TestClient, patient_token: str):
    """Patient trying to access an admin-only route must receive 403 Forbidden."""
    headers = {"Authorization": f"Bearer {patient_token}"}
    response = client.get("/test-rbac/admin-only", headers=headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_rbac_patient_cannot_access_doctor_route(client: TestClient, patient_token: str):
    """Patient trying to access a doctor-only route must receive 403 Forbidden."""
    headers = {"Authorization": f"Bearer {patient_token}"}
    response = client.get("/test-rbac/doctor-only", headers=headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_rbac_doctor_cannot_access_admin_route(client: TestClient, doctor_token: str):
    """Doctor trying to access an admin-only route must receive 403 Forbidden."""
    headers = {"Authorization": f"Bearer {doctor_token}"}
    response = client.get("/test-rbac/admin-only", headers=headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_rbac_admin_can_access_admin_route(client: TestClient, admin_token: str):
    """Admin can successfully access admin-only routes."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = client.get("/test-rbac/admin-only", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["message"] == "Welcome Admin"
