"""Typed State and Extraction Schemas for LangGraph Workflow."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from typing_extensions import TypedDict


class AssistantTurn(BaseModel):
    """One turn from the model: what to say, and what it learned."""

    reply: str = Field(min_length=1, description="What to say to the patient, in their language")
    possible_emergency: bool = Field(
        default=False,
        description="True if the message could describe a life-threatening emergency or self-harm",
    )
    symptoms: list[str] = Field(
        default_factory=list, description="Symptoms the patient has described, in plain words"
    )
    duration: str | None = Field(default=None, description="How long symptoms have lasted")
    severity: str | None = Field(default=None, description="How severe the patient says they are")
    age_group: str | None = Field(default=None, description="Patient age group if mentioned")
    location: str | None = Field(default=None, description="City the patient wants a doctor in")
    preferred_max_fee: float | None = Field(default=None, description="Budget in BDT if mentioned")
    candidate_specialty_names: list[str] = Field(
        default_factory=list, description="Suitable specialties, from the available list only"
    )
    ready_to_search: bool = Field(
        default=False, description="True when there is enough to look for doctors"
    )
    asking_about: Literal["symptoms", "duration", "location", "severity"] | None = Field(
        default=None, description="What the question in this reply asks for, if anything"
    )

    model_config = ConfigDict(extra="ignore")


class SearchCriteria(BaseModel):
    """Finalized doctor search criteria mapped to verified database specialties."""

    candidate_specialties: list[str] = Field(
        default_factory=list, description="Verified specialty names from DB"
    )
    city: str = Field(description="Target city for doctor search")
    max_fee: float | None = Field(default=None, description="Maximum consultation fee filter")
    keywords: list[str] = Field(
        default_factory=list, description="Key symptom keywords for retrieval"
    )


# What carries over between turns. Everything else is rebuilt from the messages each time
PERSISTED_STATE_FIELDS = (
    "symptoms",
    "duration",
    "severity",
    "age_group",
    "location",
    "preferred_max_fee",
    "candidate_specialty_names",
    "followup_count",
)


class ConversationState(TypedDict, total=False):
    """Typed state passed through LangGraph nodes."""

    conversation_id: str
    patient_id: str
    messages: list[dict[str, str]]
    symptoms: list[str]
    duration: str | None
    severity: str | None
    age_group: str | None
    location: str | None
    preferred_max_fee: float | None
    candidate_specialty_names: list[str]
    safety_status: str  # "safe" | "emergency"
    asking_about: str | None
    ready_to_search: bool
    followup_count: int
    search_criteria: dict[str, Any] | None
    current_step: str
    assistant_reply: str | None
