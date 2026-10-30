"""Chat Service Module for MediMatch AI.

Manages conversational sessions in Supabase, verifies patient ownership,
persists message history, and coordinates LangGraph workflow execution.
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status

from app.ai.graph import get_symptom_graph
from app.core.supabase import get_supabase_admin_client, get_supabase_client

logger = logging.getLogger("medimatch.chat_service")

DISCLAIMER_MESSAGE = (
    "Hello! I am your MediMatch Assistant.\n\n"
    "⚠️ Medical Disclaimer: I am an AI assistant designed solely to help you find qualified medical specialists. "
    "I do not provide medical diagnosis, clinical treatment plans, or drug prescriptions. "
    "If you are experiencing a life-threatening medical emergency, please call 999 immediately.\n\n"
    "Please describe your symptoms, how long you've had them, and your preferred city or location."
)


def create_conversation(patient_id: str, title: Optional[str] = None) -> Dict[str, Any]:
    """Creates a new conversation session and seeds initial greeting with mandatory disclaimer."""
    client = get_supabase_admin_client() or get_supabase_client()
    if not client:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database service unavailable")

    conv_title = title.strip() if title else "Symptom Consultation"
    res = client.table("conversations").insert({
        "patient_id": patient_id,
        "title": conv_title,
    }).execute()

    if not res.data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to initialize conversation")

    conv = res.data[0]
    conversation_id = str(conv["id"])

    # Persist the initial greeting message with disclaimer
    client.table("messages").insert({
        "conversation_id": conversation_id,
        "sender": "assistant",
        "content": DISCLAIMER_MESSAGE,
    }).execute()

    return {
        "id": conversation_id,
        "patient_id": patient_id,
        "title": conv["title"],
        "initial_message": DISCLAIMER_MESSAGE,
        "created_at": conv.get("created_at"),
    }


def list_patient_conversations(patient_id: str) -> List[Dict[str, Any]]:
    """Lists all consultation conversations for the patient, ordered latest first."""
    client = get_supabase_admin_client() or get_supabase_client()
    if not client:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database service unavailable")

    res = (
        client.table("conversations")
        .select("*")
        .eq("patient_id", patient_id)
        .order("created_at", desc=True)
        .execute()
    )
    return res.data or []


def get_conversation_history(conversation_id: str, patient_id: str, is_admin: bool = False) -> Dict[str, Any]:
    """Retrieves conversation details and complete message history with ownership enforcement."""
    client = get_supabase_admin_client() or get_supabase_client()
    if not client:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database service unavailable")

    # Verify ownership
    conv_res = client.table("conversations").select("*").eq("id", conversation_id).execute()
    if not conv_res.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    conv = conv_res.data[0]
    if conv["patient_id"] != patient_id and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: You do not own this conversation",
        )

    # Fetch messages
    msg_res = (
        client.table("messages")
        .select("*")
        .eq("conversation_id", conversation_id)
        .order("created_at", desc=False)
        .execute()
    )

    return {
        "id": conversation_id,
        "patient_id": conv["patient_id"],
        "title": conv["title"],
        "created_at": conv.get("created_at"),
        "messages": msg_res.data or [],
    }


def send_patient_message(
    conversation_id: str,
    patient_id: str,
    message_content: str,
) -> Dict[str, Any]:
    """Processes incoming patient message through LangGraph and persists dialogue."""
    content = message_content.strip()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Message content cannot be empty")

    client = get_supabase_admin_client() or get_supabase_client()
    if not client:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database service unavailable")

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
    client.table("messages").insert({
        "conversation_id": conversation_id,
        "sender": "patient",
        "content": content,
    }).execute()

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
        "conversation_id": conversation_id,
        "patient_id": patient_id,
        "messages": formatted_messages,
    }

    config = {"configurable": {"thread_id": conversation_id}}
    result_state = graph.invoke(initial_state, config=config)

    assistant_reply = result_state.get(
        "assistant_reply",
        "Could you tell me a little more about your symptoms and location?",
    )
    current_step = result_state.get("current_step", "extract_symptoms")
    search_criteria = result_state.get("search_criteria")

    # 5. If search criteria formed, call hybrid recommender
    recommendations_list: List[Dict[str, Any]] = []
    if search_criteria:
        from app.search.recommend import recommend_doctors

        try:
            rec_res = recommend_doctors(search_criteria, top_k=5)
            recommendations_list = [r.model_dump() for r in rec_res.recommendations]

            if recommendations_list:
                doc_lines = ["\n\n### 🩺 Recommended Specialists:"]
                for i, doc in enumerate(recommendations_list[:3], 1):
                    specs_str = ", ".join([s["name"] for s in doc.get("specialties", [])])
                    doc_lines.append(
                        f"**{i}. {doc['full_name']}** — {specs_str} ({doc['city']})\n"
                        f"   • Clinical Experience: {doc['years_experience']} years | Consultation Fee: {int(doc['consultation_fee'])} BDT\n"
                        f"   • Match Score: {doc['match_score']}% | Upcoming Slots: {doc['available_slots_count']}\n"
                        f"   • _{doc['match_explanation']}_"
                    )
                assistant_reply += "\n" + "\n".join(doc_lines)
        except Exception as e:
            logger.warning(f"Could not generate recommendations during chat: {e}")

    # 6. Persist assistant reply
    client.table("messages").insert({
        "conversation_id": conversation_id,
        "sender": "assistant",
        "content": assistant_reply,
    }).execute()

    # 7. If search criteria formed or emergency flagged, record in patient_symptom_sessions
    is_emergency = result_state.get("safety_status") == "emergency"
    if search_criteria or is_emergency:
        client.table("patient_symptom_sessions").insert({
            "patient_id": patient_id,
            "raw_symptoms": content,
            "extracted_criteria": search_criteria or {},
            "emergency_flag": is_emergency,
        }).execute()

    return {
        "conversation_id": conversation_id,
        "assistant_reply": assistant_reply,
        "current_step": current_step,
        "safety_status": result_state.get("safety_status", "safe"),
        "is_emergency": is_emergency,
        "search_criteria": search_criteria,
        "recommendations": recommendations_list,
    }
