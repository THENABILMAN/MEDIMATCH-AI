from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.models.enums import VerificationStatus
from app.schemas.profile import SpecialtyRead


class DoctorProfileCreateOrUpdate(BaseModel):
    bio: Optional[str] = Field(default=None, max_length=2000)
    qualifications: List[str] = Field(default_factory=list, description="List of degrees e.g. ['MBBS', 'FCPS']")
    years_experience: int = Field(default=0, ge=0)
    consultation_fee: float = Field(default=0.0, ge=0)
    clinic_name: Optional[str] = Field(default=None, max_length=200)
    city: str = Field(default="Dhaka", max_length=100)
    specialty_ids: List[str] = Field(default_factory=list, description="UUIDs of associated specialties")

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
    bio: Optional[str] = None
    qualifications: List[str] = Field(default_factory=list)
    years_experience: int = 0
    consultation_fee: float = 0.0
    clinic_name: Optional[str] = None
    city: str
    verification_status: VerificationStatus
    specialties: List[SpecialtyRead] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class DoctorSearchResult(BaseModel):
    items: List[PublicDoctorRead]
    total: int
    page: int
    page_size: int
    total_pages: int


class AdminDoctorActionRequest(BaseModel):
    reason: Optional[str] = Field(default=None, description="Reason for rejection or suspension")


class SpecialtyCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    description: Optional[str] = Field(default=None, max_length=1000)


class SpecialtyUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=100)
    description: Optional[str] = Field(default=None, max_length=1000)


class AuditLogRead(BaseModel):
    id: str
    actor_id: Optional[str] = None
    action: str
    target_type: str
    target_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AuditLogPaginatedResponse(BaseModel):
    items: List[AuditLogRead]
    total: int
    limit: int
    offset: int

