"""Doctor Lifecycle Event Hooks.

These functions are invoked upon doctor profile status transitions.
Each one queues a Pinecone sync. Stale vectors are harmless in the meantime, because every search
result is checked against Postgres before it is returned.
"""

import logging
from typing import Any, Dict, List, Optional
from app.search.sync import delete_doctor_vector, run_in_background, sync_doctor_vector

logger = logging.getLogger("medimatch.doctor_events")


def on_doctor_approved(doctor_id: str, admin_id: str, metadata: Optional[Dict[str, Any]] = None) -> None:
    """An administrator approved a doctor, so their vector is built."""
    logger.info(f"[DOCTOR_EVENT] on_doctor_approved: doctor_id={doctor_id}")
    run_in_background(sync_doctor_vector, doctor_id)


def on_doctor_updated(doctor_id: str, updated_fields: List[str], metadata: Optional[Dict[str, Any]] = None) -> None:
    """A doctor changed material details. A profile back in review loses its vector until approved."""
    logger.info(f"[DOCTOR_EVENT] on_doctor_updated: doctor_id={doctor_id}, fields={updated_fields}")
    run_in_background(sync_doctor_vector, doctor_id)


def on_doctor_suspended(doctor_id: str, admin_id: str, reason: str, metadata: Optional[Dict[str, Any]] = None) -> None:
    """An administrator suspended a doctor, so their vector is removed."""
    logger.info(f"[DOCTOR_EVENT] on_doctor_suspended: doctor_id={doctor_id}")
    run_in_background(delete_doctor_vector, doctor_id)


def on_doctor_rejected(doctor_id: str, admin_id: str, reason: str, metadata: Optional[Dict[str, Any]] = None) -> None:
    """An administrator rejected a doctor, so any vector is removed."""
    logger.info(f"[DOCTOR_EVENT] on_doctor_rejected: doctor_id={doctor_id}")
    run_in_background(delete_doctor_vector, doctor_id)
