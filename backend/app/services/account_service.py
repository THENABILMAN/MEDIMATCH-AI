"""Patient privacy controls: erase chat history and anonymize accounts."""

import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from fastapi import HTTPException, status

from app.core.config import settings
from app.core.supabase import get_supabase_admin_client
from app.models.enums import AppointmentStatus, UserRole
from app.services.audit_service import log_audit_event

logger = logging.getLogger(__name__)

DELETED_PATIENT_NAME = "Deleted Patient"


def _get_admin_client() -> Any:
    client = get_supabase_admin_client()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service unavailable",
        )
    return client


def _erase_chat_data(client: Any, user_id: str) -> int:
    """Removes conversations, their messages (by cascade) and symptom sessions."""
    conversations = client.table("conversations").select("id").eq("patient_id", user_id).execute()

    # Messages and saved assistant state go with their conversation
    client.table("conversations").delete().eq("patient_id", user_id).execute()
    client.table("patient_symptom_sessions").delete().eq("patient_id", user_id).execute()

    return len(conversations.data or [])


def purge_expired_chats() -> int:
    """Erases chats and symptom sessions past the retention period. Run on a schedule."""
    client = _get_admin_client()
    cutoff = (datetime.now(timezone.utc) - timedelta(days=settings.CHAT_RETENTION_DAYS)).isoformat()

    expired = client.table("conversations").delete().lt("updated_at", cutoff).execute()
    client.table("patient_symptom_sessions").delete().lt("created_at", cutoff).execute()

    count = len(expired.data or [])
    log_audit_event(
        actor_id=None,
        action="PURGE_EXPIRED_CHATS",
        target_type="conversations",
        metadata={"conversations_deleted": count, "retention_days": settings.CHAT_RETENTION_DAYS},
    )
    return count


def delete_chat_history(user_id: str) -> Dict[str, Any]:
    """Permanently erases the user's conversations and symptom sessions."""
    client = _get_admin_client()
    deleted = _erase_chat_data(client, user_id)

    log_audit_event(
        actor_id=user_id,
        action="DELETE_CHAT_HISTORY",
        target_type="profiles",
        target_id=user_id,
        metadata={"conversations_deleted": deleted},
    )
    return {"conversations_deleted": deleted}


def _has_upcoming_appointment(client: Any, user_id: str) -> bool:
    res = (
        client.table("appointments")
        .select("id, availability_slots(start_time)")
        .eq("patient_id", user_id)
        .eq("status", AppointmentStatus.BOOKED.value)
        .execute()
    )
    now = datetime.now(timezone.utc).isoformat()
    for row in res.data or []:
        start_time = (row.get("availability_slots") or {}).get("start_time")
        if start_time and start_time > now:
            return True
    return False


def anonymize_patient_account(user_id: str, role: UserRole) -> Dict[str, Any]:
    """Closes a patient account while keeping doctors' appointment records intact.

    The profile row must stay because appointments reference it, so identifying fields are
    cleared and the sign-in identity is replaced and banned.
    """
    if role != UserRole.PATIENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only patient accounts can be closed here. Please contact support.",
        )

    client = _get_admin_client()
    if _has_upcoming_appointment(client, user_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cancel your upcoming appointments before closing your account.",
        )

    # Identity first: if this fails, nothing has been erased and the patient can retry
    try:
        client.auth.admin.update_user_by_id(
            user_id,
            {
                "email": f"deleted-{user_id}@deleted.medimatch.invalid",
                "password": secrets.token_urlsafe(32),
                "user_metadata": {},
                "ban_duration": "876000h",
            },
        )
    except Exception as e:
        logger.error(f"Could not anonymize auth user {user_id}: {type(e).__name__}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Your account could not be closed. Please try again.",
        )

    _erase_chat_data(client, user_id)
    client.table("profiles").update({
        "full_name": DELETED_PATIENT_NAME,
        "phone": None,
        "ai_consent_at": None,
        "deleted_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", user_id).execute()

    log_audit_event(
        actor_id=user_id,
        action="ANONYMIZE_PATIENT_ACCOUNT",
        target_type="profiles",
        target_id=user_id,
    )
    return {"message": "Your account has been closed."}
