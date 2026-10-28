import pytest
from fastapi import status
from fastapi.testclient import TestClient
from conftest import create_mock_jwt
from app.models.enums import UserRole, VerificationStatus


@pytest.fixture
def admin_headers(admin_user_id: str) -> dict:
    # Use seeded admin user id
    token = create_mock_jwt(
        "a0000000-0000-0000-0000-000000000001",
        "admin@medimatch.test",
        UserRole.ADMIN,
        "System Admin",
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def patient_headers() -> dict:
    token = create_mock_jwt(
        "a0000000-0000-0000-0000-000000000002",
        "patient@medimatch.test",
        UserRole.PATIENT,
        "Patient Karim",
    )
    return {"Authorization": f"Bearer {token}"}


def test_non_admin_forbidden_on_admin_routes(client: TestClient, patient_headers: dict):
    """Patients and doctors must receive 403 Forbidden on all admin endpoints."""
    # List doctors
    res = client.get("/admin/doctors", headers=patient_headers)
    assert res.status_code == status.HTTP_403_FORBIDDEN

    # Audit logs
    res_audit = client.get("/admin/audit-logs", headers=patient_headers)
    assert res_audit.status_code == status.HTTP_403_FORBIDDEN

    # Approve action
    res_app = client.post("/admin/doctors/fake-id/approve", headers=patient_headers)
    assert res_app.status_code == status.HTTP_403_FORBIDDEN


def test_admin_list_doctors_with_filter(client: TestClient, admin_headers: dict):
    """Admin can list doctors with status filter."""
    res = client.get("/admin/doctors?status=pending", headers=admin_headers)
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert "items" in data
    assert data["total"] >= 1
    for doc in data["items"]:
        assert doc["verification_status"] == VerificationStatus.PENDING.value


def test_admin_reject_doctor_with_reason(client: TestClient, admin_headers: dict):
    """Admin can reject a doctor profile with a mandatory reason."""
    doctor_id = "d2000000-0000-0000-0000-000000000008"  # Dr. Zubaida Khan
    payload = {"reason": "BMDC license number could not be authenticated"}
    try:
        res = client.post(f"/admin/doctors/{doctor_id}/reject", headers=admin_headers, json=payload)
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        assert data["verification_status"] == VerificationStatus.REJECTED.value
        assert data["reason"] == payload["reason"]
    finally:
        # Restore to pending for test isolation
        from app.core.supabase import get_supabase_admin_client
        admin_client = get_supabase_admin_client()
        if admin_client:
            admin_client.table("doctor_profiles").update({"verification_status": "pending"}).eq("id", doctor_id).execute()


def test_admin_suspend_doctor_removes_from_search(client: TestClient, admin_headers: dict):
    """Suspending a doctor sets status to suspended and prevents appearing in search."""
    doctor_id = "d2000000-0000-0000-0000-000000000002"  # Dr. Samira Rahman (initially approved)
    payload = {"reason": "Temporary suspension pending certificate renewal"}
    try:
        res = client.post(f"/admin/doctors/{doctor_id}/suspend", headers=admin_headers, json=payload)
        assert res.status_code == status.HTTP_200_OK

        # Detail endpoint must now return 404
        detail_res = client.get(f"/doctors/{doctor_id}")
        assert detail_res.status_code == status.HTTP_404_NOT_FOUND
    finally:
        # Restore to approved
        from app.core.supabase import get_supabase_admin_client
        admin_client = get_supabase_admin_client()
        if admin_client:
            admin_client.table("doctor_profiles").update({"verification_status": "approved"}).eq("id", doctor_id).execute()


def test_admin_approval_makes_doctor_searchable(client: TestClient, admin_headers: dict):
    """CRITICAL FLOW: A pending doctor only becomes searchable AFTER admin approval."""
    doctor_id = "d2000000-0000-0000-0000-000000000007"  # Dr. Jamil Siddiqui (Pending)

    try:
        # 1. Before approval: detail must return 404
        pre_check = client.get(f"/doctors/{doctor_id}")
        assert pre_check.status_code == status.HTTP_404_NOT_FOUND

        # 2. Admin approves doctor
        approve_res = client.post(f"/admin/doctors/{doctor_id}/approve", headers=admin_headers)
        assert approve_res.status_code == status.HTTP_200_OK
        assert approve_res.json()["verification_status"] == VerificationStatus.APPROVED.value

        # 3. After approval: detail endpoint must now return 200 OK!
        post_check = client.get(f"/doctors/{doctor_id}")
        assert post_check.status_code == status.HTTP_200_OK
        assert post_check.json()["id"] == doctor_id
        assert post_check.json()["verification_status"] == VerificationStatus.APPROVED.value
    finally:
        # Restore to pending
        from app.core.supabase import get_supabase_admin_client
        admin_client = get_supabase_admin_client()
        if admin_client:
            admin_client.table("doctor_profiles").update({"verification_status": "pending"}).eq("id", doctor_id).execute()
    assert post_check.json()["id"] == doctor_id
    assert post_check.json()["verification_status"] == VerificationStatus.APPROVED.value


def test_admin_audit_logs_pagination(client: TestClient, admin_headers: dict):
    """Admin can view paginated audit logs."""
    res = client.get("/admin/audit-logs?limit=5&offset=0", headers=admin_headers)
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert "items" in data
    assert "total" in data
    assert len(data["items"]) <= 5
    if data["items"]:
        first = data["items"][0]
        assert "action" in first
        assert "target_type" in first


def test_admin_specialty_crud(client: TestClient, admin_headers: dict):
    """Admin can create, view, update, and delete specialties."""
    # 1. Create specialty
    create_payload = {
        "name": "Dermatology",
        "description": "Diagnosis and management of skin, hair, and nail conditions.",
    }
    res_create = client.post("/admin/specialties", headers=admin_headers, json=create_payload)
    assert res_create.status_code == status.HTTP_201_CREATED
    spec = res_create.json()
    specialty_id = spec["id"]
    assert spec["name"] == "Dermatology"

    # 2. List specialties
    res_list = client.get("/admin/specialties", headers=admin_headers)
    assert res_list.status_code == status.HTTP_200_OK
    names = [s["name"] for s in res_list.json()]
    assert "Dermatology" in names

    # 3. Update specialty
    update_payload = {"description": "Updated skin & aesthetic clinical dermatology care."}
    res_update = client.put(f"/admin/specialties/{specialty_id}", headers=admin_headers, json=update_payload)
    assert res_update.status_code == status.HTTP_200_OK
    assert res_update.json()["description"] == update_payload["description"]

    # 4. Delete specialty
    res_del = client.delete(f"/admin/specialties/{specialty_id}", headers=admin_headers)
    assert res_del.status_code == status.HTTP_200_OK
