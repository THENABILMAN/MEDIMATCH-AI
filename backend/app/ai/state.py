"""Typed State and Extraction Schemas for LangGraph Workflow."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from typing_extensions import TypedDict


class ExtractedSymptoms(BaseModel):
    """Structured extraction produced by LLM from patient conversation."""

    symptoms: list[str] = Field(
        default_factory=list,
        description="Extracted clinical symptoms (e.g., headache, fever, chest tightness)",
    )
    duration: str | None = Field(
        default=None, description="How long symptoms have lasted (e.g. 3 days, 2 weeks)"
    )
    severity: str | None = Field(
        default=None, description="Reported severity (mild, moderate, severe)"
    )
    age_group: str | None = Field(
        default=None, description="Patient age group if mentioned (child, adult, elderly)"
    )
    location: str | None = Field(
        default=None, description="Patient city or preferred area (e.g. Dhaka, Chittagong, Sylhet)"
    )
    preferred_max_fee: float | None = Field(
        default=None, description="Budget or max fee in BDT if mentioned"
    )
    candidate_specialty_names: list[str] = Field(
        default_factory=list,
        description="Suggested medical specialties based on symptoms (e.g. Neurology, Cardiology, General Medicine)",
    )

    model_config = ConfigDict(extra="ignore")


class ConversationIntent(BaseModel):
    """LLM-routed intent for the latest patient message."""

    intent: Literal["symptom_update", "general_conversation"] = Field(
        description="Whether the latest message adds clinical/search information or is conversational."
    )
    possible_emergency: bool = Field(
        default=False,
        description="True if the latest message could describe a life-threatening emergency or self-harm.",
    )

    model_config = ConfigDict(extra="ignore")


class SearchCriteria(BaseModel):
    """Finalized doctor search criteria mapped to verified database specialties."""

    candidate_specialties: list[str] = Field(
        default_factory=list, description="Verified specialty names from DB"
    )
    city: str = Field(default="Dhaka", description="Target city for doctor search")
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
    missing_fields: list[str]
    followup_count: int
    search_criteria: dict[str, Any] | None
    current_step: str
    assistant_reply: str | None
    intent: Literal["symptom_update", "general_conversation"]
