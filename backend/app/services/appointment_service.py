import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID
from fastapi import HTTPException, status
from app.core.supabase import get_supabase_admin_client, get_supabase_client
from app.models.enums import AppointmentStatus, UserRole, VerificationStatus
from app.schemas.appointment import (
    AppointmentDoctorInfo,
    AppointmentPatientInfo,
    AppointmentResponse,
    SlotResponse,
)
from app.services.audit_service import log_audit_event
from app.services.doctor_service import get_doctor_profile_by_user_id

logger = logging.getLogger(__name__)


def _get_client():
    client = get_supabase_admin_client() or get_supabase_client()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service unavailable",
        )
    return client


def create_availability_slot(
    doctor_user_id: str,
    start_time: datetime,
    end_time: datetime,
) -> SlotResponse:
    """Creates a new availability slot for an approved doctor."""
    doctor = get_doctor_profile_by_user_id(doctor_user_id)
    if doctor.verification_status != VerificationStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only approved doctors can manage availability slots",
        )

    client = _get_client()

    # Normalize to ISO UTC
    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=timezone.utc)
    if end_time.tzinfo is None:
        end_time = end_time.replace(tzinfo=timezone.utc)

    # Check for slot overlaps in python first for user-friendly error
    overlap_res = (
        client.table("availability_slots")
        .select("id")
        .eq("doctor_id", doctor.id)
        .lt("start_time", end_time.isoformat())
        .gt("end_time", start_time.isoformat())
        .execute()
    )
    if overlap_res.data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This slot overlaps with an existing availability slot for your profile",
        )

    insert_data = {
        "doctor_id": doctor.id,
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "is_booked": False,
    }

    try:
        res = client.table("availability_slots").insert(insert_data).execute()
        if not res.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create availability slot",
            )
        row = res.data[0]
        return SlotResponse(
            id=str(row["id"]),
            doctor_id=str(row["doctor_id"]),
            start_time=row["start_time"],
            end_time=row["end_time"],
            is_booked=bool(row["is_booked"]),
            created_at=row.get("created_at"),
        )
    except Exception as e:
        err_msg = str(e)
        if "no_overlapping_slots" in err_msg or "conflicting key" in err_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This slot overlaps with an existing availability slot",
            )
        logger.error(f"Error creating slot: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Slot creation failed: {e}",
        )


def list_doctor_slots(
    doctor_user_id: str,
    include_booked: bool = True,
) -> List[SlotResponse]:
    """Retrieves all slots for the authenticated doctor."""
    doctor = get_doctor_profile_by_user_id(doctor_user_id)
    client = _get_client()

    query = (
        client.table("availability_slots")
        .select("*")
        .eq("doctor_id", doctor.id)
        .order("start_time", desc=False)
    )

    if not include_booked:
        now_utc = datetime.now(timezone.utc).isoformat()
        query = query.eq("is_booked", False).gt("start_time", now_utc)

    res = query.execute()
    slots = []
    for row in res.data or []:
        slots.append(
            SlotResponse(
                id=str(row["id"]),
                doctor_id=str(row["doctor_id"]),
                start_time=row["start_time"],
                end_time=row["end_time"],
                is_booked=bool(row["is_booked"]),
                created_at=row.get("created_at"),
            )
        )
    return slots


def list_public_doctor_slots(doctor_id: str) -> List[SlotResponse]:
    """Retrieves upcoming available (unbooked) slots for an approved doctor."""
    client = _get_client()

    # Check doctor approval
    doc_res = (
        client.table("doctor_profiles")
        .select("id, verification_status")
        .eq("id", doctor_id)
        .execute()
    )
    if not doc_res.data or doc_res.data[0]["verification_status"] != VerificationStatus.APPROVED.value:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found or not approved",
        )

    now_utc = datetime.now(timezone.utc).isoformat()
    res = (
        client.table("availability_slots")
        .select("*")
        .eq("doctor_id", doctor_id)
        .eq("is_booked", False)
        .gt("start_time", now_utc)
        .order("start_time", desc=False)
        .execute()
    )

    slots = []
    for row in res.data or []:
        slots.append(
            SlotResponse(
                id=str(row["id"]),
                doctor_id=str(row["doctor_id"]),
                start_time=row["start_time"],
                end_time=row["end_time"],
                is_booked=bool(row["is_booked"]),
                created_at=row.get("created_at"),
            )
        )
    return slots


def delete_availability_slot(doctor_user_id: str, slot_id: str) -> None:
    """Deletes an unbooked availability slot belonging to the doctor."""
    doctor = get_doctor_profile_by_user_id(doctor_user_id)
    client = _get_client()

    slot_res = (
        client.table("availability_slots")
        .select("*")
        .eq("id", slot_id)
        .execute()
    )
    if not slot_res.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Availability slot not found",
        )

    slot = slot_res.data[0]
    if str(slot["doctor_id"]) != str(doctor.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to delete this availability slot",
        )

    if slot.get("is_booked"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete an availability slot that is currently booked. Cancel the appointment first.",
        )

    client.table("availability_slots").delete().eq("id", slot_id).execute()


def book_slot_atomic(patient_user_id: str, slot_id: str) -> AppointmentResponse:
    """Atomically books an appointment slot for a patient using the database RPC."""
    client = _get_client()

    # Call atomic stored procedure
    rpc_res = client.rpc(
        "book_appointment_atomic",
        {"p_slot_id": str(slot_id), "p_patient_id": str(patient_user_id)},
    ).execute()

    result = rpc_res.data
    if not result:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database booking procedure returned empty response",
        )

    if not result.get("success"):
        code = result.get("code", 400)
        error_msg = result.get("error", "Booking failed")
        if code == 409:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error_msg)
        elif code == 404:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error_msg)
        elif code == 400:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg)
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error_msg)

    appointment_id = result["appointment_id"]

    # Audit log booking
    log_audit_event(
        actor_id=patient_user_id,
        action="APPOINTMENT_BOOKED",
        target_type="appointment",
        target_id=str(appointment_id),
        metadata={
            "slot_id": str(slot_id),
            "doctor_id": str(result.get("doctor_id")),
        },
    )

    # Return full hydrated appointment
    return get_appointment_by_id(appointment_id)


def _hydrate_appointments(raw_appointments: List[Dict[str, Any]]) -> List[AppointmentResponse]:
    """Helper to join doctor details, patient details, and slot times to appointments."""
    if not raw_appointments:
        return []

    client = _get_client()

    doc_ids = list({str(a["doctor_id"]) for a in raw_appointments if a.get("doctor_id")})
    patient_ids = list({str(a["patient_id"]) for a in raw_appointments if a.get("patient_id")})
    slot_ids = list({str(a["slot_id"]) for a in raw_appointments if a.get("slot_id")})

    # Bulk fetch doctors with profiles and specialties
    doctors_map: Dict[str, AppointmentDoctorInfo] = {}
    if doc_ids:
        docs_res = (
            client.table("doctor_profiles")
            .select("id, consultation_fee, clinic_name, city, profiles!inner(full_name), doctor_specialties(specialties(name))")
            .in_("id", doc_ids)
            .execute()
        )
        for d in docs_res.data or []:
            d_id = str(d["id"])
            p_info = d.get("profiles") or {}
            specs = [
                ds["specialties"]["name"]
                for ds in d.get("doctor_specialties", [])
                if ds.get("specialties") and ds["specialties"].get("name")
            ]
            doctors_map[d_id] = AppointmentDoctorInfo(
                id=d_id,
                full_name=p_info.get("full_name", "Doctor"),
                clinic_name=d.get("clinic_name"),
                city=d.get("city", "Dhaka"),
                consultation_fee=float(d.get("consultation_fee", 0.0)),
                specialties=specs,
            )

    # Bulk fetch patients
    patients_map: Dict[str, AppointmentPatientInfo] = {}
    if patient_ids:
        patients_res = (
            client.table("profiles")
            .select("id, full_name, phone")
            .in_("id", patient_ids)
            .execute()
        )
        for p in patients_res.data or []:
            p_id = str(p["id"])
            patients_map[p_id] = AppointmentPatientInfo(
                id=p_id,
                full_name=p.get("full_name", "Patient"),
                phone=p.get("phone"),
                email=None,
            )

    # Bulk fetch slot times
    slots_map: Dict[str, Dict[str, Any]] = {}
    if slot_ids:
        slots_res = (
            client.table("availability_slots")
            .select("id, start_time, end_time")
            .in_("id", slot_ids)
            .execute()
        )
        for s in slots_res.data or []:
            slots_map[str(s["id"])] = s

    results: List[AppointmentResponse] = []
    for row in raw_appointments:
        a_id = str(row["id"])
        d_id = str(row["doctor_id"])
        p_id = str(row["patient_id"])
        s_id = str(row["slot_id"]) if row.get("slot_id") else None

        slot_info = slots_map.get(s_id) if s_id else None

        results.append(
            AppointmentResponse(
                id=a_id,
                patient_id=p_id,
                doctor_id=d_id,
                slot_id=s_id,
                status=AppointmentStatus(row["status"]),
                created_at=row["created_at"],
                updated_at=row.get("updated_at"),
                start_time=slot_info["start_time"] if slot_info else None,
                end_time=slot_info["end_time"] if slot_info else None,
                doctor=doctors_map.get(d_id),
                patient=patients_map.get(p_id),
            )
        )

    return results


def get_appointment_by_id(appointment_id: str) -> AppointmentResponse:
    """Fetch single appointment with hydrated doctor, patient, and slot details."""
    client = _get_client()
    res = (
        client.table("appointments")
        .select("*")
        .eq("id", appointment_id)
        .execute()
    )
    if not res.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found",
        )
    hydrated = _hydrate_appointments(res.data)
    return hydrated[0]


def get_user_appointments(
    user_id: str,
    role: UserRole,
    status_filter: Optional[AppointmentStatus] = None,
) -> List[AppointmentResponse]:
    """Retrieves appointments for the current user based on their role."""
    client = _get_client()
    query = client.table("appointments").select("*").order("created_at", desc=True)

    if role == UserRole.PATIENT:
        query = query.eq("patient_id", user_id)
    elif role == UserRole.DOCTOR:
        doctor = get_doctor_profile_by_user_id(user_id)
        query = query.eq("doctor_id", doctor.id)
    elif role == UserRole.ADMIN:
        pass  # Admins can view all appointments
    else:
        return []

    if status_filter:
        query = query.eq("status", status_filter.value)

    res = query.execute()
    return _hydrate_appointments(res.data or [])


def cancel_appointment(
    user_id: str,
    role: UserRole,
    appointment_id: str,
    reason: Optional[str] = None,
) -> AppointmentResponse:
    """Cancels an appointment, frees the associated slot, and logs an audit event."""
    client = _get_client()

    res = (
        client.table("appointments")
        .select("*")
        .eq("id", appointment_id)
        .execute()
    )
    if not res.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found",
        )

    app = res.data[0]
    app_status = app.get("status")

    if app_status == AppointmentStatus.CANCELLED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Appointment is already cancelled",
        )
    if app_status == AppointmentStatus.COMPLETED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot cancel an appointment that is already completed",
        )

    # Enforce authorization: only involved patient, doctor, or admin
    if role == UserRole.PATIENT:
        if str(app["patient_id"]) != str(user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to cancel this appointment",
            )
    elif role == UserRole.DOCTOR:
        doctor = get_doctor_profile_by_user_id(user_id)
        if str(app["doctor_id"]) != str(doctor.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to cancel this appointment",
            )
    elif role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden",
        )

    # 1. Update appointment status to cancelled
    now_utc = datetime.now(timezone.utc).isoformat()
    client.table("appointments").update({
        "status": AppointmentStatus.CANCELLED.value,
        "updated_at": now_utc,
    }).eq("id", appointment_id).execute()

    # 2. Free up the availability slot
    slot_id = app.get("slot_id")
    if slot_id:
        client.table("availability_slots").update({
            "is_booked": False,
        }).eq("id", slot_id).execute()

    # 3. Log immutable audit log
    log_audit_event(
        actor_id=user_id,
        action="APPOINTMENT_CANCELLED",
        target_type="appointment",
        target_id=str(appointment_id),
        metadata={
            "reason": reason,
            "cancelled_by_role": role.value,
            "slot_id": str(slot_id) if slot_id else None,
            "doctor_id": str(app.get("doctor_id")),
            "patient_id": str(app.get("patient_id")),
        },
    )

    return get_appointment_by_id(appointment_id)


def complete_appointment(doctor_user_id: str, appointment_id: str) -> AppointmentResponse:
    """Marks an appointment as completed (doctor only)."""
    doctor = get_doctor_profile_by_user_id(doctor_user_id)
    client = _get_client()

    res = (
        client.table("appointments")
        .select("*")
        .eq("id", appointment_id)
        .execute()
    )
    if not res.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found",
        )

    app = res.data[0]
    if str(app["doctor_id"]) != str(doctor.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the assigned doctor can mark this appointment as completed",
        )

    if app.get("status") == AppointmentStatus.CANCELLED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot complete a cancelled appointment",
        )

    now_utc = datetime.now(timezone.utc).isoformat()
    client.table("appointments").update({
        "status": AppointmentStatus.COMPLETED.value,
        "updated_at": now_utc,
    }).eq("id", appointment_id).execute()

    log_audit_event(
        actor_id=doctor_user_id,
        action="APPOINTMENT_COMPLETED",
        target_type="appointment",
        target_id=str(appointment_id),
        metadata={
            "doctor_id": str(doctor.id),
            "patient_id": str(app.get("patient_id")),
        },
    )

    return get_appointment_by_id(appointment_id)

