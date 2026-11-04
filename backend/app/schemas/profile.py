from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import UserRole, VerificationStatus
from app.schemas.common import (
    MAX_BIO_LENGTH,
    MAX_CONSULTATION_FEE,
    MAX_QUALIFICATIONS,
    MAX_YEARS_EXPERIENCE,
    ShortText,
)


class SpecialtyRead(BaseModel):
    id: str
    name: str
    description: str | None = None

    model_config = ConfigDict(from_attributes=True)


class DoctorProfileRead(BaseModel):
    id: str
    user_id: str
    bio: str | None = None
    qualifications: list[str] = Field(default_factory=list)
    years_experience: int = 0
    consultation_fee: float = 0.0
    clinic_name: str | None = None
    city: str
    verification_status: VerificationStatus
    specialties: list[SpecialtyRead] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class DoctorProfileUpdate(BaseModel):
    bio: str | None = Field(default=None, max_length=MAX_BIO_LENGTH)
    qualifications: list[ShortText] | None = Field(default=None, max_length=MAX_QUALIFICATIONS)
    years_experience: int | None = Field(default=None, ge=0, le=MAX_YEARS_EXPERIENCE)
    consultation_fee: float | None = Field(default=None, ge=0, le=MAX_CONSULTATION_FEE)
    clinic_name: str | None = Field(default=None, max_length=200)
    city: str | None = Field(default=None, max_length=100)

    model_config = ConfigDict(extra="forbid")


class ProfileRead(BaseModel):
    id: str
    role: UserRole
    full_name: str
    phone: str | None = None
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class ProfileUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=150)
    phone: str | None = Field(default=None, max_length=25)
    ai_consent: bool | None = None
    doctor_profile: DoctorProfileUpdate | None = None

    # Forbid any extra fields like 'role' or 'verification_status'
    model_config = ConfigDict(extra="forbid")


class UserMeResponse(BaseModel):
    id: str
    email: str | None = None
    role: UserRole
    full_name: str
    phone: str | None = None
    doctor_profile: DoctorProfileRead | None = None
    ai_consent_at: datetime | None = None
    created_at: datetime | None = None
