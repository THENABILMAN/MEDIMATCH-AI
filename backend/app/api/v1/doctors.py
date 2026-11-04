import logging
import uuid
from typing import Any, Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from postgrest import SyncPostgrestClient

from app.api.deps import get_current_user, get_user_db, require_doctor
from app.core.config import settings
from app.core.rate_limit import limit_by_user
from app.core.supabase import get_supabase_admin_client
from app.models.enums import UserRole
from app.schemas.appointment import SlotCreate, SlotResponse
from app.schemas.common import MAX_CONSULTATION_FEE, MAX_YEARS_EXPERIENCE, UuidStr
from app.schemas.doctor import (
    DoctorCredentialRead,
    DoctorProfileCreateOrUpdate,
    DoctorSearchResult,
    PublicDoctorRead,
)
from app.schemas.profile import DoctorProfileRead, SpecialtyRead, UserMeResponse
from app.schemas.responses import CredentialLink, VerificationEvent
from app.services.admin_service import list_specialties
from app.services.appointment_service import (
    create_availability_slot,
    delete_availability_slot,
    list_doctor_slots,
    list_public_doctor_slots,
)
from app.services.doctor_service import (
    CREDENTIAL_BUCKET,
    add_doctor_credential,
    detect_document_type,
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


@router.post(
    "/me/profile", response_model=DoctorProfileRead, summary="Create or update own doctor profile"
)
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


@router.post(
    "/me/credentials",
    response_model=DoctorCredentialRead,
    summary="Upload verification credential document",
    dependencies=[Depends(limit_by_user("upload", "RATE_LIMIT_UPLOAD"))],
)
def upload_credential(
    document_type: str = Form(
        ..., pattern=r"^[a-z_]{2,50}$", description="e.g. bmdc_license, mbbs_degree, certificate"
    ),
    file: UploadFile = File(...),
    current_user: UserMeResponse = Depends(require_doctor),
) -> DoctorCredentialRead:
    """Stores a verified file in private Storage under a path the caller has no say in."""
    content = file.file.read(settings.MAX_UPLOAD_BYTES + 1)
    if len(content) > settings.MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="This file is too large. The limit is 10 MB.",
        )

    detected = detect_document_type(content)
    if not detected:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Please upload a PDF, PNG, JPEG or WebP file.",
        )
    content_type, extension = detected

    admin_client = get_supabase_admin_client()
    if not admin_client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Credential storage is unavailable",
        )

    target_path = f"{current_user.id}/{uuid.uuid4()}{extension}"
    try:
        admin_client.storage.from_(CREDENTIAL_BUCKET).upload(
            path=target_path,
            file=content,
            file_options={"content-type": content_type},
        )
    except Exception as e:
        # A record must never point at a document an admin cannot open
        logger.error(f"Credential upload failed for {current_user.id}: {type(e).__name__}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Your document could not be uploaded. Please try again.",
        ) from e

    return add_doctor_credential(
        user_id=current_user.id,
        file_path=target_path,
        document_type=document_type,
    )


@router.get(
    "/me/credentials",
    response_model=list[DoctorCredentialRead],
    summary="List own credential documents",
)
def get_my_credentials(
    current_user: UserMeResponse = Depends(require_doctor),
    db: SyncPostgrestClient = Depends(get_user_db),
) -> list[DoctorCredentialRead]:
    return list_my_credentials(current_user.id, db)


@router.get(
    "/me/verification-history",
    response_model=list[VerificationEvent],
    summary="List own verification status events",
)
def get_my_verification_history(
    current_user: UserMeResponse = Depends(require_doctor),
) -> list[dict[str, Any]]:
    return get_verification_history(current_user.id)


@router.get(
    "/credentials/{id}/url",
    response_model=CredentialLink,
    summary="Get a short-lived link to a credential document",
)
def get_credential_link(
    id: UuidStr,
    current_user: UserMeResponse = Depends(get_current_user),
) -> dict[str, str]:
    return get_credential_url(id, current_user.id, current_user.role == UserRole.ADMIN)


@router.post(
    "/me/slots",
    response_model=SlotResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an availability slot",
)
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


@router.get(
    "/me/slots", response_model=list[SlotResponse], summary="List doctor's availability slots"
)
def get_my_slots(
    include_booked: bool = Query(default=True, description="Whether to include booked slots"),
    current_user: UserMeResponse = Depends(require_doctor),
) -> list[SlotResponse]:
    """Retrieve all availability slots for the authenticated doctor."""
    return list_doctor_slots(
        doctor_user_id=current_user.id,
        include_booked=include_booked,
    )


@router.delete(
    "/me/slots/{slot_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an availability slot",
)
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


@router.get(
    "/specialties", response_model=list[SpecialtyRead], summary="List all medical specialties"
)
def get_public_specialties() -> list[SpecialtyRead]:
    """Public listing of all available medical specialties."""
    return list_specialties()


@router.get(
    "/search", response_model=DoctorSearchResult, summary="Search verified approved doctors"
)
def search_doctors(
    specialty: str | None = Query(
        default=None, max_length=100, description="Specialty name or ID filter"
    ),
    city: str | None = Query(default=None, max_length=100, description="City location filter"),
    max_fee: float | None = Query(
        default=None, ge=0, le=MAX_CONSULTATION_FEE, description="Maximum consultation fee (BDT)"
    ),
    min_experience: int | None = Query(
        default=None,
        ge=0,
        le=MAX_YEARS_EXPERIENCE,
        description="Minimum years of clinical experience",
    ),
    sort_by: Literal["fee_asc", "fee_desc", "experience_desc"] | None = Query(
        default=None, description="Sort order"
    ),
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


@router.get(
    "/{id}", response_model=PublicDoctorRead, summary="Get public profile of an approved doctor"
)
def get_doctor_by_id(
    id: UuidStr,
) -> PublicDoctorRead:
    """Fetch public profile of an approved doctor. Returns 404 if not found or unapproved."""
    return get_public_doctor_by_id(doctor_id=id)


@router.get(
    "/{id}/slots",
    response_model=list[SlotResponse],
    summary="Get public upcoming available slots of an approved doctor",
)
def get_doctor_slots(
    id: UuidStr,
) -> list[SlotResponse]:
    """Fetch upcoming unbooked slots for an approved doctor."""
    return list_public_doctor_slots(doctor_id=id)
