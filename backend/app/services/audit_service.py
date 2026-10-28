import logging
from typing import Any, Dict, Optional
from app.core.supabase import get_supabase_admin_client

logger = logging.getLogger(__name__)


def log_audit_event(
    actor_id: Optional[str],
    action: str,
    target_type: str,
    target_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """Records an immutable security/system event in the audit_logs table."""
    admin_client = get_supabase_admin_client()
    if not admin_client:
        logger.warning(f"Audit log skipped (no admin client): {action} by {actor_id}")
        return

    try:
        data = {
            "actor_id": actor_id,
            "action": action,
            "target_type": target_type,
            "target_id": str(target_id) if target_id else None,
            "metadata": metadata or {},
        }
        admin_client.table("audit_logs").insert(data).execute()
    except Exception as e:
        logger.error(f"Failed to record audit log: {e}")

