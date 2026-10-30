"""Integration & Safety Tests for Doctor Recommendation Engine.

Verifies:
1. Stale Pinecone vectors for unapproved, suspended, or rejected doctors are strictly discarded.
2. Doctors without future availability slots are excluded from recommendations.
3. Pinecone outages gracefully fall back to authoritative SQL search without failing patient requests.
4. Consultation budget (max_fee) is strictly respected.
5. Direct /recommendations and chat integration return properly ranked recommendations.
"""

import uuid
from unittest.mock import MagicMock

import pytest
from conftest import create_mock_jwt
from fastapi import status
from fastapi.testclient import TestClient

from app.ai.llm import LLMClient, set_llm_client
from app.ai.state import ConversationIntent, ExtractedSymptoms
from app.models.enums import UserRole
from app.search.embeddings import FakeEmbeddingProvider, set_embedding_provider
from app.search.recommend import recommend_doctors
from app.search.sync import set_pinecone_index_client


@pytest.fixture(autouse=True)
def setup_test_search():
    """Activates FakeEmbeddingProvider and mocked Pinecone by default in tests."""
    provider = FakeEmbeddingProvider(dimension=1024)
    set_embedding_provider(provider)

    mock_index = MagicMock()
    # Default mock matches seeded approved doctors
    mock_index.query = MagicMock(
        return_value=MagicMock(
            matches=[
                MagicMock(id="d2000000-0000-0000-0000-000000000001", score=0.88),  # Dr. Kazi Ahmed (Approved Neuro)
                MagicMock(id="d2000000-0000-0000-0000-000000000006", score=0.82),  # Dr. Rubina Akhter (Approved Neuro)
                MagicMock(id="d2000000-0000-0000-0000-000000000003", score=0.74),  # Dr. Mahmudul Hasan (Approved Gen)
            ]
        )
    )
    set_pinecone_index_client(mock_index)

    yield mock_index

    set_embedding_provider(None)
    set_pinecone_index_client(None)


def test_stale_unapproved_or_suspended_vector_never_recommended():
    """NON-NEGOTIABLE RULE: Supabase is the single source of truth.

    Even if Pinecone returns a stale vector for a suspended or rejected doctor,
    the recommendation engine MUST reject them upon authoritative DB verification.
    """
    mock_index = MagicMock()
    # Mock Pinecone returning suspended and rejected doctors with high vector scores!
    mock_index.query = MagicMock(
        return_value=MagicMock(
            matches=[
                MagicMock(id="d2000000-0000-0000-0000-000000000009", score=0.99),  # Suspended doctor!
                MagicMock(id="d2000000-0000-0000-0000-000000000010", score=0.98),  # Rejected doctor!
                MagicMock(id="d2000000-0000-0000-0000-000000000001", score=0.85),  # Approved doctor
            ]
        )
    )
    set_pinecone_index_client(mock_index)

    criteria = {
        "candidate_specialties": ["Neurology"],
        "city": "Dhaka",
        "keywords": ["headache"],
    }
    res = recommend_doctors(criteria, top_k=5)

    rec_ids = [d.id for d in res.recommendations]

    # Suspended and rejected doctors MUST NEVER appear in recommendations
    assert "d2000000-0000-0000-0000-000000000009" not in rec_ids
    assert "d2000000-0000-0000-0000-000000000010" not in rec_ids

    # The approved doctor should be present
    assert "d2000000-0000-0000-0000-000000000001" in rec_ids


def test_doctor_with_no_future_availability_slots_excluded():
    """Doctors who do not have any future unbooked slots are not bookable

    and must be excluded from recommendations.
    """
    non_existent_uuid = str(uuid.uuid4())
    mock_index = MagicMock()
    mock_index.query = MagicMock(
        return_value=MagicMock(
            matches=[
                MagicMock(id="non-uuid-string-from-index", score=0.99),
                MagicMock(id=non_existent_uuid, score=0.95),
                MagicMock(id="d2000000-0000-0000-0000-000000000001", score=0.85),
            ]
        )
    )
    set_pinecone_index_client(mock_index)

    criteria = {
        "candidate_specialties": ["Neurology"],
        "city": "Dhaka",
        "keywords": ["headache"],
    }
    res = recommend_doctors(criteria, top_k=5)

    assert "non-uuid-string-from-index" not in [d.id for d in res.recommendations]
    assert non_existent_uuid not in [d.id for d in res.recommendations]
    for d in res.recommendations:
        assert d.available_slots_count > 0
        assert d.soonest_slot is not None


def test_pinecone_failure_triggers_graceful_sql_fallback():
    """If Pinecone service is unavailable or throws network errors,

    recommend_doctors catches the failure and seamlessly returns SQL fallback results.
    """
    mock_index = MagicMock()
    mock_index.query = MagicMock(side_effect=RuntimeError("Pinecone connection timed out"))
    set_pinecone_index_client(mock_index)

    criteria = {
        "candidate_specialties": ["Neurology"],
        "city": "Dhaka",
        "keywords": ["headache"],
    }
    res = recommend_doctors(criteria, top_k=3)

    assert res.retrieval_mode == "sql_fallback"
    assert len(res.recommendations) >= 1
    # Check that returned doctors are valid and approved
    for d in res.recommendations:
        assert d.match_score > 0
        assert d.available_slots_count > 0
        assert "Specializes in" in d.match_explanation


def test_budget_max_fee_filter_enforced():
    """Consultation fee upper bound (max_fee) must be strictly enforced."""
    criteria = {
        "candidate_specialties": ["Cardiology"],
        "city": "Dhaka",
        "max_fee": 1300.0,
        "keywords": ["chest tightness"],
    }
    res = recommend_doctors(criteria, top_k=5)

    for doc in res.recommendations:
        assert doc.consultation_fee <= 1300.0


def test_direct_recommendations_api_endpoints(client: TestClient):
    """POST /recommendations and POST /api/v1/recommendations respond with recommendations."""
    payload = {
        "candidate_specialties": ["Neurology"],
        "city": "Dhaka",
        "keywords": ["migraine headache"],
        "top_k": 3,
    }

    # Test top-level route
    res1 = client.post("/recommendations", json=payload)
    assert res1.status_code == status.HTTP_200_OK
    data1 = res1.json()
    assert "recommendations" in data1
    assert data1["total_found"] >= 1
    assert len(data1["recommendations"]) <= 3

    # Test /api/v1/recommendations
    res2 = client.post("/api/v1/recommendations", json=payload)
    assert res2.status_code == status.HTTP_200_OK
    data2 = res2.json()
    assert len(data2["recommendations"]) >= 1


def test_chat_completion_populates_recommendations(client: TestClient):
    """When chat consultation finishes symptom extraction, the response contains

    both the structured search_criteria and the top recommended doctors list.
    """
    patient_id = "a0000000-0000-0000-0000-000000000002"
    token = create_mock_jwt(patient_id, "patient@medimatch.test", UserRole.PATIENT, "Demo Patient")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create conversation
    create_res = client.post("/chat/conversations", headers=headers, json={"title": "Neuro Consultation"})
    assert create_res.status_code == status.HTTP_201_CREATED
    conv_id = create_res.json()["id"]

    # 2. Configure deterministic mock LLM
    class MockNeuroLLM(LLMClient):
        def generate_structured(self, messages, response_model, system_prompt=None):
            if response_model is ConversationIntent:
                return ConversationIntent(intent="symptom_update")
            return ExtractedSymptoms(
                symptoms=["severe migraine", "throbbing head pain"],
                duration="3 days",
                severity="moderate",
                location="Dhaka",
                candidate_specialty_names=["Neurology"],
            )

    set_llm_client(MockNeuroLLM(api_key="mock", model="mock"))

    # 3. Send message that completes extraction
    msg_res = client.post(
        f"/chat/conversations/{conv_id}/messages",
        headers=headers,
        json={"content": "I have had a severe throbbing migraine for 3 days in Dhaka."},
    )
    assert msg_res.status_code == status.HTTP_200_OK
    data = msg_res.json()

    assert data["current_step"] == "completed"
    assert data["search_criteria"] is not None

    # Recommendations must be returned in the response
    assert "recommendations" in data
    assert data["recommendations"] is not None
    assert len(data["recommendations"]) >= 1

    top_doc = data["recommendations"][0]
    assert "full_name" in top_doc
    assert "match_score" in top_doc
    assert top_doc["available_slots_count"] > 0

    # Assistant reply must include doctor presentation
    assert "Recommended Specialists" in data["assistant_reply"]

    # Reset LLM
    set_llm_client(LLMClient())
