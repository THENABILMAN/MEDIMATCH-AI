"""Doctor Lifecycle Event Hooks.

These functions are invoked upon doctor profile status transitions.
In Phase 2, they log structured telemetry.
In Phase 4, they will trigger Pinecone vector embedding generation and index synchronization.
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("medimatch.doctor_events")


def on_doctor_approved(doctor_id: str, admin_id: str, metadata: Optional[Dict[str, Any]] = None) -> None:
    """Hook invoked when an administrator approves a doctor profile.
    
    Prepares the doctor's profile and specialties for vector indexing in Pinecone (Phase 4).
    """
    logger.info(
        f"[DOCTOR_EVENT] on_doctor_approved: doctor_id={doctor_id}, approved_by={admin_id}, metadata={metadata}"
    )


def on_doctor_updated(doctor_id: str, updated_fields: List[str], metadata: Optional[Dict[str, Any]] = None) -> None:
    """Hook invoked when a doctor updates material profile details.
    
    Signals that vector embeddings should be invalidated or recomputed once re-approved (Phase 4).
    """
    logger.info(
        f"[DOCTOR_EVENT] on_doctor_updated: doctor_id={doctor_id}, fields={updated_fields}, metadata={metadata}"
    )


def on_doctor_suspended(doctor_id: str, admin_id: str, reason: str, metadata: Optional[Dict[str, Any]] = None) -> None:
    """Hook invoked when an administrator suspends a doctor profile.
    
    Signals that vector embeddings for this doctor must be removed from the active Pinecone index (Phase 4).
    """
    logger.info(
        f"[DOCTOR_EVENT] on_doctor_suspended: doctor_id={doctor_id}, suspended_by={admin_id}, reason='{reason}', metadata={metadata}"
    )

