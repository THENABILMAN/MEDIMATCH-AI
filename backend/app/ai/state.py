"""Typed State and Extraction Schemas for LangGraph Workflow."""

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field
from typing_extensions import TypedDict


class ExtractedSymptoms(BaseModel):
    """Structured extraction produced by LLM from patient conversation."""
    symptoms: List[str] = Field(default_factory=list, description="Extracted clinical symptoms (e.g., headache, fever, chest tightness)")
    duration: Optional[str] = Field(default=None, description="How long symptoms have lasted (e.g. 3 days, 2 weeks)")
    severity: Optional[str] = Field(default=None, description="Reported severity (mild, moderate, severe)")
    age_group: Optional[str] = Field(default=None, description="Patient age group if mentioned (child, adult, elderly)")
    location: Optional[str] = Field(default=None, description="Patient city or preferred area (e.g. Dhaka, Chittagong, Sylhet)")
    preferred_max_fee: Optional[float] = Field(default=None, description="Budget or max fee in BDT if mentioned")
    candidate_specialty_names: List[str] = Field(
        default_factory=list,
        description="Suggested medical specialties based on symptoms (e.g. Neurology, Cardiology, General Medicine)",
    )

    model_config = ConfigDict(extra="ignore")


class ConversationIntent(BaseModel):
    """LLM-routed intent for the latest patient message."""

    intent: Literal["symptom_update", "general_conversation"] = Field(
        description="Whether the latest message adds clinical/search information or is conversational."
    )
    assistant_reply: Optional[str] = Field(
        default=None,
        description="A safe, helpful reply for general conversation; null for symptom updates.",
    )


class SearchCriteria(BaseModel):
    """Finalized doctor search criteria mapped to verified database specialties."""
    candidate_specialties: List[str] = Field(default_factory=list, description="Verified specialty names from DB")
    city: str = Field(default="Dhaka", description="Target city for doctor search")
    max_fee: Optional[float] = Field(default=None, description="Maximum consultation fee filter")
    keywords: List[str] = Field(default_factory=list, description="Key symptom keywords for retrieval")


class ConversationState(TypedDict, total=False):
    """Typed state passed through LangGraph nodes."""
    conversation_id: str
    patient_id: str
    messages: List[Dict[str, str]]
    symptoms: List[str]
    duration: Optional[str]
    severity: Optional[str]
    age_group: Optional[str]
    location: Optional[str]
    preferred_max_fee: Optional[float]
    safety_status: str  # "safe" | "emergency"
    missing_fields: List[str]
    followup_count: int
    search_criteria: Optional[Dict[str, Any]]
    current_step: str
    assistant_reply: Optional[str]
    intent: Literal["symptom_update", "general_conversation"]
