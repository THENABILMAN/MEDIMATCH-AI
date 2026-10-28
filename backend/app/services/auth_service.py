import logging
from typing import Any, Dict
from fastapi import HTTPException, status
from app.core.supabase import get_supabase_admin_client, get_supabase_client
from app.models.enums import UserRole, VerificationStatus
from app.schemas.auth import LoginRequest, RegisterDoctorRequest, RegisterPatientRequest, TokenResponse
from app.services.audit_service import log_audit_event
from app.services.profile_service import get_user_profile

logger = logging.getLogger(__name__)


def register_patient_service(req: RegisterPatientRequest) -> Dict[str, Any]:
    """Register a new patient account."""
    admin_client = get_supabase_admin_client()
    anon_client = get_supabase_client()
    client = admin_client or anon_client

    if not client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable",
        )

    # 1. Create auth user in Supabase
    try:
        if admin_client:
            # Use admin API to create user directly with confirmed email for seamless onboarding
            auth_res = admin_client.auth.admin.create_user({
                "email": req.email,
                "password": req.password,
                "email_confirm": True,
                "user_metadata": {
                    "full_name": req.full_name,
                    "phone": req.phone,
                    "role": UserRole.PATIENT.value,
                },
            })
            user_id = str(auth_res.user.id)
        else:
            auth_res = anon_client.auth.sign_up({
                "email": req.email,
                "password": req.password,
                "options": {
                    "data": {
                        "full_name": req.full_name,
                        "phone": req.phone,
                        "role": UserRole.PATIENT.value,
                    }
                },
            })
            if not auth_res.user:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Sign up failed")
            user_id = str(auth_res.user.id)
    except Exception as e:
        logger.error(f"Sign up error for {req.email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Registration failed: {str(e)}",
        )

    # 2. Ensure profile exists and role is patient (in case trigger hasn't fired or needs sync)
    if admin_client:
        admin_client.table("profiles").upsert({
            "id": user_id,
            "role": UserRole.PATIENT.value,
            "full_name": req.full_name,
            "phone": req.phone,
        }).execute()

    log_audit_event(
        actor_id=user_id,
        action="REGISTER_PATIENT",
        target_type="profiles",
        target_id=user_id,
        metadata={"email": req.email},
    )

    return {
        "message": "Patient registered successfully",
        "user_id": user_id,
        "role": UserRole.PATIENT.value,
    }


def register_doctor_service(req: RegisterDoctorRequest) -> Dict[str, Any]:
    """Register a new doctor account with default 'pending' verification status."""
    admin_client = get_supabase_admin_client()
    anon_client = get_supabase_client()
    client = admin_client or anon_client

    if not client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable",
        )

    # 1. Create auth user
    try:
        if admin_client:
            auth_res = admin_client.auth.admin.create_user({
                "email": req.email,
                "password": req.password,
                "email_confirm": True,
                "user_metadata": {
                    "full_name": req.full_name,
                    "phone": req.phone,
                    "role": UserRole.DOCTOR.value,
                },
            })
            user_id = str(auth_res.user.id)
        else:
            auth_res = anon_client.auth.sign_up({
                "email": req.email,
                "password": req.password,
                "options": {
                    "data": {
                        "full_name": req.full_name,
                        "phone": req.phone,
                        "role": UserRole.DOCTOR.value,
                    }
                },
            })
            if not auth_res.user:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Sign up failed")
            user_id = str(auth_res.user.id)
    except Exception as e:
        logger.error(f"Sign up doctor error for {req.email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Doctor registration failed: {str(e)}",
        )

    # 2. Upsert profile as doctor
    if admin_client:
        admin_client.table("profiles").upsert({
            "id": user_id,
            "role": UserRole.DOCTOR.value,
            "full_name": req.full_name,
            "phone": req.phone,
        }).execute()

        # 3. Create doctor_profiles row with verification_status = 'pending'
        doc_profile = {
            "user_id": user_id,
            "bio": req.bio,
            "qualifications": req.qualifications,
            "years_experience": req.years_experience,
            "consultation_fee": req.consultation_fee,
            "clinic_name": req.clinic_name,
            "city": req.city,
            "verification_status": VerificationStatus.PENDING.value,
        }
        res_doc = admin_client.table("doctor_profiles").insert(doc_profile).execute()
        doctor_id = str(res_doc.data[0]["id"]) if res_doc.data else None

        # 4. Link specialties if provided
        if doctor_id and req.specialty_ids:
            spec_entries = [{"doctor_id": doctor_id, "specialty_id": s_id} for s_id in req.specialty_ids]
            admin_client.table("doctor_specialties").insert(spec_entries).execute()

    log_audit_event(
        actor_id=user_id,
        action="REGISTER_DOCTOR",
        target_type="doctor_profiles",
        target_id=user_id,
        metadata={"email": req.email, "city": req.city},
    )

    return {
        "message": "Doctor registered successfully. Account pending administrative approval.",
        "user_id": user_id,
        "role": UserRole.DOCTOR.value,
        "verification_status": VerificationStatus.PENDING.value,
    }


def login_service(req: LoginRequest) -> TokenResponse:
    """Authenticate via Supabase Auth and return access token with role."""
    client = get_supabase_client()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable",
        )

    try:
        auth_res = client.auth.sign_in_with_password({
            "email": req.email,
            "password": req.password,
        })
    except Exception as e:
        logger.warning(f"Login failed for {req.email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not auth_res or not auth_res.session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed: No active session",
        )

    user_id = str(auth_res.user.id)
    token = auth_res.session.access_token

    # Retrieve profile to return current role and name
    profile = get_user_profile(user_id, email=req.email)

    log_audit_event(
        actor_id=user_id,
        action="LOGIN_SUCCESS",
        target_type="auth.users",
        target_id=user_id,
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user_id=user_id,
        role=profile.role,
        full_name=profile.full_name,
    )
