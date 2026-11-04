from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from postgrest import SyncPostgrestClient
from app.api.deps import get_current_user, get_user_db, require_doctor, require_patient
from app.models.enums import AppointmentStatus, UserRole
from app.schemas.appointment import (
    AppointmentCancelRequest,
    AppointmentCreate,
    AppointmentResponse,
)
from app.schemas.common import UuidStr
from app.schemas.profile import UserMeResponse
from app.services.appointment_service import (
    book_slot_atomic,
    cancel_appointment,
    complete_appointment,
    get_user_appointments,
)

router = APIRouter(prefix="/appointments", tags=["Appointments"])


@router.post(
    "",
    response_model=AppointmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Book an appointment slot atomically",
)
def book_appointment(
    payload: AppointmentCreate,
    current_user: UserMeResponse = Depends(require_patient),
) -> AppointmentResponse:
    """Atomically books an upcoming unbooked slot for the current patient.
    
    Protected against race conditions via database-level row locking
    and partial unique index.
    """
    return book_slot_atomic(
        patient_user_id=current_user.id,
        slot_id=payload.slot_id,
    )


@router.get(
    "/me",
    response_model=List[AppointmentResponse],
    summary="List current user's appointments",
)
def get_my_appointments(
    status: Optional[AppointmentStatus] = Query(default=None, description="Optional appointment status filter"),
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: UserMeResponse = Depends(get_current_user),
    db: SyncPostgrestClient = Depends(get_user_db),
) -> List[AppointmentResponse]:
    """Retrieve appointments for the authenticated user (patient or doctor view)."""
    return get_user_appointments(
        user_id=current_user.id,
        role=current_user.role,
        status_filter=status,
        db=db,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/{id}/cancel",
    response_model=AppointmentResponse,
    summary="Cancel an appointment",
)
def cancel_my_appointment(
    id: UuidStr,
    payload: Optional[AppointmentCancelRequest] = None,
    current_user: UserMeResponse = Depends(get_current_user),
) -> AppointmentResponse:
    """Cancels an appointment, frees the associated slot, and logs an audit log entry.
    
    Allowed only for the involved patient or doctor (or system admin).
    """
    reason = payload.reason if payload else None
    return cancel_appointment(
        user_id=current_user.id,
        role=current_user.role,
        appointment_id=id,
        reason=reason,
    )


@router.post(
    "/{id}/complete",
    response_model=AppointmentResponse,
    summary="Mark an appointment as completed",
)
def complete_my_appointment(
    id: UuidStr,
    current_user: UserMeResponse = Depends(require_doctor),
) -> AppointmentResponse:
    """Marks an appointment as completed. Allowed only for the assigned doctor."""
    return complete_appointment(
        doctor_user_id=current_user.id,
        appointment_id=id,
    )

