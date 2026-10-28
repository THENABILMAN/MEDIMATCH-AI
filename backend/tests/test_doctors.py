import pytest
from fastapi import status
from fastapi.testclient import TestClient
from app.models.enums import UserRole, VerificationStatus


def test_public_search_returns_only_approved_doctors(client: TestClient):
    """Public search must strictly return ONLY approved doctors.
    
    Pending, suspended, and rejected demo doctors seeded in the database
    must never be exposed in public search results.
    """
    response = client.get("/doctors/search")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "items" in data
    assert data["total"] >= 1

    for doctor in data["items"]:
        # Must be approved
        assert doctor["verification_status"] == VerificationStatus.APPROVED.value
        # Private fields must never leak in public search
        assert "credentials" not in doctor
        assert "phone" not in doctor
        assert "user_id" not in doctor
        # Must not contain demo pending or suspended flags in title
        assert "Pending" not in doctor["full_name"]
        assert "Suspended" not in doctor["full_name"]
        assert "Rejected" not in doctor["full_name"]


def test_public_doctor_detail_endpoint_approved(client: TestClient):
    """An approved doctor profile is publicly viewable by ID."""
    # Seeded approved doctor
    doctor_id = "d2000000-0000-0000-0000-000000000001"  # Dr. Kazi Ahmed (Neurologist)
    response = client.get(f"/doctors/{doctor_id}")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == doctor_id
    assert data["verification_status"] == VerificationStatus.APPROVED.value
    assert "Neurology" in [s["name"] for s in data["specialties"]]
    # Ensure private fields are sanitized
    assert "phone" not in data
    assert "credentials" not in data


def test_unapproved_doctor_detail_returns_404(client: TestClient):
    """Attempting to access a pending or suspended doctor's public detail endpoint must return 404."""
    # Seeded pending doctor
    pending_id = "d2000000-0000-0000-0000-000000000007"
    resp_pending = client.get(f"/doctors/{pending_id}")
    assert resp_pending.status_code == status.HTTP_404_NOT_FOUND

    # Seeded suspended doctor
    suspended_id = "d2000000-0000-0000-0000-000000000009"
    resp_suspended = client.get(f"/doctors/{suspended_id}")
    assert resp_suspended.status_code == status.HTTP_404_NOT_FOUND


def test_search_filter_by_city(client: TestClient):
    """Search correctly filters by city."""
    response = client.get("/doctors/search?city=Chittagong")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total"] >= 1
    for doctor in data["items"]:
        assert doctor["city"].lower() == "chittagong"


def test_search_filter_by_specialty(client: TestClient):
    """Search correctly filters by specialty name."""
    response = client.get("/doctors/search?specialty=Neurology")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total"] >= 1
    for doctor in data["items"]:
        spec_names = [s["name"] for s in doctor["specialties"]]
        assert "Neurology" in spec_names


def test_search_filter_by_fee_and_experience(client: TestClient):
    """Search filters by max fee and min experience."""
    response = client.get("/doctors/search?max_fee=1200&min_experience=10")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    for doctor in data["items"]:
        assert doctor["consultation_fee"] <= 1200.0
        assert doctor["years_experience"] >= 10


def test_search_sorting(client: TestClient):
    """Search supports sorting by fee ascending and descending."""
    res_asc = client.get("/doctors/search?sort_by=fee_asc")
    assert res_asc.status_code == status.HTTP_200_OK
    items_asc = res_asc.json()["items"]
    fees_asc = [d["consultation_fee"] for d in items_asc]
    assert fees_asc == sorted(fees_asc)


def test_doctor_can_get_own_profile(client: TestClient, doctor_token: str):
    """A doctor can fetch their own profile via /doctors/me/profile."""
    # Seeded demo doctor user_id: a0000000-0000-0000-0000-000000000003
    from conftest import create_mock_jwt
    demo_doc_token = create_mock_jwt(
        "a0000000-0000-0000-0000-000000000003",
        "doctor@medimatch.test",
        UserRole.DOCTOR,
        "Dr. Tanvir Hasan",
    )
    headers = {"Authorization": f"Bearer {demo_doc_token}"}
    response = client.get("/doctors/me/profile", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["user_id"] == "a0000000-0000-0000-0000-000000000003"
    assert data["city"] == "Dhaka"


def test_doctor_update_resets_status_to_pending(client: TestClient):
    """A doctor modifying their profile resets their status to pending."""
    from conftest import create_mock_jwt
    demo_doc_token = create_mock_jwt(
        "a0000000-0000-0000-0000-000000000003",
        "doctor@medimatch.test",
        UserRole.DOCTOR,
        "Dr. Tanvir Hasan",
    )
    headers = {"Authorization": f"Bearer {demo_doc_token}"}
    payload = {
        "bio": "Updated clinical bio for demo doctor",
        "consultation_fee": 1800.0,
        "clinic_name": "Square Hospital, New Wing",
        "city": "Dhaka",
        "specialty_ids": ["11111111-0000-0000-0000-000000000002"],
    }
    try:
        response = client.put("/doctors/me/profile", headers=headers, json=payload)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["consultation_fee"] == 1800.0
        # Crucial Rule: Status resets to pending upon edit!
        assert data["verification_status"] == VerificationStatus.PENDING.value
    finally:
        from app.core.supabase import get_supabase_admin_client
        admin_client = get_supabase_admin_client()
        if admin_client:
            admin_client.table("doctor_profiles").update({"verification_status": "approved"}).eq("id", "d0000000-0000-0000-0000-000000000000").execute()


def test_doctor_upload_credentials(client: TestClient):
    """A doctor can upload a credential record."""
    from conftest import create_mock_jwt
    demo_doc_token = create_mock_jwt(
        "a0000000-0000-0000-0000-000000000003",
        "doctor@medimatch.test",
        UserRole.DOCTOR,
        "Dr. Tanvir Hasan",
    )
    headers = {"Authorization": f"Bearer {demo_doc_token}"}
    response = client.post(
        "/doctors/me/credentials",
        headers=headers,
        data={
            "document_type": "bmdc_license",
            "file_path": "a0000000-0000-0000-0000-000000000003/sample_bmdc_license.pdf",
        },
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["document_type"] == "bmdc_license"
    assert "sample_bmdc_license.pdf" in data["file_path"]
