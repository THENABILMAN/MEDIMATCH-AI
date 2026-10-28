from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field
from app.models.enums import UserRole


class RegisterPatientRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, description="Password must be at least 6 characters")
    full_name: str = Field(min_length=2, max_length=150)
    phone: Optional[str] = Field(default=None, max_length=25)


class RegisterDoctorRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, description="Password must be at least 6 characters")
    full_name: str = Field(min_length=2, max_length=150)
    phone: Optional[str] = Field(default=None, max_length=25)
    bio: Optional[str] = Field(default=None, max_length=2000)
    qualifications: List[str] = Field(default_factory=list, description="e.g. ['MBBS', 'FCPS']")
    years_experience: int = Field(default=0, ge=0)
    consultation_fee: float = Field(default=0.0, ge=0)
    clinic_name: Optional[str] = Field(default=None, max_length=200)
    city: str = Field(default="Dhaka", max_length=100)
    specialty_ids: List[str] = Field(default_factory=list, description="List of specialty UUIDs")


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    role: UserRole
    full_name: Optional[str] = None

