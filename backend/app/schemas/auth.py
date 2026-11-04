from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import UserRole
from app.schemas.common import (
    MAX_BIO_LENGTH,
    MAX_CONSULTATION_FEE,
    MAX_QUALIFICATIONS,
    MAX_SPECIALTIES,
    MAX_YEARS_EXPERIENCE,
    ShortText,
    UuidStr,
)

MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 72  # Supabase Auth hashes with bcrypt, which stops reading at 72 bytes


class RegisterPatientRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str = Field(min_length=MIN_PASSWORD_LENGTH, max_length=MAX_PASSWORD_LENGTH)
    full_name: str = Field(min_length=2, max_length=150)
    phone: str | None = Field(default=None, max_length=25)


class RegisterDoctorRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str = Field(min_length=MIN_PASSWORD_LENGTH, max_length=MAX_PASSWORD_LENGTH)
    full_name: str = Field(min_length=2, max_length=150)
    phone: str | None = Field(default=None, max_length=25)
    bio: str | None = Field(default=None, max_length=MAX_BIO_LENGTH)
    qualifications: list[ShortText] = Field(
        default_factory=list, max_length=MAX_QUALIFICATIONS, description="e.g. ['MBBS', 'FCPS']"
    )
    years_experience: int = Field(default=0, ge=0, le=MAX_YEARS_EXPERIENCE)
    consultation_fee: float = Field(default=0.0, ge=0, le=MAX_CONSULTATION_FEE)
    clinic_name: str | None = Field(default=None, max_length=200)
    city: str = Field(default="Dhaka", max_length=100)
    specialty_ids: list[UuidStr] = Field(
        default_factory=list, max_length=MAX_SPECIALTIES, description="List of specialty UUIDs"
    )


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(max_length=MAX_PASSWORD_LENGTH)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    role: UserRole
    full_name: str | None = None
