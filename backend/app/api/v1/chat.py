from typing import Any, Literal

from fastapi import APIRouter, Depends, Query, status
from postgrest import SyncPostgrestClient
from pydantic import BaseModel, Field, model_validator

from app.api.deps import get_user_db, require_patient
from app.core.rate_limit import limit_by_user
from app.schemas.common import UuidStr
from app.schemas.profile import UserMeResponse
from app.schemas.responses import ConversationCreated, ConversationDetail, ConversationSummary
from app.search.recommend import DoctorRecommendation
from app.services.chat_service import (
    create_conversation,
    get_conversation_history,
    list_patient_conversations,
    send_patient_message,
)

router = APIRouter(prefix="/chat", tags=["Symptom Assistant Chat"])


class CreateConversationRequest(BaseModel):
    title: str | None = Field(
        default=None, max_length=150, description="Optional title for the consultation"
    )


class SendMessageRequest(BaseModel):
    content: str | None = Field(
        default=None,
        min_length=1,
        max_length=2000,
        description="Patient symptom description or answer",
    )
    message: str | None = Field(
        default=None,
        min_length=1,
        max_length=2000,
        description="Alternative field name for message content",
    )

    @model_validator(mode="after")
    def resolve_message_content(self) -> "SendMessageRequest":
        if not self.content and not self.message:
            raise ValueError("Message content must be provided.")
        if not self.content and self.message:
            self.content = self.message
        return self


class Chip(BaseModel):
    """A tappable answer. Tapping one sends its label as a normal message."""

    label: str


class SendMessageResponse(BaseModel):
    conversation_id: str
    assistant_reply: str
    current_step: str
    safety_status: str
    is_emergency: bool
    search_criteria: dict[str, Any] | None = None
    recommendations: list[DoctorRecommendation] | None = None
    followup_field: str | None = None
    chips: list[Chip] = Field(default_factory=list)
    safety_kind: Literal["physical", "self_harm"] | None = None


@router.get(
    "/conversations",
    response_model=list[ConversationSummary],
    summary="List patient's consultation conversations",
)
def api_list_conversations(
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: UserMeResponse = Depends(require_patient),
    db: SyncPostgrestClient = Depends(get_user_db),
) -> list[dict[str, Any]]:
    """Retrieves all consultation conversations belonging to the authenticated patient."""
    return list_patient_conversations(patient_id=current_user.id, db=db, limit=limit, offset=offset)


@router.post(
    "/conversations",
    response_model=ConversationCreated,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new symptom consultation conversation",
)
def api_create_conversation(
    payload: CreateConversationRequest | None = None,
    current_user: UserMeResponse = Depends(require_patient),
) -> dict[str, Any]:
    """Initializes a new consultation conversation session for the authenticated patient."""
    title = payload.title if payload else None
    return create_conversation(patient_id=current_user.id, title=title)


@router.post(
    "/conversations/{id}/messages",
    response_model=SendMessageResponse,
    summary="Send a message in the consultation conversation",
    dependencies=[Depends(limit_by_user("chat", "RATE_LIMIT_CHAT"))],
)
def api_send_message(
    id: UuidStr,
    payload: SendMessageRequest,
    current_user: UserMeResponse = Depends(require_patient),
) -> SendMessageResponse:
    """Processes a patient's symptoms through LangGraph and returns assistant reply / search criteria."""
    result = send_patient_message(
        conversation_id=id,
        patient_id=current_user.id,
        message_content=payload.content or "",
        consented=current_user.ai_consent_at is not None,
    )
    return SendMessageResponse(
        conversation_id=result["conversation_id"],
        assistant_reply=result["assistant_reply"],
        current_step=result["current_step"],
        safety_status=result.get("safety_status", "safe"),
        is_emergency=result.get("safety_status") == "emergency",
        search_criteria=result.get("search_criteria"),
        recommendations=result.get("recommendations"),
        followup_field=result.get("followup_field"),
        chips=[Chip(label=label) for label in result.get("chips") or []],
        safety_kind=result.get("safety_kind"),
    )


@router.get(
    "/conversations/{id}",
    response_model=ConversationDetail,
    summary="Get conversation history and status",
)
def api_get_conversation(
    id: UuidStr,
    current_user: UserMeResponse = Depends(require_patient),
    db: SyncPostgrestClient = Depends(get_user_db),
) -> dict[str, Any]:
    """Retrieves conversation history. Enforces strict patient ownership."""
    return get_conversation_history(conversation_id=id, patient_id=current_user.id, db=db)
