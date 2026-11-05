"""Typed State and Extraction Schemas for LangGraph Workflow."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from typing_extensions import TypedDict

Language = Literal["en", "bn", "banglish"]
QuestionGoal = Literal[
    "symptoms",
    "clarify_meaning",
    "duration",
    "severity",
    "daily_impact",
    "care_preference",
    "location",
]
ChipMeaning = Literal["physical", "emotional", "both", "any_city", "other"]


class TurnAnalysis(BaseModel):
    """The hidden first step of a turn. None of this ever reaches the patient."""

    possible_emergency: Literal["none", "physical", "self_harm"] = "none"
    language: Language = "en"
    emotional_state: Literal["calm", "distressed", "anxious", "angry", "sad"] = "calm"
    symptoms: list[str] = Field(default_factory=list)
    duration: str | None = None
    severity: str | None = None
    daily_impact: str | None = None
    age_group: str | None = None
    location: str | None = None
    preferred_max_fee: float | None = None
    urgency: Literal["routine", "soon", "unknown"] = "unknown"
    care_preference: Literal["talking", "medical", "either"] | None = None
    specialty_confidence: dict[str, float] = Field(default_factory=dict)
    physical_symptoms_too: bool = False
    ambiguous_phrases: list[str] = Field(default_factory=list)
    ambiguity_answer: Literal["emotional", "physical", "both", "unclear"] | None = None
    next_question: QuestionGoal | None = None
    wants_doctors_now: bool = False
    wants_to_keep_refining: bool = False
    answer_basis: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="ignore")


class WriterChip(BaseModel):
    """A short tappable answer. The patient sees only the label."""

    label: str = Field(min_length=1, max_length=40)
    meaning: ChipMeaning = "other"


class WriterTurn(BaseModel):
    """The second step of a turn: what the patient reads."""

    reply: str = Field(min_length=1, description="What to say to the patient, in their language")
    chips: list[WriterChip] = Field(
        default_factory=list, description="Up to 3 short answers to your question, or none"
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
    strict_specialty: bool = Field(
        default=True, description="Show General Medicine only when routing chose it"
    )


# What carries over between turns. Everything else is rebuilt from the messages each time.
# emotional_state is left out on purpose: it sets one reply's tone and is never kept.
PERSISTED_STATE_FIELDS = (
    "symptoms",
    "duration",
    "severity",
    "daily_impact",
    "age_group",
    "location",
    "preferred_max_fee",
    "urgency",
    "care_preference",
    "physical_symptoms_too",
    "candidate_specialty_names",
    "specialty_confidence",
    "ambiguity_flags",
    "asked_questions",
    "question_count",
    "language",
    "crisis_active",
    "escape_pending",
    "pending_chips",
    "routing_log",
)


class ConversationState(TypedDict, total=False):
    """Typed state passed through LangGraph nodes."""

    conversation_id: str
    patient_id: str
    messages: list[dict[str, str]]
    symptoms: list[str]
    duration: str | None
    severity: str | None
    daily_impact: str | None
    age_group: str | None
    location: str | None
    preferred_max_fee: float | None
    urgency: str
    care_preference: str | None
    physical_symptoms_too: bool
    candidate_specialty_names: list[str]
    specialty_confidence: dict[str, float]
    ambiguity_flags: dict[str, str]  # phrase id -> "open", or how the patient explained it
    asked_questions: list[str]  # goal labels only, never patient text
    question_count: int
    followup_count: int  # read from conversations saved before question_count existed
    language: str
    emotional_state: str
    crisis_active: bool
    escape_pending: bool
    pending_chips: list[dict[str, str]]
    routing_log: list[dict[str, Any]]
    safety_status: str  # "safe" | "emergency"
    safety_kind: str | None  # "physical" | "self_harm"
    asking_about: str | None
    action: str  # "ask" | "search" | "talk" | "support"
    search_reason: str | None
    searched_everywhere: bool
    soft_limit_reached: bool
    search_criteria: dict[str, Any] | None
    recommendations: list[dict[str, Any]]
    chips: list[str]
    current_step: str
    assistant_reply: str | None
