from datetime import datetime
from typing import List, Optional
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
    description: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class DoctorProfileRead(BaseModel):
    id: str
    user_id: str
    bio: Optional[str] = None
    qualifications: List[str] = Field(default_factory=list)
    years_experience: int = 0
    consultation_fee: float = 0.0
    clinic_name: Optional[str] = None
    city: str
    verification_status: VerificationStatus
    specialties: List[SpecialtyRead] = Field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class DoctorProfileUpdate(BaseModel):
    bio: Optional[str] = Field(default=None, max_length=MAX_BIO_LENGTH)
    qualifications: Optional[List[ShortText]] = Field(default=None, max_length=MAX_QUALIFICATIONS)
    years_experience: Optional[int] = Field(default=None, ge=0, le=MAX_YEARS_EXPERIENCE)
    consultation_fee: Optional[float] = Field(default=None, ge=0, le=MAX_CONSULTATION_FEE)
    clinic_name: Optional[str] = Field(default=None, max_length=200)
    city: Optional[str] = Field(default=None, max_length=100)

    model_config = ConfigDict(extra="forbid")


class ProfileRead(BaseModel):
    id: str
    role: UserRole
    full_name: str
    phone: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ProfileUpdate(BaseModel):
    full_name: Optional[str] = Field(default=None, min_length=2, max_length=150)
    phone: Optional[str] = Field(default=None, max_length=25)
    ai_consent: Optional[bool] = None
    doctor_profile: Optional[DoctorProfileUpdate] = None

    # Forbid any extra fields like 'role' or 'verification_status'
    model_config = ConfigDict(extra="forbid")


class UserMeResponse(BaseModel):
    id: str
    email: Optional[str] = None
    role: UserRole
    full_name: str
    phone: Optional[str] = None
    doctor_profile: Optional[DoctorProfileRead] = None
    ai_consent_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

