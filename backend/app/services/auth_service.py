import logging
from typing import Any

from fastapi import HTTPException, status

from app.core.supabase import create_auth_client, get_supabase_admin_client
from app.models.enums import UserRole, VerificationStatus
from app.schemas.auth import (
    LoginRequest,
    RegisterDoctorRequest,
    RegisterPatientRequest,
    TokenResponse,
)
from app.services.audit_service import log_audit_event
from app.services.profile_service import get_user_profile

logger = logging.getLogger(__name__)

# The same answer whatever went wrong, so this cannot be used to test which emails have accounts
REGISTRATION_FAILED = "We could not create this account. If you already have one, please sign in."


def _require_admin_client() -> Any:
    client = get_supabase_admin_client()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable",
        )
    return client


def _create_account(
    client: Any, req: RegisterPatientRequest | RegisterDoctorRequest, role: UserRole
) -> str:
    """Creates the sign-in identity and profile together, or leaves neither behind."""
    try:
        auth_res = client.auth.admin.create_user(
            {
                "email": req.email,
                "password": req.password,
                "email_confirm": True,
                "user_metadata": {
                    "full_name": req.full_name,
                    "phone": req.phone,
                    "role": role.value,
                },
            }
        )
        user_id = str(auth_res.user.id)
    except Exception as e:
        logger.warning(f"Sign up failed: {type(e).__name__}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=REGISTRATION_FAILED,
        ) from e

    try:
        client.table("profiles").upsert(
            {"id": user_id, "role": role.value, "full_name": req.full_name, "phone": req.phone}
        ).execute()
    except Exception:
        _remove_account(client, user_id)
        raise
    return user_id


def _remove_account(client: Any, user_id: str) -> None:
    try:
        client.auth.admin.delete_user(user_id)
    except Exception as e:
        logger.error(f"Could not remove incomplete account {user_id}: {type(e).__name__}")


def register_patient_service(req: RegisterPatientRequest) -> dict[str, Any]:
    """Register a new patient account."""
    client = _require_admin_client()
    user_id = _create_account(client, req, UserRole.PATIENT)

    log_audit_event(
        actor_id=user_id,
        action="REGISTER_PATIENT",
        target_type="profiles",
        target_id=user_id,
    )

    return {
        "message": "Patient registered successfully",
        "user_id": user_id,
        "role": UserRole.PATIENT.value,
    }


def register_doctor_service(req: RegisterDoctorRequest) -> dict[str, Any]:
    """Register a new doctor account with default 'pending' verification status."""
    client = _require_admin_client()
    user_id = _create_account(client, req, UserRole.DOCTOR)

    try:
        res_doc = (
            client.table("doctor_profiles")
            .insert(
                {
                    "user_id": user_id,
                    "bio": req.bio,
                    "qualifications": req.qualifications,
                    "years_experience": req.years_experience,
                    "consultation_fee": req.consultation_fee,
                    "clinic_name": req.clinic_name,
                    "city": req.city,
                    "verification_status": VerificationStatus.PENDING.value,
                }
            )
            .execute()
        )
        if req.specialty_ids:
            doctor_id = str(res_doc.data[0]["id"])
            client.table("doctor_specialties").insert(
                [{"doctor_id": doctor_id, "specialty_id": s_id} for s_id in req.specialty_ids]
            ).execute()
    except Exception as e:
        logger.warning(f"Doctor profile setup failed: {type(e).__name__}")
        _remove_account(client, user_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=REGISTRATION_FAILED,
        ) from e

    log_audit_event(
        actor_id=user_id,
        action="REGISTER_DOCTOR",
        target_type="doctor_profiles",
        target_id=user_id,
        metadata={"city": req.city},
    )

    return {
        "message": "Doctor registered successfully. Account pending administrative approval.",
        "user_id": user_id,
        "role": UserRole.DOCTOR.value,
        "verification_status": VerificationStatus.PENDING.value,
    }


def login_service(req: LoginRequest) -> TokenResponse:
    """Authenticate via Supabase Auth and return access token with role."""
    client = create_auth_client()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable",
        )

    try:
        auth_res = client.auth.sign_in_with_password(
            {
                "email": req.email,
                "password": req.password,
            }
        )
    except Exception as e:
        logger.info(f"Login failed: {type(e).__name__}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e

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
