import logging
import uuid
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from app.api.deps import get_current_user, require_doctor
from app.core.supabase import get_supabase_admin_client
from app.models.enums import UserRole
from app.schemas.common import MAX_CONSULTATION_FEE, MAX_YEARS_EXPERIENCE, UuidStr
from app.schemas.appointment import SlotCreate, SlotResponse
from app.schemas.doctor import (
    DoctorCredentialRead,
    DoctorProfileCreateOrUpdate,
    DoctorSearchResult,
    PublicDoctorRead,
)
from app.schemas.profile import DoctorProfileRead, SpecialtyRead, UserMeResponse
from app.services.admin_service import list_specialties
from app.services.appointment_service import (
    create_availability_slot,
    delete_availability_slot,
    list_doctor_slots,
    list_public_doctor_slots,
)
from app.services.doctor_service import (
    add_doctor_credential,
    get_credential_url,
    get_doctor_profile_by_user_id,
    get_public_doctor_by_id,
    get_verification_history,
    list_my_credentials,
    search_public_doctors,
    upsert_doctor_profile,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/doctors", tags=["Doctors"])


# ------------------------------------------------------------------------------
# Doctor Self-Management (Role: Doctor)
# ------------------------------------------------------------------------------

@router.get("/me/profile", response_model=DoctorProfileRead, summary="Get own doctor profile")
def get_my_doctor_profile(
    current_user: UserMeResponse = Depends(require_doctor),
) -> DoctorProfileRead:
    return get_doctor_profile_by_user_id(current_user.id)


@router.post("/me/profile", response_model=DoctorProfileRead, summary="Create or update own doctor profile")
def create_my_doctor_profile(
    payload: DoctorProfileCreateOrUpdate,
    current_user: UserMeResponse = Depends(require_doctor),
) -> DoctorProfileRead:
    return upsert_doctor_profile(current_user.id, payload)


@router.put("/me/profile", response_model=DoctorProfileRead, summary="Update own doctor profile")
def update_my_doctor_profile(
    payload: DoctorProfileCreateOrUpdate,
    current_user: UserMeResponse = Depends(require_doctor),
) -> DoctorProfileRead:
    return upsert_doctor_profile(current_user.id, payload)


@router.post("/me/credentials", response_model=DoctorCredentialRead, summary="Upload verification credential document")
async def upload_credential(
    document_type: str = Form(..., description="e.g. bmdc_license, mbbs_degree, certificate"),
    file: Optional[UploadFile] = File(default=None),
    file_path: Optional[str] = Form(default=None),
    current_user: UserMeResponse = Depends(require_doctor),
) -> DoctorCredentialRead:
    """Upload a credential document to private Supabase Storage and register credential record."""
    if file_path and not file_path.startswith(f"{current_user.id}/"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Credential paths must be inside your own folder",
        )

    target_path = file_path

    # If an actual file was uploaded, stream it into Supabase Storage
    if file:
        admin_client = get_supabase_admin_client()
        if not admin_client:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Credential storage is unavailable",
            )

        file_bytes = await file.read()
        safe_name = Path(file.filename or "document").name
        target_path = f"{current_user.id}/{uuid.uuid4()}_{safe_name}"
        try:
            admin_client.storage.from_("doctor-credentials").upload(
                path=target_path,
                file=file_bytes,
                file_options={"content-type": file.content_type or "application/octet-stream"},
            )
        except Exception as e:
            # A record must never point at a document an admin cannot open
            logger.error(f"Credential upload failed for {current_user.id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Your document could not be uploaded. Please try again.",
            )

    if not target_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either a file upload or file_path must be provided",
        )

    return add_doctor_credential(
        user_id=current_user.id,
        file_path=target_path,
        document_type=document_type,
    )


@router.get("/me/credentials", response_model=List[DoctorCredentialRead], summary="List own credential documents")
def get_my_credentials(
    current_user: UserMeResponse = Depends(require_doctor),
) -> List[DoctorCredentialRead]:
    return list_my_credentials(current_user.id)


@router.get("/me/verification-history", summary="List own verification status events")
def get_my_verification_history(
    current_user: UserMeResponse = Depends(require_doctor),
) -> List[Dict[str, Any]]:
    return get_verification_history(current_user.id)


@router.get("/credentials/{id}/url", summary="Get a short-lived link to a credential document")
def get_credential_link(
    id: UuidStr,
    current_user: UserMeResponse = Depends(get_current_user),
) -> Dict[str, str]:
    return get_credential_url(id, current_user.id, current_user.role == UserRole.ADMIN)


@router.post("/me/slots", response_model=SlotResponse, status_code=status.HTTP_201_CREATED, summary="Create an availability slot")
def create_slot(
    payload: SlotCreate,
    current_user: UserMeResponse = Depends(require_doctor),
) -> SlotResponse:
    """Create an availability slot for the authenticated doctor."""
    return create_availability_slot(
        doctor_user_id=current_user.id,
        start_time=payload.start_time,
        end_time=payload.end_time,
    )


@router.get("/me/slots", response_model=List[SlotResponse], summary="List doctor's availability slots")
def get_my_slots(
    include_booked: bool = Query(default=True, description="Whether to include booked slots"),
    current_user: UserMeResponse = Depends(require_doctor),
) -> List[SlotResponse]:
    """Retrieve all availability slots for the authenticated doctor."""
    return list_doctor_slots(
        doctor_user_id=current_user.id,
        include_booked=include_booked,
    )


@router.delete("/me/slots/{slot_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete an availability slot")
def delete_my_slot(
    slot_id: UuidStr,
    current_user: UserMeResponse = Depends(require_doctor),
) -> None:
    """Delete an unbooked availability slot belonging to the authenticated doctor."""
    delete_availability_slot(
        doctor_user_id=current_user.id,
        slot_id=slot_id,
    )


# ------------------------------------------------------------------------------
# Public Patient-Facing Directory & Search (Anonymous-Safe)
# ------------------------------------------------------------------------------

@router.get("/specialties", response_model=List[SpecialtyRead], summary="List all medical specialties")
def get_public_specialties() -> List[SpecialtyRead]:
    """Public listing of all available medical specialties."""
    return list_specialties()


@router.get("/search", response_model=DoctorSearchResult, summary="Search verified approved doctors")
def search_doctors(
    specialty: Optional[str] = Query(default=None, max_length=100, description="Specialty name or ID filter"),
    city: Optional[str] = Query(default=None, max_length=100, description="City location filter"),
    max_fee: Optional[float] = Query(default=None, ge=0, le=MAX_CONSULTATION_FEE, description="Maximum consultation fee (BDT)"),
    min_experience: Optional[int] = Query(default=None, ge=0, le=MAX_YEARS_EXPERIENCE, description="Minimum years of clinical experience"),
    sort_by: Optional[Literal["fee_asc", "fee_desc", "experience_desc"]] = Query(default=None, description="Sort order"),
    page: int = Query(default=1, ge=1, le=10000, description="Page number"),
    page_size: int = Query(default=10, ge=1, le=50, description="Items per page"),
) -> DoctorSearchResult:
    """Public search endpoint.
    
    Guaranteed: Returns ONLY doctors with verification_status = 'approved'.
    Does not leak credential files, personal phone numbers, or unapproved profiles.
    """
    return search_public_doctors(
        specialty=specialty,
        city=city,
        max_fee=max_fee,
        min_experience=min_experience,
        sort_by=sort_by,
        page=page,
        page_size=page_size,
    )


@router.get("/{id}", response_model=PublicDoctorRead, summary="Get public profile of an approved doctor")
def get_doctor_by_id(
    id: UuidStr,
) -> PublicDoctorRead:
    """Fetch public profile of an approved doctor. Returns 404 if not found or unapproved."""
    return get_public_doctor_by_id(doctor_id=id)


@router.get("/{id}/slots", response_model=List[SlotResponse], summary="Get public upcoming available slots of an approved doctor")
def get_doctor_slots(
    id: UuidStr,
) -> List[SlotResponse]:
    """Fetch upcoming unbooked slots for an approved doctor."""
    return list_public_doctor_slots(doctor_id=id)


