"""Full Vector Index Rebuild Utility for MediMatch AI.

Rebuilds the MongoDB vector index entirely from Supabase PostgreSQL (the single
source of truth).

Idempotent:
1. Queries all doctors from Supabase.
2. Approved doctors are embedded and upserted with metadata.
3. Non-approved (pending, suspended, rejected) doctors are purged from MongoDB.
4. Updates sync_status and last_synced_at columns in doctor_profiles.

Usage:
    python backend/scripts/reindex_all.py
"""

import sys
from pathlib import Path
from typing import Any

# Ensure UTF-8 output on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Ensure backend root is on sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import argparse

from app.core.config import settings
from app.core.supabase import get_supabase_admin_client
from app.models.enums import VerificationStatus
from app.search.embeddings import get_embedding_provider
from app.search.sync import index_doctors, retry_unsynced
from app.search.vector_store import get_vector_store


def reindex_all():
    print("=" * 65)
    print(" [INDEX REBUILD] MediMatch AI -- MongoDB Vector Re-indexing")
    print("=" * 65)

    client = get_supabase_admin_client()
    if not client:
        print("[ERROR] Could not connect to Supabase. Check configuration.")
        sys.exit(1)

    index = get_vector_store()
    provider = get_embedding_provider()

    index.prepare()
    print(f"MongoDB collection          : {settings.MONGODB_DOCTORS}")
    print(f"Embedding Provider          : {provider.__class__.__name__}")
    print(f"Embedding Model             : {settings.EMBEDDING_MODEL} ({provider.dimension}-dim)\n")

    # 1. Fetch every doctor, a page at a time, because a request returns at most 1,000 rows
    all_doctors: list[dict[str, Any]] = []
    page = 1000
    while True:
        res = (
            client.table("doctor_profiles")
            .select("*, doctor_specialties(specialties(id, name, description))")
            .order("id")
            .range(len(all_doctors), len(all_doctors) + page - 1)
            .execute()
        )
        rows = res.data or []
        all_doctors += rows
        if len(rows) < page:
            break
    print(f"[INFO] Found {len(all_doctors)} total doctor profile(s) in Supabase.")

    approved_docs: list[dict[str, Any]] = []
    unapproved_doc_ids: list[str] = []
    for doc in all_doctors:
        doc["specialties"] = [
            item["specialties"]
            for item in doc.get("doctor_specialties", [])
            if item.get("specialties")
        ]
        if doc.get("verification_status") == VerificationStatus.APPROVED.value:
            approved_docs.append(doc)
        else:
            unapproved_doc_ids.append(str(doc["id"]))

    print(f"  • Approved Doctors to Index : {len(approved_docs)}")
    print(f"  • Unapproved to Purge       : {len(unapproved_doc_ids)}\n")

    # 2. Purge unapproved doctors from MongoDB
    for start in range(0, len(unapproved_doc_ids), 1000):
        index.delete(ids=unapproved_doc_ids[start : start + 1000])

    # 3. Embed and upsert approved doctors in batches
    if not approved_docs:
        print("[WARNING] No approved doctors found to index.")
        return
    index_doctors(
        approved_docs,
        progress=lambda done, total: print(f"  • Indexed {done}/{total}", flush=True),
    )

    # 6. Report final stats
    print("\n" + "=" * 65)
    print(" [SUMMARY] Vector Reindexing Complete")
    print("=" * 65)
    print(f"  • Approved Doctors Indexed : {len(approved_docs)}")
    print(f"  • Unapproved Purged        : {len(unapproved_doc_ids)}")
    print(f"  • MongoDB Vector Count     : {index.count()}")
    print("=" * 65)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Rebuild the vector index from Supabase")
    parser.add_argument(
        "--unsynced", action="store_true", help="Only retry pending or failed doctors"
    )
    if parser.parse_args().unsynced:
        print(f"[INFO] Retried {retry_unsynced()} doctor(s).")
    else:
        reindex_all()
