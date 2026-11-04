"""Chat Service Module for MediMatch AI.

Manages conversational sessions in Supabase, verifies patient ownership,
persists message history, and coordinates LangGraph workflow execution.
"""

import logging
from typing import Any

from fastapi import HTTPException, status
from postgrest import SyncPostgrestClient

from app.ai.graph import get_symptom_graph
from app.ai.safety import check_emergency, get_emergency_response
from app.ai.state import PERSISTED_STATE_FIELDS
from app.core.supabase import get_supabase_admin_client

logger = logging.getLogger("medimatch.chat_service")

DISCLAIMER_MESSAGE = (
    "Hello! I am your MediMatch Assistant.\n\n"
    "⚠️ Medical Disclaimer: I am an AI assistant designed solely to help you find qualified medical specialists. "
    "I do not provide medical diagnosis, clinical treatment plans, or drug prescriptions. "
    "If you are experiencing a life-threatening medical emergency, please call 999 immediately.\n\n"
    "Please describe your symptoms, how long you've had them, and your preferred city or location."
)


def create_conversation(patient_id: str, title: str | None = None) -> dict[str, Any]:
    """Creates a new conversation session and seeds initial greeting with mandatory disclaimer."""
    client = get_supabase_admin_client()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database service unavailable"
        )

    conv_title = title.strip() if title else "Symptom Consultation"
    res = (
        client.table("conversations")
        .insert(
            {
                "patient_id": patient_id,
                "title": conv_title,
            }
        )
        .execute()
    )

    if not res.data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to initialize conversation"
        )

    conv = res.data[0]
    conversation_id = str(conv["id"])

    # Persist the initial greeting message with disclaimer
    client.table("messages").insert(
        {
            "conversation_id": conversation_id,
            "sender": "assistant",
            "content": DISCLAIMER_MESSAGE,
        }
    ).execute()

    return {
        "id": conversation_id,
        "patient_id": patient_id,
        "title": conv["title"],
        "initial_message": DISCLAIMER_MESSAGE,
        "created_at": conv.get("created_at"),
    }


def list_patient_conversations(
    patient_id: str, db: SyncPostgrestClient, limit: int = 100, offset: int = 0
) -> list[dict[str, Any]]:
    """Lists all consultation conversations for the patient, ordered latest first."""
    res = (
        db.table("conversations")
        .select("*")
        .eq("patient_id", patient_id)
        .order("created_at", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
    )
    return res.data or []  # type: ignore[return-value]


def read_messages(conversation_id: str, db: SyncPostgrestClient) -> list[dict[str, Any]]:
    """Reads a conversation's messages as the caller, so RLS has the final say."""
    res = (
        db.table("messages")
        .select("*")
        .eq("conversation_id", conversation_id)
        .order("created_at", desc=False)
        .execute()
    )
    return res.data or []  # type: ignore[return-value]


def get_conversation_history(
    conversation_id: str, patient_id: str, db: SyncPostgrestClient
) -> dict[str, Any]:
    """Retrieves conversation details and complete message history with ownership enforcement."""
    client = get_supabase_admin_client()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database service unavailable"
        )

    # Verify ownership
    conv_res = client.table("conversations").select("*").eq("id", conversation_id).execute()
    if not conv_res.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    conv = conv_res.data[0]
    if conv["patient_id"] != patient_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: You do not own this conversation",
        )

    return {
        "id": conversation_id,
        "patient_id": conv["patient_id"],
        "title": conv["title"],
        "created_at": conv.get("created_at"),
        "messages": read_messages(conversation_id, db),
    }


def _emergency_turn(
    conversation_id: str, patient_id: str, content: str, consented: bool
) -> dict[str, Any]:
    """Answers an emergency with the fixed alert. It must arrive even if saving it fails.

    Someone else's conversation is still refused, but a database outage only loses the record.
    Without consent the alert is still given, and nothing the patient wrote is stored.
    """
    reply = get_emergency_response()
    try:
        client = get_supabase_admin_client()
        conversation = (
            client.table("conversations").select("patient_id").eq("id", conversation_id).execute()
        )
        if not conversation.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found"
            )
        if conversation.data[0]["patient_id"] != patient_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: You do not own this conversation",
            )

        if consented:
            client.table("messages").insert(
                {"conversation_id": conversation_id, "sender": "patient", "content": content}
            ).execute()
            client.table("messages").insert(
                {
                    "conversation_id": conversation_id,
                    "sender": "assistant",
                    "content": reply,
                    "metadata": {"is_emergency": True, "recommendations": []},
                }
            ).execute()
            client.table("patient_symptom_sessions").insert(
                {
                    "patient_id": patient_id,
                    "raw_symptoms": content,
                    "extracted_criteria": {},
                    "emergency_flag": True,
                }
            ).execute()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Emergency turn was not saved: {type(e).__name__}")

    return {
        "conversation_id": conversation_id,
        "assistant_reply": reply,
        "current_step": "emergency_escalated",
        "safety_status": "emergency",
        "is_emergency": True,
        "search_criteria": None,
        "recommendations": [],
        "followup_field": None,
    }


def send_patient_message(
    conversation_id: str,
    patient_id: str,
    message_content: str,
    consented: bool = True,
) -> dict[str, Any]:
    """Processes incoming patient message through LangGraph and persists dialogue."""
    content = message_content.strip()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Message content cannot be empty"
        )

    if check_emergency(content)[0]:
        return _emergency_turn(conversation_id, patient_id, content, consented)

    if not consented:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please agree to the AI assistant terms before describing your symptoms.",
        )

    client = get_supabase_admin_client()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database service unavailable"
        )

    # 1. Enforce ownership
    conv_res = client.table("conversations").select("*").eq("id", conversation_id).execute()
    if not conv_res.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    conv = conv_res.data[0]
    if conv["patient_id"] != patient_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: You do not own this conversation",
        )

    # 2. Persist patient message
    client.table("messages").insert(
        {
            "conversation_id": conversation_id,
            "sender": "patient",
            "content": content,
        }
    ).execute()

    # 3. Load past message history to feed the workflow state
    history_res = (
        client.table("messages")
        .select("sender, content")
        .eq("conversation_id", conversation_id)
        .order("created_at", desc=False)
        .execute()
    )

    formatted_messages = [
        {
            "role": "user" if m["sender"] == "patient" else "assistant",
            "content": m["content"],
        }
        for m in (history_res.data or [])
    ]

    # 4. Invoke LangGraph
    graph = get_symptom_graph()
    initial_state = {
        **(conv.get("graph_state") or {}),
        "conversation_id": conversation_id,
        "patient_id": patient_id,
        "messages": formatted_messages,
    }

    result_state = graph.invoke(initial_state)

    if result_state.get("safety_status") != "emergency":
        client.table("conversations").update(
            {
                "graph_state": {
                    k: result_state[k] for k in PERSISTED_STATE_FIELDS if k in result_state
                }
            }
        ).eq("id", conversation_id).execute()

    # A node can leave the reply as None, so a .get() default is not enough
    assistant_reply = (
        result_state.get("assistant_reply")
        or "Could you tell me a little more about your symptoms and location?"
    )
    current_step = result_state.get("current_step", "extract_symptoms")
    search_criteria = result_state.get("search_criteria")

    # The field being asked about lets the UI offer suggested answers
    missing_fields = result_state.get("missing_fields") or []
    followup_field = (
        missing_fields[0] if current_step == "ask_followup" and missing_fields else None
    )

    # 5. If search criteria formed, call hybrid recommender
    recommendations_list: list[dict[str, Any]] = []
    if search_criteria:
        from app.search.recommend import recommend_doctors

        try:
            rec_res = recommend_doctors(search_criteria, top_k=5)
            recommendations_list = [r.model_dump() for r in rec_res.recommendations]

        except Exception as e:
            logger.warning(f"Could not generate recommendations during chat: {type(e).__name__}")

    # 6. Persist assistant reply, with what the UI needs to redraw it on reload
    is_emergency = result_state.get("safety_status") == "emergency"
    client.table("messages").insert(
        {
            "conversation_id": conversation_id,
            "sender": "assistant",
            "content": assistant_reply,
            "metadata": {"is_emergency": is_emergency, "recommendations": recommendations_list},
        }
    ).execute()

    # 7. If search criteria formed or emergency flagged, record in patient_symptom_sessions
    if search_criteria or is_emergency:
        client.table("patient_symptom_sessions").insert(
            {
                "patient_id": patient_id,
                "raw_symptoms": content,
                "extracted_criteria": search_criteria or {},
                "emergency_flag": is_emergency,
            }
        ).execute()

    return {
        "conversation_id": conversation_id,
        "assistant_reply": assistant_reply,
        "current_step": current_step,
        "safety_status": result_state.get("safety_status", "safe"),
        "is_emergency": is_emergency,
        "search_criteria": search_criteria,
        "recommendations": recommendations_list,
        "followup_field": followup_field,
    }
