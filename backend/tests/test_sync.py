"""Unit Tests for Vector Synchronization Pipeline & Lifecycle Hooks.

Verifies:
1. FakeEmbeddingProvider produces deterministic, normalized unit vectors without network calls.
2. Doctor document builder includes clinical details and strictly omits PII and fees.
3. Doctor approval creates/upserts vector to Pinecone with correct metadata.
4. Non-approved (pending, suspended, rejected) doctors have their vectors deleted from Pinecone.
5. Lifecycle hooks trigger vector synchronization.
"""

from unittest.mock import MagicMock
import pytest
from app.search.builder import build_doctor_embedding_text
from app.search.embeddings import FakeEmbeddingProvider, set_embedding_provider
from app.search.sync import (
    delete_doctor_vector,
    set_pinecone_index_client,
    sync_doctor_vector,
)
from app.services.doctor_events import (
    on_doctor_approved,
    on_doctor_rejected,
    on_doctor_suspended,
    on_doctor_updated,
)


@pytest.fixture(autouse=True)
def setup_fake_search():
    """Ensure FakeEmbeddingProvider and mocked Pinecone are active during tests."""
    fake_provider = FakeEmbeddingProvider(dimension=1024)
    set_embedding_provider(fake_provider)

    mock_index = MagicMock()
    mock_index.upsert = MagicMock(return_value={"upserted_count": 1})
    mock_index.delete = MagicMock(return_value={})
    set_pinecone_index_client(mock_index)

    yield mock_index

    # Reset
    set_embedding_provider(None)
    set_pinecone_index_client(None)


def test_fake_embedding_provider_dimension_and_determinism():
    """Fake embedding provider must generate 1024-dim unit vectors consistently."""
    provider = FakeEmbeddingProvider(dimension=1024)
    assert provider.dimension == 1024

    v1 = provider.embed_query("headache specialist in Dhaka")
    v2 = provider.embed_query("headache specialist in Dhaka")
    v3 = provider.embed_query("cardiologist in Chittagong")

    assert len(v1) == 1024
    assert len(v2) == 1024
    assert len(v3) == 1024

    # Determinism: identical text yields identical vector
    assert v1 == v2

    # Different text yields different vector
    assert v1 != v3

    # Vector length (L2 norm) must be approximately 1.0 (unit vector)
    norm = sum(x * x for x in v1) ** 0.5
    assert abs(norm - 1.0) < 1e-4


def test_doctor_document_builder_omits_pii_and_fees():
    """Doctor document builder must include clinical fields and strictly omit PII and fees."""
    sample_doc = {
        "id": "doc-uuid-1234",
        "user_id": "user-uuid-5678",
        "full_name": "Dr. Highly Sensitive Name",
        "phone": "+8801712345678",
        "email": "doctor.secret@example.com",
        "consultation_fee": 1500.0,
        "bio": "Experienced clinical neurologist specializing in stroke and migraine therapy.",
        "qualifications": ["MBBS", "FCPS (Neurology)"],
        "years_experience": 14,
        "clinic_name": "United Hospital, Gulshan",
        "city": "Dhaka",
        "specialties": [
            {
                "name": "Neurology",
                "description": "Diagnosis and management of disorders of the brain and nerves.",
            }
        ],
    }

    doc_text = build_doctor_embedding_text(sample_doc)

    # Must contain clinical details
    assert "Neurology" in doc_text
    assert "stroke and migraine therapy" in doc_text
    assert "FCPS (Neurology)" in doc_text
    assert "United Hospital, Gulshan" in doc_text
    assert "Dhaka" in doc_text
    assert "14 years" in doc_text

    # CRITICAL SECURITY / PRIVACY CHECK: Must NEVER leak PII or fee!
    assert "Dr. Highly Sensitive Name" not in doc_text
    assert "+8801712345678" not in doc_text
    assert "doctor.secret@example.com" not in doc_text
    assert "1500" not in doc_text
    assert "doc-uuid-1234" not in doc_text
    assert "user-uuid-5678" not in doc_text


def test_sync_doctor_approved_upserts_to_pinecone(setup_fake_search):
    """Syncing an approved doctor embeds and upserts vector with metadata."""
    mock_index = setup_fake_search
    # Seeded approved doctor
    approved_id = "d2000000-0000-0000-0000-000000000001"

    success = sync_doctor_vector(approved_id)
    assert success is True
    assert mock_index.upsert.called

    call_args = mock_index.upsert.call_args[1]
    vectors = call_args["vectors"]
    assert len(vectors) == 1
    assert vectors[0]["id"] == approved_id
    assert len(vectors[0]["values"]) == 1024

    metadata = vectors[0]["metadata"]
    assert metadata["status"] == "approved"
    assert metadata["city"] == "Dhaka"
    assert "Neurology" in metadata["specialty_names"]


def test_sync_doctor_unapproved_deletes_from_pinecone(setup_fake_search):
    """Syncing a non-approved doctor purges vector from Pinecone."""
    mock_index = setup_fake_search
    # Seeded pending doctor
    pending_id = "d2000000-0000-0000-0000-000000000007"

    success = sync_doctor_vector(pending_id)
    assert success is True
    assert mock_index.delete.called
    mock_index.delete.assert_called_with(ids=[pending_id])


def test_doctor_events_lifecycle_triggers_vector_sync(setup_fake_search):
    """Lifecycle event hooks trigger appropriate sync and delete operations."""
    mock_index = setup_fake_search
    approved_id = "d2000000-0000-0000-0000-000000000001"
    suspended_id = "d2000000-0000-0000-0000-000000000009"

    # 1. Approval triggers upsert
    on_doctor_approved(doctor_id=approved_id, admin_id="admin-1")
    assert mock_index.upsert.called

    # 2. Suspension triggers delete
    mock_index.delete.reset_mock()
    on_doctor_suspended(doctor_id=suspended_id, admin_id="admin-1", reason="Outdated license")
    assert mock_index.delete.called
    mock_index.delete.assert_called_with(ids=[suspended_id])

    # 3. Rejection triggers delete
    mock_index.delete.reset_mock()
    on_doctor_rejected(doctor_id=suspended_id, admin_id="admin-1", reason="Incomplete docs")
    assert mock_index.delete.called
    mock_index.delete.assert_called_with(ids=[suspended_id])

