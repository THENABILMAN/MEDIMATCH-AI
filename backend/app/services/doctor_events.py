"""Doctor Lifecycle Event Hooks.

These functions are invoked upon doctor profile status transitions.
In Phase 2, they log structured telemetry.
In Phase 4, they will trigger Pinecone vector embedding generation and index synchronization.
"""

import logging
from typing import Any, Dict, List, Optional
from app.search.sync import delete_doctor_vector, sync_doctor_vector

logger = logging.getLogger("medimatch.doctor_events")


def on_doctor_approved(doctor_id: str, admin_id: str, metadata: Optional[Dict[str, Any]] = None) -> None:
    """Hook invoked when an administrator approves a doctor profile.
    
    Triggers Pinecone vector embedding generation and upsert.
    """
    logger.info(
        f"[DOCTOR_EVENT] on_doctor_approved: doctor_id={doctor_id}, approved_by={admin_id}, metadata={metadata}"
    )
    try:
        sync_doctor_vector(doctor_id)
    except Exception as e:
        logger.error(f"[DOCTOR_EVENT] Failed syncing vector on approval for doctor {doctor_id}: {e}")


def on_doctor_updated(doctor_id: str, updated_fields: List[str], metadata: Optional[Dict[str, Any]] = None) -> None:
    """Hook invoked when a doctor updates material profile details.
    
    If profile is reset to pending, removes vector from Pinecone until re-approved.
    """
    logger.info(
        f"[DOCTOR_EVENT] on_doctor_updated: doctor_id={doctor_id}, fields={updated_fields}, metadata={metadata}"
    )
    try:
        sync_doctor_vector(doctor_id)
    except Exception as e:
        logger.error(f"[DOCTOR_EVENT] Failed syncing vector on update for doctor {doctor_id}: {e}")


def on_doctor_suspended(doctor_id: str, admin_id: str, reason: str, metadata: Optional[Dict[str, Any]] = None) -> None:
    """Hook invoked when an administrator suspends a doctor profile.
    
    Immediately deletes vector embeddings for this doctor from Pinecone.
    """
    logger.info(
        f"[DOCTOR_EVENT] on_doctor_suspended: doctor_id={doctor_id}, suspended_by={admin_id}, reason='{reason}', metadata={metadata}"
    )
    try:
        delete_doctor_vector(doctor_id)
    except Exception as e:
        logger.error(f"[DOCTOR_EVENT] Failed deleting vector on suspension for doctor {doctor_id}: {e}")


def on_doctor_rejected(doctor_id: str, admin_id: str, reason: str, metadata: Optional[Dict[str, Any]] = None) -> None:
    """Hook invoked when an administrator rejects a doctor profile.
    
    Deletes vector embeddings for this doctor from Pinecone if present.
    """
    logger.info(
        f"[DOCTOR_EVENT] on_doctor_rejected: doctor_id={doctor_id}, rejected_by={admin_id}, reason='{reason}', metadata={metadata}"
    )
    try:
        delete_doctor_vector(doctor_id)
    except Exception as e:
        logger.error(f"[DOCTOR_EVENT] Failed deleting vector on rejection for doctor {doctor_id}: {e}")


