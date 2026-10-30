from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from app.api.deps import require_patient
from app.schemas.profile import UserMeResponse
from app.services.chat_service import (
    create_conversation,
    get_conversation_history,
    send_patient_message,
)

router = APIRouter(prefix="/chat", tags=["Symptom Assistant Chat"])


class CreateConversationRequest(BaseModel):
    title: Optional[str] = Field(default=None, max_length=150, description="Optional title for the consultation")


class SendMessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=2000, description="Patient symptom description or answer")


class SendMessageResponse(BaseModel):
    conversation_id: str
    assistant_reply: str
    current_step: str
    search_criteria: Optional[Dict[str, Any]] = None
    recommendations: Optional[List[Dict[str, Any]]] = None


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

