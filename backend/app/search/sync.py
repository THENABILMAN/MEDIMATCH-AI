"""Vector Synchronization Pipeline for MediMatch AI.

Maintains bidirectional consistency between Supabase PostgreSQL (the single
source of truth) and the Pinecone vector index.

Ensures:
1. Only doctors with verification_status = 'approved' exist in Pinecone.
2. Unapproved, suspended, or rejected doctors have their vectors deleted immediately.
3. Doctor profiles update their sync_status and last_synced_at columns.
4. Transient network errors are automatically retried.
"""

from concurrent.futures import Future, ThreadPoolExecutor, wait
from datetime import datetime, timezone
import logging
from typing import Any, Callable, Dict, List, Optional, Set
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential
from app.core.config import settings
from app.core.supabase import get_supabase_admin_client
from app.models.enums import VerificationStatus
from app.search.builder import build_doctor_embedding_text
from app.search.embeddings import get_embedding_provider

logger = logging.getLogger("medimatch.search.sync")

# Mockable Pinecone Index Client for unit tests
_MOCK_PINECONE_INDEX: Optional[Any] = None
_PINECONE_INDEX: Optional[Any] = None

# Provider calls are slow and retried, so they must not hold up an admin's request
_sync_pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="vector-sync")
_pending_syncs: Set[Future] = set()


def run_in_background(task: Callable[..., Any], *args: Any) -> None:
    """Runs a sync after the response. A failure is recorded in sync_status by the task itself."""
    if not settings.SYNC_IN_BACKGROUND:
        task(*args)
        return

    future = _sync_pool.submit(task, *args)
    _pending_syncs.add(future)
    future.add_done_callback(_pending_syncs.discard)


def wait_for_background_syncs(timeout: float = 30.0) -> None:
    """Lets running syncs finish, so a shutdown does not leave a doctor half indexed."""
    if _pending_syncs:
        wait(list(_pending_syncs), timeout=timeout)


def get_pinecone_index() -> Any:
    """Returns the Pinecone Index instance or mock."""
    global _PINECONE_INDEX
    if _MOCK_PINECONE_INDEX is not None:
        return _MOCK_PINECONE_INDEX

    if _PINECONE_INDEX is None:
        from pinecone import Pinecone

        _PINECONE_INDEX = Pinecone(api_key=settings.PINECONE_API_KEY).Index(settings.PINECONE_INDEX)
    return _PINECONE_INDEX


def set_pinecone_index_client(client: Optional[Any]) -> None:
    """Sets a mock Pinecone index client for unit tests."""
    global _MOCK_PINECONE_INDEX
    _MOCK_PINECONE_INDEX = client


def _fetch_doctor_with_specialties(doctor_id: str) -> Optional[Dict[str, Any]]:
    """Fetches complete doctor profile and associated specialties from Supabase."""
    client = get_supabase_admin_client()
    if not client:
        return None

    res = (
        client.table("doctor_profiles")
        .select("*, doctor_specialties(specialties(id, name, description))")
        .eq("id", doctor_id)
        .execute()
    )
    if not res.data:
        return None

    doc = res.data[0]
    specs = []
    for item in doc.get("doctor_specialties", []):
        s = item.get("specialties")
        if s:
            specs.append(s)
    doc["specialties"] = specs
    return doc


def _update_sync_status(doctor_id: str, status: str) -> None:
    """Updates sync_status and last_synced_at in doctor_profiles table."""
    client = get_supabase_admin_client()
    if not client:
        return

    updates: Dict[str, Any] = {"sync_status": status}
    if status == "synced":
        updates["last_synced_at"] = datetime.now(timezone.utc).isoformat()

    try:
        client.table("doctor_profiles").update(updates).eq("id", doctor_id).execute()
    except Exception as e:
        logger.warning(f"Could not update sync_status for doctor {doctor_id}: {type(e).__name__}")


@retry(
    retry=retry_if_exception_type(Exception),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=4),
    reraise=True,
)
def _upsert_vector_to_pinecone(doctor_id: str, vector: List[float], metadata: Dict[str, Any]) -> None:
    index = get_pinecone_index()
    index.upsert(
        vectors=[
            {
                "id": doctor_id,
                "values": vector,
                "metadata": metadata,
            }
        ]
    )


@retry(
    retry=retry_if_exception_type(Exception),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=4),
    reraise=True,
)
def _delete_vector_from_pinecone(doctor_id: str) -> None:
    index = get_pinecone_index()
    index.delete(ids=[doctor_id])


def sync_doctor_vector(doctor_id: str) -> bool:
    """Synchronizes a doctor's vector with Pinecone based on Supabase record.

    If status is 'approved', generates embedding and upserts to Pinecone.
    If status is anything else ('pending', 'suspended', 'rejected'), deletes vector.
    """
    logger.info(f"[VECTOR_SYNC] Starting sync for doctor {doctor_id}")
    doc = _fetch_doctor_with_specialties(doctor_id)
    if not doc:
        logger.warning(f"[VECTOR_SYNC] Doctor {doctor_id} not found in Supabase. Deleting vector.")
        try:
            _delete_vector_from_pinecone(doctor_id)
        except Exception:
            pass
        return False

    status = doc.get("verification_status")

    # Non-negotiable Rule: Only 'approved' doctors exist in Pinecone
    if status != VerificationStatus.APPROVED.value:
        logger.info(
            f"[VECTOR_SYNC] Doctor {doctor_id} status is '{status}' (not approved). Removing from Pinecone."
        )
        try:
            _delete_vector_from_pinecone(doctor_id)
            _update_sync_status(doctor_id, "synced")
            return True
        except Exception as e:
            logger.error(f"[VECTOR_SYNC] Failed removing vector for doctor {doctor_id}: {type(e).__name__}")
            _update_sync_status(doctor_id, "failed")
            return False

    # Doctor is approved: build document and embed
    try:
        doc_text = build_doctor_embedding_text(doc)
        provider = get_embedding_provider()
        vectors = provider.embed_documents([doc_text])
        if not vectors:
            raise ValueError(f"Embedding provider produced no vector for doctor {doctor_id}")

        vector = vectors[0]
        specialty_ids = [s["id"] for s in doc.get("specialties", [])]
        specialty_names = [s["name"] for s in doc.get("specialties", [])]

        metadata = {
            "doctor_id": doctor_id,
            "specialty_ids": specialty_ids,
            "specialty_names": specialty_names,
            "city": doc.get("city", "Dhaka"),
            "status": "approved",
        }

        _upsert_vector_to_pinecone(doctor_id=doctor_id, vector=vector, metadata=metadata)
        _update_sync_status(doctor_id, "synced")
        logger.info(f"[VECTOR_SYNC] Successfully indexed doctor {doctor_id} in Pinecone")
        return True

    except Exception as e:
        logger.error(f"[VECTOR_SYNC] Error syncing vector for doctor {doctor_id}: {type(e).__name__}")
        _update_sync_status(doctor_id, "failed")
        return False


def delete_doctor_vector(doctor_id: str) -> bool:
    """Deletes doctor vector from Pinecone and updates Supabase sync status."""
    logger.info(f"[VECTOR_SYNC] Deleting vector for doctor {doctor_id}")
    try:
        _delete_vector_from_pinecone(doctor_id)
        _update_sync_status(doctor_id, "synced")
        return True
    except Exception as e:
        logger.error(f"[VECTOR_SYNC] Failed deleting vector for doctor {doctor_id}: {type(e).__name__}")
        _update_sync_status(doctor_id, "failed")
        return False


def retry_unsynced() -> int:
    """Syncs every doctor left pending or failed, and returns how many were tried."""
    client = get_supabase_admin_client()
    if not client:
        return 0

    rows = (
        client.table("doctor_profiles").select("id").in_("sync_status", ["pending", "failed"]).execute()
    )
    doctor_ids = [str(row["id"]) for row in rows.data or []]
    for doctor_id in doctor_ids:
        sync_doctor_vector(doctor_id)
    return len(doctor_ids)
