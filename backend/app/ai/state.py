"""What the assistant records each turn and keeps between turns."""

from typing import Any, Literal

from pydantic import BaseModel, Field
from typing_extensions import TypedDict


class Condition(BaseModel):
    name: str
    likelihood: int


class Assessment(BaseModel):
    """The hidden medical step. The fields are in the order the model should think in."""

    language: Literal["English", "Bangla", "Banglish"]
    has_health_problem: bool
    new_findings: list[str]
    city: str | None
    max_fee: float | None
    wants_doctors_now: bool
    possible_conditions: list[Condition]
    confidence: int
    specialty: str | None
    next_question: str
    answer_options: list[str]


class SearchCriteria(BaseModel):
    candidate_specialties: list[str] = Field(default_factory=list)
    city: str
    max_fee: float | None = None
    keywords: list[str] = Field(default_factory=list)
    strict_specialty: bool = True


# What is saved with the conversation between turns
PERSISTED_STATE_FIELDS = (
    "findings",
    "city",
    "max_fee",
    "possible_conditions",
    "confidence",
    "specialty",
    "question_count",
    "city_asks",
    "shown_search",
    "shown_bookable",
    "crisis_active",
)


class ConversationState(TypedDict, total=False):
    conversation_id: str
    patient_id: str
    messages: list[dict[str, str]]
    language: str
    findings: list[str]
    city: str | None
    max_fee: float | None
    possible_conditions: list[dict[str, Any]]
    confidence: int
    specialty: str | None
    next_question: str
    passages: list[str]
    question_count: int
    city_asks: int
    shown_search: list[str]
    shown_bookable: bool
    crisis_active: bool
    action: str  # "chat" | "ask" | "ask_city" | "search" | "support"
    asking_about: str | None
    safety_status: str  # "safe" | "emergency"
    safety_kind: str | None  # "physical" | "self_harm"
    search_criteria: dict[str, Any] | None
    recommendations: list[dict[str, Any]]
    chips: list[str]
    current_step: str
    assistant_reply: str | None
