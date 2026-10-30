from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.api.deps import get_current_user, require_doctor
from app.models.enums import AppointmentStatus, UserRole
from app.schemas.appointment import (
    AppointmentCancelRequest,
    AppointmentCreate,
    AppointmentResponse,
)
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
    current_user: UserMeResponse = Depends(get_current_user),
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
    current_user: UserMeResponse = Depends(get_current_user),
) -> List[AppointmentResponse]:
    """Retrieve appointments for the authenticated user (patient or doctor view)."""
    return get_user_appointments(
        user_id=current_user.id,
        role=current_user.role,
        status_filter=status,
    )


@router.post(
    "/{id}/cancel",
    response_model=AppointmentResponse,
    summary="Cancel an appointment",
)
def cancel_my_appointment(
    id: str,
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
    id: str,
    current_user: UserMeResponse = Depends(require_doctor),
) -> AppointmentResponse:
    """Marks an appointment as completed. Allowed only for the assigned doctor."""
    return complete_appointment(
        doctor_user_id=current_user.id,
        appointment_id=id,
    )

