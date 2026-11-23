"""Vector Synchronization Pipeline for MediMatch AI.

Maintains bidirectional consistency between Supabase PostgreSQL (the single
source of truth) and the MongoDB vector index.

Ensures:
1. Only doctors with verification_status = 'approved' exist in MongoDB.
2. Unapproved, suspended, or rejected doctors have their vectors deleted immediately.
3. Doctor profiles update their sync_status and last_synced_at columns.
4. Transient network errors are automatically retried.
"""

import logging
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor, wait
from datetime import UTC, datetime
from typing import Any

from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.core.supabase import get_supabase_admin_client
from app.models.enums import VerificationStatus
from app.search.builder import build_doctor_embedding_text
from app.search.cities import normalize_city
from app.search.embeddings import get_embedding_provider
from app.search.vector_store import get_vector_store

logger = logging.getLogger("medimatch.search.sync")

# Provider calls are slow and retried, so they must not hold up an admin's request
_sync_pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="vector-sync")
_pending_syncs: set[Future] = set()


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


def vector_metadata(doc: dict[str, Any]) -> dict[str, Any]:
    """What MongoDB filters on."""
    specialties = doc.get("specialties", [])
    metadata: dict[str, Any] = {
        "doctor_id": str(doc["id"]),
        "specialty_ids": [str(s["id"]) for s in specialties],
        "specialty_names": [s["name"] for s in specialties],
        "status": "approved",
        "listing_source": doc.get("listing_source") or "registered",
    }
    city = normalize_city(doc.get("city"))
    if city:
        metadata["city"] = city
    return metadata


def _fetch_doctor_with_specialties(doctor_id: str) -> dict[str, Any] | None:
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

    updates: dict[str, Any] = {"sync_status": status}
    if status == "synced":
        updates["last_synced_at"] = datetime.now(UTC).isoformat()

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
def _upsert_vector(doctor_id: str, vector: list[float], metadata: dict[str, Any]) -> None:
    index = get_vector_store()
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
def _delete_vector(doctor_id: str) -> None:
    index = get_vector_store()
    index.delete(ids=[doctor_id])


def sync_doctor_vector(doctor_id: str) -> bool:
    """Synchronizes a doctor's vector with MongoDB based on Supabase record.

    If status is 'approved', generates embedding and upserts to MongoDB.
    If status is anything else ('pending', 'suspended', 'rejected'), deletes vector.
    """
    logger.info(f"[VECTOR_SYNC] Starting sync for doctor {doctor_id}")
    doc = _fetch_doctor_with_specialties(doctor_id)
    if not doc:
        logger.warning(f"[VECTOR_SYNC] Doctor {doctor_id} not found in Supabase. Deleting vector.")
        try:
            _delete_vector(doctor_id)
        except Exception:
            pass
        return False

    status = doc.get("verification_status")

    # Non-negotiable Rule: Only 'approved' doctors exist in MongoDB
    if status != VerificationStatus.APPROVED.value:
        logger.info(
            f"[VECTOR_SYNC] Doctor {doctor_id} status is '{status}' (not approved). Removing from MongoDB."
        )
        try:
            _delete_vector(doctor_id)
            _update_sync_status(doctor_id, "synced")
            return True
        except Exception as e:
            logger.error(
                f"[VECTOR_SYNC] Failed removing vector for doctor {doctor_id}: {type(e).__name__}"
            )
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
        metadata = vector_metadata(doc)

        _upsert_vector(doctor_id=doctor_id, vector=vector, metadata=metadata)
        _update_sync_status(doctor_id, "synced")
        logger.info(f"[VECTOR_SYNC] Successfully indexed doctor {doctor_id} in MongoDB")
        return True

    except Exception as e:
        logger.error(
            f"[VECTOR_SYNC] Error syncing vector for doctor {doctor_id}: {type(e).__name__}"
        )
        _update_sync_status(doctor_id, "failed")
        return False


def delete_doctor_vector(doctor_id: str) -> bool:
    """Deletes doctor vector from MongoDB and updates Supabase sync status."""
    logger.info(f"[VECTOR_SYNC] Deleting vector for doctor {doctor_id}")
    try:
        _delete_vector(doctor_id)
        _update_sync_status(doctor_id, "synced")
        return True
    except Exception as e:
        logger.error(
            f"[VECTOR_SYNC] Failed deleting vector for doctor {doctor_id}: {type(e).__name__}"
        )
        _update_sync_status(doctor_id, "failed")
        return False


def retry_unsynced() -> int:
    """Syncs every doctor left pending or failed, and returns how many were tried."""
    client = get_supabase_admin_client()
    if not client:
        return 0

    rows = (
        client.table("doctor_profiles")
        .select("id")
        .in_("sync_status", ["pending", "failed"])
        .execute()
    )
    doctor_ids = [str(row["id"]) for row in rows.data or []]
    for doctor_id in doctor_ids:
        sync_doctor_vector(doctor_id)
    return len(doctor_ids)


EMBED_BATCH = 64
STATUS_BATCH = 200


def _mark_synced(doctor_ids: list[str]) -> None:
    client = get_supabase_admin_client()
    if not client:
        return
    now = datetime.now(UTC).isoformat()
    for start in range(0, len(doctor_ids), STATUS_BATCH):
        chunk = doctor_ids[start : start + STATUS_BATCH]
        client.table("doctor_profiles").update(
            {"sync_status": "synced", "last_synced_at": now}
        ).in_("id", chunk).execute()


def index_doctors(
    doctors: list[dict[str, Any]], progress: Callable[[int, int], None] | None = None
) -> int:
    """Embeds and upserts approved doctors in batches, then marks them synced.

    Each doctor needs its "specialties" list. Returns how many were indexed.
    """
    approved = [
        d for d in doctors if d.get("verification_status") == VerificationStatus.APPROVED.value
    ]
    provider = get_embedding_provider()
    index = get_vector_store()
    done = 0
    for start in range(0, len(approved), EMBED_BATCH):
        batch = approved[start : start + EMBED_BATCH]
        texts = [build_doctor_embedding_text(d) for d in batch]
        vectors = provider.embed_documents(texts)
        records = [
            {"id": str(doc["id"]), "values": vector, "metadata": vector_metadata(doc)}
            for doc, vector in zip(batch, vectors, strict=True)
        ]
        index.upsert(vectors=records)
        _mark_synced([str(doc["id"]) for doc in batch])
        done += len(batch)
        if progress:
            progress(done, len(approved))
    return done
