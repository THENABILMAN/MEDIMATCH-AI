from datetime import UTC, datetime

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from app.models.enums import AppointmentStatus
from app.schemas.common import UuidStr


class SlotCreate(BaseModel):
    start_time: AwareDatetime = Field(description="Slot start, with a UTC offset")
    end_time: AwareDatetime = Field(description="Slot end, with a UTC offset")

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_slot_times(self) -> "SlotCreate":
        start, end = self.start_time, self.end_time

        if start <= datetime.now(UTC):
            raise ValueError("Slot start_time must be in the future.")

        if end <= start:
            raise ValueError("Slot end_time must be strictly greater than start_time.")

        duration_minutes = (end - start).total_seconds() / 60.0
        if duration_minutes < 15.0:
            raise ValueError(
                f"Slot duration must be at least 15 minutes (provided {duration_minutes:.1f} minutes)."
            )

        return self


class SlotResponse(BaseModel):
    id: str
    doctor_id: str
    start_time: datetime
    end_time: datetime
    is_booked: bool
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class AppointmentCreate(BaseModel):
    slot_id: UuidStr = Field(description="UUID of the availability slot to book")

    model_config = ConfigDict(extra="forbid")


class AppointmentCancelRequest(BaseModel):
    reason: str | None = Field(
        default=None, max_length=500, description="Optional cancellation reason"
    )

    model_config = ConfigDict(extra="forbid")


class AppointmentDoctorInfo(BaseModel):
    id: str
    full_name: str
    clinic_name: str | None = None
    city: str
    consultation_fee: float = 0.0
    specialties: list[str] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class AppointmentPatientInfo(BaseModel):
    id: str
    full_name: str
    phone: str | None = None
    email: str | None = None

    model_config = ConfigDict(from_attributes=True)


class AppointmentResponse(BaseModel):
    id: str
    patient_id: str
    doctor_id: str
    slot_id: str | None = None
    status: AppointmentStatus
    created_at: datetime
    updated_at: datetime | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    doctor: AppointmentDoctorInfo | None = None
    patient: AppointmentPatientInfo | None = None

    model_config = ConfigDict(from_attributes=True)
