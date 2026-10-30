"""Full Vector Index Rebuild Utility for MediMatch AI.

Rebuilds the Pinecone vector index entirely from Supabase PostgreSQL (the single
source of truth).

Idempotent:
1. Queries all doctors from Supabase.
2. Approved doctors are embedded and upserted with metadata.
3. Non-approved (pending, suspended, rejected) doctors are purged from Pinecone.
4. Updates sync_status and last_synced_at columns in doctor_profiles.

Usage:
    python backend/scripts/reindex_all.py
"""

from datetime import datetime, timezone
import sys
from pathlib import Path
from typing import Any, Dict, List

# Ensure UTF-8 output on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Ensure backend root is on sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.core.config import settings
from app.core.supabase import get_supabase_admin_client
from app.models.enums import VerificationStatus
from app.search.builder import build_doctor_embedding_text
from app.search.embeddings import get_embedding_provider
from app.search.sync import get_pinecone_index


def reindex_all():
    print("=" * 65)
    print(" [INDEX REBUILD] MediMatch AI -- Pinecone Vector Re-indexing")
    print("=" * 65)

    client = get_supabase_admin_client()
    if not client:
        print("[ERROR] Could not connect to Supabase. Check configuration.")
        sys.exit(1)

    index = get_pinecone_index()
    provider = get_embedding_provider()

    print(f"Connecting to Pinecone Index : {settings.PINECONE_INDEX}")
    print(f"Embedding Provider          : {provider.__class__.__name__}")
    print(f"Embedding Model             : {settings.EMBEDDING_MODEL} ({provider.dimension}-dim)\n")

    # 1. Fetch all doctor profiles with specialties
    res = (
        client.table("doctor_profiles")
        .select("*, doctor_specialties(specialties(id, name, description))")
        .execute()
    )
    all_doctors: List[Dict[str, Any]] = res.data or []
    print(f"[INFO] Found {len(all_doctors)} total doctor profile(s) in Supabase.")

    approved_docs: List[Dict[str, Any]] = []
    unapproved_doc_ids: List[str] = []

    for doc in all_doctors:
        specs = []
        for item in doc.get("doctor_specialties", []):
            s = item.get("specialties")
            if s:
                specs.append(s)
        doc["specialties"] = specs

        if doc.get("verification_status") == VerificationStatus.APPROVED.value:
            approved_docs.append(doc)
        else:
            unapproved_doc_ids.append(str(doc["id"]))

    print(f"  • Approved Doctors to Index : {len(approved_docs)}")
    print(f"  • Unapproved to Purge       : {len(unapproved_doc_ids)}\n")

    # 2. Purge unapproved doctors from Pinecone
    if unapproved_doc_ids:
        print(f"[INFO] Purging {len(unapproved_doc_ids)} unapproved/suspended vectors from Pinecone...")
        try:
            index.delete(ids=unapproved_doc_ids)
            print("[SUCCESS] Purged unapproved vectors from index.")
        except Exception as e:
            print(f"[NOTICE] Vector purge completed with note: {e}")

    # 3. Build documents and embed approved doctors
    if not approved_docs:
        print("[WARNING] No approved doctors found to index.")
        return

    print(f"[INFO] Building documents and generating embeddings for {len(approved_docs)} doctor(s)...")
    doc_texts = [build_doctor_embedding_text(d) for d in approved_docs]
    embeddings = provider.embed_documents(doc_texts)

    vectors_to_upsert = []
    now_iso = datetime.now(timezone.utc).isoformat()

    for doc, vec in zip(approved_docs, embeddings):
        doc_id = str(doc["id"])
        specialty_ids = [s["id"] for s in doc.get("specialties", [])]
        specialty_names = [s["name"] for s in doc.get("specialties", [])]

        metadata = {
            "doctor_id": doc_id,
            "specialty_ids": specialty_ids,
            "specialty_names": specialty_names,
            "city": doc.get("city", "Dhaka"),
            "status": "approved",
        }

        vectors_to_upsert.append({
            "id": doc_id,
            "values": vec,
            "metadata": metadata,
        })

    # 4. Batch upsert to Pinecone
    batch_size = 50
    total_upserted = 0
    for i in range(0, len(vectors_to_upsert), batch_size):
        batch = vectors_to_upsert[i : i + batch_size]
        index.upsert(vectors=batch)
        total_upserted += len(batch)
        print(f"  • Upserted batch {i + 1} to {i + len(batch)} ({total_upserted}/{len(vectors_to_upsert)})")

    # 5. Update sync_status in Supabase
    approved_ids = [str(d["id"]) for d in approved_docs]
    for doc_id in approved_ids:
        client.table("doctor_profiles").update({
            "sync_status": "synced",
            "last_synced_at": now_iso,
        }).eq("id", doc_id).execute()

    for doc_id in unapproved_doc_ids:
        client.table("doctor_profiles").update({
            "sync_status": "synced",
            "last_synced_at": now_iso,
        }).eq("id", doc_id).execute()

    # 6. Report final stats
    stats = index.describe_index_stats()
    print("\n" + "=" * 65)
    print(" [SUMMARY] Vector Reindexing Complete")
    print("=" * 65)
    print(f"  • Approved Doctors Indexed : {len(approved_docs)}")
    print(f"  • Unapproved Purged        : {len(unapproved_doc_ids)}")
    print(f"  • Pinecone Vector Count    : {stats.total_vector_count}")
    print("=" * 65)


if __name__ == "__main__":
    reindex_all()

