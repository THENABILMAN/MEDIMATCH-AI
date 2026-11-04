import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from fastapi import HTTPException, status
from app.core.supabase import contains_pattern, get_supabase_admin_client, get_supabase_client
from app.models.enums import VerificationStatus
from app.schemas.doctor import (
    AuditLogPaginatedResponse,
    AuditLogRead,
    SpecialtyCreate,
    SpecialtyUpdate,
)
from app.schemas.profile import DoctorProfileRead, SpecialtyRead
from app.services.audit_service import log_audit_event
from app.services.doctor_events import (
    on_doctor_approved,
    on_doctor_rejected,
    on_doctor_suspended,
)

logger = logging.getLogger(__name__)


DOCTOR_SORT_COLUMNS = {"created_at", "city", "years_experience", "consultation_fee", "verification_status"}
PATIENT_SORT_COLUMNS = {"created_at", "full_name"}


def _validated_sort(sort: str, allowed: set) -> str:
    if sort not in allowed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported sort column")
    return sort


def list_patients_for_admin(
    limit: int = 50,
    offset: int = 0,
    sort: str = "created_at",
    descending: bool = True,
    search: Optional[str] = None,
) -> Dict[str, Any]:
    """Lists active patient accounts with their appointment counts."""
    admin_client = get_supabase_admin_client()
    if not admin_client:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database service unavailable")

    query = (
        admin_client.table("profiles")
        .select("id, full_name, phone, created_at, appointments(count)", count="exact")
        .eq("role", "patient")
        .is_("deleted_at", "null")
        .order(_validated_sort(sort, PATIENT_SORT_COLUMNS), desc=descending)
    )
    if search:
        query = query.ilike("full_name", contains_pattern(search))

    res = query.range(offset, offset + limit - 1).execute()
    items = [
        {
            "id": row["id"],
            "full_name": row["full_name"],
            "phone": row.get("phone"),
            "created_at": row.get("created_at"),
            "appointment_count": (row.get("appointments") or [{}])[0].get("count", 0),
        }
        for row in res.data or []
    ]
    return {"items": items, "total": res.count or 0, "limit": limit, "offset": offset}


def list_doctors_for_admin(
    status_filter: Optional[VerificationStatus] = None,
    limit: int = 50,
    offset: int = 0,
    sort: str = "created_at",
    descending: bool = True,
) -> Dict[str, Any]:
    """Retrieve list of doctor profiles for administration, filterable by status."""
    admin_client = get_supabase_admin_client()
    if not admin_client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service unavailable",
        )

    query = (
        admin_client.table("doctor_profiles")
        .select("*, profiles!inner(full_name, phone), doctor_specialties(specialties(*)), doctor_credentials(*)", count="exact")
        .order(_validated_sort(sort, DOCTOR_SORT_COLUMNS), desc=descending)
    )

    if status_filter:
        query = query.eq("verification_status", status_filter.value)

    res = query.range(offset, offset + limit - 1).execute()
    total = res.count or 0
    items = []

    for doc in res.data or []:
        specs = []
        for ds in doc.get("doctor_specialties", []):
            s = ds.get("specialties")
            if s:
                specs.append(s)

        items.append({
            "id": doc["id"],
            "user_id": doc["user_id"],
            "full_name": doc.get("profiles", {}).get("full_name"),
            "phone": doc.get("profiles", {}).get("phone"),
            "bio": doc.get("bio"),
            "qualifications": doc.get("qualifications") or [],
            "years_experience": doc.get("years_experience", 0),
            "consultation_fee": float(doc.get("consultation_fee", 0.0)),
            "clinic_name": doc.get("clinic_name"),
            "city": doc.get("city", "Dhaka"),
            "verification_status": doc.get("verification_status"),
            "specialties": specs,
            "credentials": doc.get("doctor_credentials") or [],
            "created_at": doc.get("created_at"),
            "updated_at": doc.get("updated_at"),
        })

    return {"items": items, "total": total, "limit": limit, "offset": offset}


def approve_doctor(doctor_id: str, admin_id: str) -> Dict[str, Any]:
    """Approve a doctor's verification status, log audit, and notify event hook."""
    admin_client = get_supabase_admin_client()
    if not admin_client:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database service unavailable")

    # Verify doctor exists
    check = admin_client.table("doctor_profiles").select("id, verification_status").eq("id", doctor_id).execute()
    if not check.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor profile not found")

    old_status = check.data[0]["verification_status"]
    admin_client.table("doctor_profiles").update({
        "verification_status": VerificationStatus.APPROVED.value,
    }).eq("id", doctor_id).execute()

    log_audit_event(
        actor_id=admin_id,
        action="APPROVE_DOCTOR",
        target_type="doctor_profiles",
        target_id=doctor_id,
        metadata={"old_status": old_status, "new_status": VerificationStatus.APPROVED.value},
    )

    on_doctor_approved(doctor_id=doctor_id, admin_id=admin_id)

    return {
        "message": f"Doctor {doctor_id} has been approved successfully",
        "doctor_id": doctor_id,
        "verification_status": VerificationStatus.APPROVED.value,
    }


def reject_doctor(doctor_id: str, admin_id: str, reason: str) -> Dict[str, Any]:
    """Reject a doctor's verification with a mandatory reason."""
    if not reason or not reason.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Rejection reason is required")

    admin_client = get_supabase_admin_client()
    if not admin_client:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database service unavailable")

    check = admin_client.table("doctor_profiles").select("id, verification_status").eq("id", doctor_id).execute()
    if not check.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor profile not found")

    old_status = check.data[0]["verification_status"]
    admin_client.table("doctor_profiles").update({
        "verification_status": VerificationStatus.REJECTED.value,
    }).eq("id", doctor_id).execute()

    log_audit_event(
        actor_id=admin_id,
        action="REJECT_DOCTOR",
        target_type="doctor_profiles",
        target_id=doctor_id,
        metadata={"old_status": old_status, "new_status": VerificationStatus.REJECTED.value, "reason": reason.strip()},
    )

    on_doctor_rejected(doctor_id=doctor_id, admin_id=admin_id, reason=reason.strip())

    return {
        "message": f"Doctor {doctor_id} has been rejected",
        "doctor_id": doctor_id,
        "verification_status": VerificationStatus.REJECTED.value,
        "reason": reason.strip(),
    }


def suspend_doctor(doctor_id: str, admin_id: str, reason: str) -> Dict[str, Any]:
    """Suspend a doctor's profile, log audit, and notify event hook."""
    if not reason or not reason.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Suspension reason is required")

    admin_client = get_supabase_admin_client()
    if not admin_client:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database service unavailable")

    check = admin_client.table("doctor_profiles").select("id, verification_status").eq("id", doctor_id).execute()
    if not check.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor profile not found")

    old_status = check.data[0]["verification_status"]
    admin_client.table("doctor_profiles").update({
        "verification_status": VerificationStatus.SUSPENDED.value,
    }).eq("id", doctor_id).execute()

    log_audit_event(
        actor_id=admin_id,
        action="SUSPEND_DOCTOR",
        target_type="doctor_profiles",
        target_id=doctor_id,
        metadata={"old_status": old_status, "new_status": VerificationStatus.SUSPENDED.value, "reason": reason.strip()},
    )

    on_doctor_suspended(doctor_id=doctor_id, admin_id=admin_id, reason=reason.strip())

    return {
        "message": f"Doctor {doctor_id} has been suspended",
        "doctor_id": doctor_id,
        "verification_status": VerificationStatus.SUSPENDED.value,
        "reason": reason.strip(),
    }


def get_audit_logs(
    limit: int = 50,
    offset: int = 0,
    action: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
) -> AuditLogPaginatedResponse:
    """Retrieve paginated platform audit logs."""
    admin_client = get_supabase_admin_client()
    if not admin_client:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database service unavailable")

    query = admin_client.table("audit_logs").select("*", count="exact").order("created_at", desc=True)
    if action:
        query = query.eq("action", action)
    if date_from:
        query = query.gte("created_at", date_from.isoformat())
    if date_to:
        query = query.lte("created_at", date_to.isoformat())

    res = query.range(offset, offset + limit - 1).execute()
    total = res.count or 0
    items = [AuditLogRead.model_validate(row) for row in res.data or []]

    return AuditLogPaginatedResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


# ------------------------------------------------------------------------------
# Specialty CRUD Operations
# ------------------------------------------------------------------------------

def create_specialty(payload: SpecialtyCreate, admin_id: str) -> SpecialtyRead:
    admin_client = get_supabase_admin_client()
    if not admin_client:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database service unavailable")

    res = admin_client.table("specialties").insert({
        "name": payload.name.strip(),
        "description": payload.description,
    }).execute()

    if not res.data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to create specialty")

    row = res.data[0]
    log_audit_event(
        actor_id=admin_id,
        action="CREATE_SPECIALTY",
        target_type="specialties",
        target_id=str(row["id"]),
        metadata={"name": row["name"]},
    )

    return SpecialtyRead(id=str(row["id"]), name=row["name"], description=row.get("description"))


def list_specialties() -> List[SpecialtyRead]:
    client = get_supabase_client()
    if not client:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database service unavailable")

    res = client.table("specialties").select("*").order("name", desc=False).execute()
    return [
        SpecialtyRead(id=str(row["id"]), name=row["name"], description=row.get("description"))
        for row in res.data or []
    ]


def update_specialty(specialty_id: str, payload: SpecialtyUpdate, admin_id: str) -> SpecialtyRead:
    admin_client = get_supabase_admin_client()
    if not admin_client:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database service unavailable")

    updates = {}
    if payload.name is not None:
        updates["name"] = payload.name.strip()
    if payload.description is not None:
        updates["description"] = payload.description

    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields provided for update")

    res = admin_client.table("specialties").update(updates).eq("id", specialty_id).execute()
    if not res.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Specialty not found")

    row = res.data[0]
    log_audit_event(
        actor_id=admin_id,
        action="UPDATE_SPECIALTY",
        target_type="specialties",
        target_id=specialty_id,
        metadata=updates,
    )

    return SpecialtyRead(id=str(row["id"]), name=row["name"], description=row.get("description"))


def delete_specialty(specialty_id: str, admin_id: str) -> Dict[str, Any]:
    admin_client = get_supabase_admin_client()
    if not admin_client:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database service unavailable")

    res = admin_client.table("specialties").delete().eq("id", specialty_id).execute()
    log_audit_event(
        actor_id=admin_id,
        action="DELETE_SPECIALTY",
        target_type="specialties",
        target_id=specialty_id,
    )

    return {"message": f"Specialty {specialty_id} deleted successfully"}

