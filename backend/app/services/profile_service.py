import logging
from typing import Any, Dict, Optional
from fastapi import HTTPException, status
from app.core.supabase import get_supabase_admin_client, get_supabase_client
from app.models.enums import UserRole
from app.schemas.profile import DoctorProfileRead, ProfileRead, ProfileUpdate, UserMeResponse
from app.services.audit_service import log_audit_event

logger = logging.getLogger(__name__)


def get_user_profile(user_id: str, email: Optional[str] = None) -> UserMeResponse:
    """Fetch complete user profile, including doctor details if applicable."""
    client = get_supabase_admin_client() or get_supabase_client()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service unavailable",
        )

    # 1. Fetch from profiles table
    resp = client.table("profiles").select("*").eq("id", user_id).execute()
    if not resp.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User profile not found",
        )

    profile_data = resp.data[0]
    role = UserRole(profile_data.get("role", "patient"))
    doctor_profile_obj: Optional[DoctorProfileRead] = None

    # 2. If doctor, fetch doctor profile and specialties
    if role == UserRole.DOCTOR:
        doc_resp = (
            client.table("doctor_profiles")
            .select("*, doctor_specialties(specialties(*))")
            .eq("user_id", user_id)
            .execute()
        )
        if doc_resp.data:
            raw_doc = doc_resp.data[0]
            # Flatten specialties if present
            specialties = []
            for ds in raw_doc.get("doctor_specialties", []):
                spec = ds.get("specialties")
                if spec:
                    specialties.append(spec)

            doctor_profile_obj = DoctorProfileRead(
                id=str(raw_doc["id"]),
                user_id=str(raw_doc["user_id"]),
                bio=raw_doc.get("bio"),
                qualifications=raw_doc.get("qualifications") or [],
                years_experience=raw_doc.get("years_experience", 0),
                consultation_fee=float(raw_doc.get("consultation_fee", 0.0)),
                clinic_name=raw_doc.get("clinic_name"),
                city=raw_doc.get("city", "Dhaka"),
                verification_status=raw_doc.get("verification_status", "pending"),
                specialties=specialties,
                created_at=raw_doc.get("created_at"),
                updated_at=raw_doc.get("updated_at"),
            )

    return UserMeResponse(
        id=str(profile_data["id"]),
        email=email,
        role=role,
        full_name=profile_data["full_name"],
        phone=profile_data.get("phone"),
        doctor_profile=doctor_profile_obj,
        created_at=profile_data.get("created_at"),
    )


def update_user_profile(user_id: str, payload: ProfileUpdate, email: Optional[str] = None) -> UserMeResponse:
    """Update profile fields with strict privilege checking.
    
    Users CANNOT modify role or verification_status through this endpoint.
    """
    client = get_supabase_admin_client() or get_supabase_client()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service unavailable",
        )

    current = get_user_profile(user_id, email)

    # 1. Update basic profile table if specified
    profile_updates: Dict[str, Any] = {}
    if payload.full_name is not None:
        profile_updates["full_name"] = payload.full_name
    if payload.phone is not None:
        profile_updates["phone"] = payload.phone

    if profile_updates:
        client.table("profiles").update(profile_updates).eq("id", user_id).execute()
        log_audit_event(
            actor_id=user_id,
            action="UPDATE_PROFILE",
            target_type="profiles",
            target_id=user_id,
            metadata=profile_updates,
        )

    # 2. Update doctor profile if user is doctor and payload supplied
    if current.role == UserRole.DOCTOR and payload.doctor_profile:
        doc_updates: Dict[str, Any] = {}
        dp = payload.doctor_profile
        if dp.bio is not None:
            doc_updates["bio"] = dp.bio
        if dp.qualifications is not None:
            doc_updates["qualifications"] = dp.qualifications
        if dp.years_experience is not None:
            doc_updates["years_experience"] = dp.years_experience
        if dp.consultation_fee is not None:
            doc_updates["consultation_fee"] = dp.consultation_fee
        if dp.clinic_name is not None:
            doc_updates["clinic_name"] = dp.clinic_name
        if dp.city is not None:
            doc_updates["city"] = dp.city

        if doc_updates:
            client.table("doctor_profiles").update(doc_updates).eq("user_id", user_id).execute()
            log_audit_event(
                actor_id=user_id,
                action="UPDATE_DOCTOR_PROFILE",
                target_type="doctor_profiles",
                target_id=user_id,
                metadata=doc_updates,
            )

    return get_user_profile(user_id, email)
