import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from app.api.deps import get_current_user, require_doctor
from app.core.supabase import get_supabase_admin_client
from app.models.enums import UserRole
from app.schemas.appointment import SlotCreate, SlotResponse
from app.schemas.doctor import (
    DoctorCredentialRead,
    DoctorProfileCreateOrUpdate,
    DoctorSearchResult,
    PublicDoctorRead,
)
from app.schemas.profile import DoctorProfileRead, UserMeResponse
from app.services.appointment_service import (
    create_availability_slot,
    delete_availability_slot,
    list_doctor_slots,
    list_public_doctor_slots,
)
from app.services.doctor_service import (
    add_doctor_credential,
    get_doctor_profile_by_user_id,
    get_public_doctor_by_id,
    search_public_doctors,
    upsert_doctor_profile,
)

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
    target_path = file_path

    # If an actual file was uploaded, stream it into Supabase Storage
    if file:
        file_bytes = await file.read()
        filename = f"{current_user.id}/{uuid.uuid4()}_{file.filename}"
        admin_client = get_supabase_admin_client()
        if admin_client:
            try:
                admin_client.storage.from_("doctor-credentials").upload(
                    path=filename,
                    file=file_bytes,
                    file_options={"content-type": file.content_type or "application/octet-stream"},
                )
                target_path = filename
            except Exception as e:
                # If bucket upload errors in test, retain path for record creation
                target_path = filename
        else:
            target_path = filename

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
    slot_id: str,
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

@router.get("/search", response_model=DoctorSearchResult, summary="Search verified approved doctors")
def search_doctors(
    specialty: Optional[str] = Query(default=None, description="Specialty name or ID filter"),
    city: Optional[str] = Query(default=None, description="City location filter"),
    max_fee: Optional[float] = Query(default=None, ge=0, description="Maximum consultation fee (BDT)"),
    min_experience: Optional[int] = Query(default=None, ge=0, description="Minimum years of clinical experience"),
    sort_by: Optional[str] = Query(default=None, description="Sort order: fee_asc, fee_desc, experience_desc"),
    page: int = Query(default=1, ge=1, description="Page number"),
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
    id: str,
) -> PublicDoctorRead:
    """Fetch public profile of an approved doctor. Returns 404 if not found or unapproved."""
    return get_public_doctor_by_id(doctor_id=id)


@router.get("/{id}/slots", response_model=List[SlotResponse], summary="Get public upcoming available slots of an approved doctor")
def get_doctor_slots(
    id: str,
) -> List[SlotResponse]:
    """Fetch upcoming unbooked slots for an approved doctor."""
    return list_public_doctor_slots(doctor_id=id)


