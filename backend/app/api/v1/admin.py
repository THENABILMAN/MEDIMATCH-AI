from datetime import datetime
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query, status
from app.api.deps import require_admin
from app.schemas.common import UuidStr
from app.models.enums import VerificationStatus
from app.schemas.doctor import (
    AdminDoctorActionRequest,
    AuditLogPaginatedResponse,
    SpecialtyCreate,
    SpecialtyUpdate,
)
from app.schemas.profile import SpecialtyRead, UserMeResponse
from app.services.admin_service import (
    approve_doctor,
    create_specialty,
    delete_specialty,
    get_audit_logs,
    list_doctors_for_admin,
    list_patients_for_admin,
    list_specialties,
    reject_doctor,
    suspend_doctor,
    update_specialty,
)

router = APIRouter(prefix="/admin", tags=["Admin"])


# ------------------------------------------------------------------------------
# Doctor Verification Management
# ------------------------------------------------------------------------------

@router.get("/patients", summary="List patient accounts")
def read_patients(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    sort: str = Query(default="created_at"),
    descending: bool = Query(default=True),
    search: Optional[str] = Query(default=None, max_length=100),
    current_admin: UserMeResponse = Depends(require_admin),
) -> Dict[str, Any]:
    return list_patients_for_admin(
        limit=limit, offset=offset, sort=sort, descending=descending, search=search
    )


@router.get("/doctors", summary="List doctor profiles for admin review")
def read_doctors(
    status: Optional[VerificationStatus] = Query(default=None, description="Filter by status"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    sort: str = Query(default="created_at"),
    descending: bool = Query(default=True),
    current_admin: UserMeResponse = Depends(require_admin),
) -> Dict[str, Any]:
    return list_doctors_for_admin(
        status_filter=status, limit=limit, offset=offset, sort=sort, descending=descending
    )


@router.post("/doctors/{id}/approve", summary="Approve doctor profile")
def approve_doctor_profile(
    id: UuidStr,
    current_admin: UserMeResponse = Depends(require_admin),
) -> Dict[str, Any]:
    return approve_doctor(doctor_id=id, admin_id=current_admin.id)


@router.post("/doctors/{id}/reject", summary="Reject doctor profile")
def reject_doctor_profile(
    id: UuidStr,
    payload: AdminDoctorActionRequest,
    current_admin: UserMeResponse = Depends(require_admin),
) -> Dict[str, Any]:
    return reject_doctor(
        doctor_id=id,
        admin_id=current_admin.id,
        reason=payload.reason or "Does not meet verification guidelines",
    )


@router.post("/doctors/{id}/suspend", summary="Suspend doctor profile")
def suspend_doctor_profile(
    id: UuidStr,
    payload: AdminDoctorActionRequest,
    current_admin: UserMeResponse = Depends(require_admin),
) -> Dict[str, Any]:
    return suspend_doctor(
        doctor_id=id,
        admin_id=current_admin.id,
        reason=payload.reason or "Suspended by administrator",
    )


# ------------------------------------------------------------------------------
# Platform Audit Logs
# ------------------------------------------------------------------------------

@router.get("/audit-logs", response_model=AuditLogPaginatedResponse, summary="Get paginated platform audit logs")
def read_audit_logs(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    action: Optional[str] = Query(default=None, max_length=100, description="Filter by action name"),
    date_from: Optional[datetime] = Query(default=None, description="Earliest event time"),
    date_to: Optional[datetime] = Query(default=None, description="Latest event time"),
    current_admin: UserMeResponse = Depends(require_admin),
) -> AuditLogPaginatedResponse:
    return get_audit_logs(
        limit=limit, offset=offset, action=action, date_from=date_from, date_to=date_to
    )


# ------------------------------------------------------------------------------
# Specialty Management
# ------------------------------------------------------------------------------

@router.post("/specialties", response_model=SpecialtyRead, status_code=status.HTTP_201_CREATED, summary="Create a medical specialty")
def admin_create_specialty(
    payload: SpecialtyCreate,
    current_admin: UserMeResponse = Depends(require_admin),
) -> SpecialtyRead:
    return create_specialty(payload=payload, admin_id=current_admin.id)


@router.get("/specialties", response_model=List[SpecialtyRead], summary="List all medical specialties")
def admin_list_specialties(
    current_admin: UserMeResponse = Depends(require_admin),
) -> List[SpecialtyRead]:
    return list_specialties()


@router.put("/specialties/{id}", response_model=SpecialtyRead, summary="Update specialty")
def admin_update_specialty(
    id: UuidStr,
    payload: SpecialtyUpdate,
    current_admin: UserMeResponse = Depends(require_admin),
) -> SpecialtyRead:
    return update_specialty(specialty_id=id, payload=payload, admin_id=current_admin.id)


@router.delete("/specialties/{id}", summary="Delete specialty")
def admin_delete_specialty(
    id: UuidStr,
    current_admin: UserMeResponse = Depends(require_admin),
) -> Dict[str, Any]:
    return delete_specialty(specialty_id=id, admin_id=current_admin.id)

