from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field, model_validator

from app.api.deps import require_patient
from app.schemas.profile import UserMeResponse
from app.services.chat_service import (
    create_conversation,
    get_conversation_history,
    list_patient_conversations,
    send_patient_message,
)

router = APIRouter(prefix="/chat", tags=["Symptom Assistant Chat"])


class CreateConversationRequest(BaseModel):
    title: Optional[str] = Field(default=None, max_length=150, description="Optional title for the consultation")


class SendMessageRequest(BaseModel):
    content: Optional[str] = Field(default=None, min_length=1, max_length=2000, description="Patient symptom description or answer")
    message: Optional[str] = Field(default=None, min_length=1, max_length=2000, description="Alternative field name for message content")

    @model_validator(mode="after")
    def resolve_message_content(self) -> "SendMessageRequest":
        if not self.content and not self.message:
            raise ValueError("Message content must be provided.")
        if not self.content and self.message:
            self.content = self.message
        return self


class SendMessageResponse(BaseModel):
    conversation_id: str
    assistant_reply: str
    current_step: str
    safety_status: str
    is_emergency: bool
    search_criteria: Optional[Dict[str, Any]] = None
    recommendations: Optional[List[Dict[str, Any]]] = None


@router.get(
    "/conversations",
    summary="List patient's consultation conversations",
)
def api_list_conversations(
    current_user: UserMeResponse = Depends(require_patient),
) -> List[Dict[str, Any]]:
    """Retrieves all consultation conversations belonging to the authenticated patient."""
    return list_patient_conversations(patient_id=current_user.id)


@router.post(
    "/conversations",
    status_code=status.HTTP_201_CREATED,
    summary="Create a new symptom consultation conversation",
)
def api_create_conversation(
    payload: Optional[CreateConversationRequest] = None,
    current_user: UserMeResponse = Depends(require_patient),
) -> Dict[str, Any]:
    """Initializes a new consultation conversation session for the authenticated patient."""
    title = payload.title if payload else None
    return create_conversation(patient_id=current_user.id, title=title)



@router.post(
    "/conversations/{id}/messages",
    response_model=SendMessageResponse,
    summary="Send a message in the consultation conversation",
)
def api_send_message(
    id: str,
    payload: SendMessageRequest,
    current_user: UserMeResponse = Depends(require_patient),
) -> SendMessageResponse:
    """Processes a patient's symptoms through LangGraph and returns assistant reply / search criteria."""
    result = send_patient_message(
        conversation_id=id,
        patient_id=current_user.id,
        message_content=payload.content,
    )
    return SendMessageResponse(
        conversation_id=result["conversation_id"],
        assistant_reply=result["assistant_reply"],
        current_step=result["current_step"],
        safety_status=result.get("safety_status", "safe"),
        is_emergency=result.get("safety_status") == "emergency",
        search_criteria=result.get("search_criteria"),
        recommendations=result.get("recommendations"),
    )


@router.get(
    "/conversations/{id}",
    summary="Get conversation history and status",
)
def api_get_conversation(
    id: str,
    current_user: UserMeResponse = Depends(require_patient),
) -> Dict[str, Any]:
    """Retrieves conversation history. Enforces strict patient ownership."""
    is_admin = current_user.role == "admin"
    return get_conversation_history(
        conversation_id=id,
        patient_id=current_user.id,
        is_admin=is_admin,
    )
