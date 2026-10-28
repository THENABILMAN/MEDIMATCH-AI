from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.models.enums import UserRole, VerificationStatus


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
    bio: Optional[str] = None
    qualifications: Optional[List[str]] = None
    years_experience: Optional[int] = Field(default=None, ge=0)
    consultation_fee: Optional[float] = Field(default=None, ge=0)
    clinic_name: Optional[str] = None
    city: Optional[str] = None

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
    created_at: Optional[datetime] = None

