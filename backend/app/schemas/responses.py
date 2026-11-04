"""Response models. Each one is a whitelist: a field not listed here cannot reach a client."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.enums import UserRole, VerificationStatus
from app.schemas.doctor import DoctorCredentialRead
from app.schemas.profile import SpecialtyRead


class ErrorResponse(BaseModel):
    detail: Any = Field(description="A message, or a list of field problems for a 422")
    code: str = Field(description="Stable machine-readable error code")
    request_id: str = Field(description="Quote this when reporting a problem")


class MessageResponse(BaseModel):
    message: str


class RegisterResponse(BaseModel):
    message: str
    user_id: str
    role: UserRole
    verification_status: VerificationStatus | None = None


class ChatHistoryDeleted(BaseModel):
    conversations_deleted: int


class VerificationEvent(BaseModel):
    action: str
    created_at: datetime
    reason: str | None = None


class CredentialLink(BaseModel):
    url: str


class ConversationSummary(BaseModel):
    id: str
    patient_id: str
    title: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ConversationCreated(BaseModel):
    id: str
    patient_id: str
    title: str | None = None
    initial_message: str
    created_at: datetime | None = None


class ChatMessage(BaseModel):
    id: str
    conversation_id: str
    sender: str
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class ConversationDetail(BaseModel):
    id: str
    patient_id: str
    title: str | None = None
    created_at: datetime | None = None
    messages: list[ChatMessage]


class AdminPatient(BaseModel):
    id: str
    full_name: str
    phone: str | None = None
    created_at: datetime | None = None
    appointment_count: int = 0


class AdminPatientPage(BaseModel):
    items: list[AdminPatient]
    total: int
    limit: int
    offset: int


class AdminDoctor(BaseModel):
    id: str
    user_id: str
    full_name: str | None = None
    phone: str | None = None
    bio: str | None = None
    qualifications: list[str] = Field(default_factory=list)
    years_experience: int = 0
    consultation_fee: float = 0.0
    clinic_name: str | None = None
    city: str
    verification_status: VerificationStatus
    specialties: list[SpecialtyRead] = Field(default_factory=list)
    credentials: list[DoctorCredentialRead] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class AdminDoctorPage(BaseModel):
    items: list[AdminDoctor]
    total: int
    limit: int
    offset: int


class DoctorActionResponse(BaseModel):
    message: str
    doctor_id: str
    verification_status: VerificationStatus
    reason: str | None = None
