from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import VerificationStatus
from app.schemas.common import (
    MAX_BIO_LENGTH,
    MAX_CONSULTATION_FEE,
    MAX_QUALIFICATIONS,
    MAX_REASON_LENGTH,
    MAX_SPECIALTIES,
    MAX_YEARS_EXPERIENCE,
    ShortText,
    UuidStr,
)
from app.schemas.profile import SpecialtyRead


class DoctorProfileCreateOrUpdate(BaseModel):
    bio: str | None = Field(default=None, max_length=MAX_BIO_LENGTH)
    qualifications: list[ShortText] = Field(
        default_factory=list,
        max_length=MAX_QUALIFICATIONS,
        description="List of degrees e.g. ['MBBS', 'FCPS']",
    )
    years_experience: int = Field(default=0, ge=0, le=MAX_YEARS_EXPERIENCE)
    consultation_fee: float = Field(default=0.0, ge=0, le=MAX_CONSULTATION_FEE)
    clinic_name: str | None = Field(default=None, max_length=200)
    city: str = Field(default="Dhaka", max_length=100)
    specialty_ids: list[UuidStr] = Field(
        default_factory=list,
        max_length=MAX_SPECIALTIES,
        description="UUIDs of associated specialties",
    )

    model_config = ConfigDict(extra="forbid")


class DoctorCredentialRead(BaseModel):
    id: str
    doctor_id: str
    file_path: str
    document_type: str
    uploaded_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PublicDoctorRead(BaseModel):
    id: str
    full_name: str
    bio: str | None = None
    qualifications: list[str] = Field(default_factory=list)
    years_experience: int = 0
    consultation_fee: float = 0.0
    clinic_name: str | None = None
    city: str
    verification_status: VerificationStatus
    specialties: list[SpecialtyRead] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class DoctorSearchResult(BaseModel):
    items: list[PublicDoctorRead]
    total: int
    page: int
    page_size: int
    total_pages: int


class AdminDoctorActionRequest(BaseModel):
    reason: str | None = Field(
        default=None, max_length=MAX_REASON_LENGTH, description="Reason for rejection or suspension"
    )


class SpecialtyCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=1000)


class SpecialtyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=1000)


class AuditLogRead(BaseModel):
    id: str
    actor_id: str | None = None
    action: str
    target_type: str
    target_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AuditLogPaginatedResponse(BaseModel):
    items: list[AuditLogRead]
    total: int
    limit: int
    offset: int
