"""Pinecone Index Setup & Verification Script for MediMatch AI.

Ensures the vector index defined by PINECONE_INDEX exists, has the correct
dimension (1024 for llama-text-embed-v2) and cosine similarity metric.

Usage:
    python backend/scripts/setup_pinecone_index.py
"""

import sys
from pathlib import Path

# Ensure backend root is on sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from pinecone import Pinecone, ServerlessSpec
from app.core.config import settings


def setup_pinecone_index():
    print("=" * 65)
    print(" [PINECONE] MediMatch AI -- Pinecone Index Setup & Verification")
    print("=" * 65)

    if not settings.PINECONE_API_KEY:
        print("[ERROR] PINECONE_API_KEY is not configured in .env file.")
        sys.exit(1)

    pc = Pinecone(api_key=settings.PINECONE_API_KEY)
    index_name = settings.PINECONE_INDEX
    target_dim = settings.EMBEDDING_DIMENSION

    print(f"Target Index Name : {index_name}")
    print(f"Target Dimension  : {target_dim}")
    print(f"Target Metric     : cosine\n")

    existing_indexes = [idx.name for idx in pc.list_indexes()]

    if index_name not in existing_indexes:
        print(f"[INFO] Index '{index_name}' does not exist. Creating serverless index...")
        try:
            pc.create_index(
                name=index_name,
                dimension=target_dim,
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-east-1"),
            )
            print(f"[SUCCESS] Index '{index_name}' created successfully!")
        except Exception as e:
            print(f"[ERROR] Failed to create index '{index_name}': {e}")
            sys.exit(1)
    else:
        print(f"[INFO] Index '{index_name}' already exists.")

    # Describe and verify parameters
    try:
        desc = pc.describe_index(index_name)
        print("\nIndex Details:")
        print(f"  • Status    : {desc.status.get('state', 'Ready') if isinstance(desc.status, dict) else desc.status}")
        print(f"  • Host      : {desc.host}")
        print(f"  • Dimension : {desc.dimension}")
        print(f"  • Metric    : {desc.metric}")

        if desc.dimension != target_dim:
            print(
                f"\n[WARNING] Index dimension ({desc.dimension}) differs from configured target ({target_dim})!"
            )
        else:
            print(f"\n[SUCCESS] Index dimension matches embedding model ({target_dim}). Ready for vector search!")

        # Check vector stats
        idx = pc.Index(index_name)
        stats = idx.describe_index_stats()
        print(f"  • Total Vectors Indexed: {stats.total_vector_count}")

    except Exception as e:
        print(f"[ERROR] Could not fetch index details: {e}")
        sys.exit(1)


if __name__ == "__main__":
    setup_pinecone_index()
