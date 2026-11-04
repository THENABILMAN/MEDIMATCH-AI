"""Vector sync and ranking rules found by the audit."""

import threading
import uuid
from unittest.mock import MagicMock, create_autospec

import psycopg2
import pytest
from conftest import STACK
from pinecone.db_data import _Index

from app.core.config import Settings, settings
from app.search import recommend as recommend_module
from app.search import sync as sync_module
from app.search.builder import build_doctor_embedding_text
from app.search.embeddings import (
    FakeEmbeddingProvider,
    get_embedding_provider,
    set_embedding_provider,
)
from app.search.recommend import _calculate_score, recommend_doctors
from app.search.sync import set_pinecone_index_client, sync_doctor_vector
from app.services import doctor_events

APPROVED_NEURO = "d2000000-0000-0000-0000-000000000001"
SUSPENDED = "d2000000-0000-0000-0000-000000000009"
NEUROLOGY_ID = "11111111-0000-0000-0000-000000000001"


def sql(query: str, params: tuple = ()):
    conn = psycopg2.connect(STACK["DB_URL"])
    try:
        with conn, conn.cursor() as cur:
            cur.execute(query, params)
            return cur.fetchall() if cur.description else None
    finally:
        conn.close()


def vector_result(*pairs):
    return MagicMock(matches=[MagicMock(id=doctor, score=score) for doctor, score in pairs])


@pytest.fixture(autouse=True)
def search_doubles():
    set_embedding_provider(FakeEmbeddingProvider(dimension=1024))
    index = MagicMock()
    index.query = MagicMock(return_value=vector_result((APPROVED_NEURO, 0.9)))
    set_pinecone_index_client(index)
    yield index
    set_embedding_provider(None)
    set_pinecone_index_client(None)


def criteria(**overrides):
    base = {"candidate_specialties": ["Neurology"], "city": "Dhaka", "keywords": ["headache"]}
    return {**base, **overrides}


def test_a_null_specialty_description_does_not_break_indexing():
    text = build_doctor_embedding_text(
        {"specialties": [{"id": "s", "name": "Neurology", "description": None}], "city": "Dhaka"}
    )
    assert "Neurology" in text


def test_contact_details_in_a_bio_never_reach_the_embedding_provider():
    text = build_doctor_embedding_text(
        {
            "bio": "Neurologist. Call 01712345678 or mail doc@clinic.com. My name is Rahim Uddin.",
            "clinic_name": "Square Hospital, 01812345678",
            "city": "Dhaka",
        }
    )
    assert "01712345678" not in text
    assert "doc@clinic.com" not in text
    assert "Rahim" not in text
    assert "01812345678" not in text
    assert "Neurologist" in text


def test_names_and_fees_stay_out_of_embedded_text():
    text = build_doctor_embedding_text(
        {
            "full_name": "Dr. Secret",
            "consultation_fee": 1500,
            "phone": "01712345678",
            "city": "Dhaka",
        }
    )
    assert "Secret" not in text and "1500" not in text and "01712345678" not in text


def test_failed_sync_does_not_claim_it_synced(search_doubles):
    search_doubles.upsert.side_effect = RuntimeError("pinecone down")
    sql("UPDATE public.doctor_profiles SET last_synced_at = NULL WHERE id = %s", (APPROVED_NEURO,))

    assert sync_doctor_vector(APPROVED_NEURO) is False

    status, synced_at = sql(
        "SELECT sync_status, last_synced_at FROM public.doctor_profiles WHERE id = %s",
        (APPROVED_NEURO,),
    )[0]
    assert status == "failed"
    assert synced_at is None


def test_successful_sync_records_the_time(search_doubles):
    assert sync_doctor_vector(APPROVED_NEURO) is True
    status, synced_at = sql(
        "SELECT sync_status, last_synced_at FROM public.doctor_profiles WHERE id = %s",
        (APPROVED_NEURO,),
    )[0]
    assert status == "synced" and synced_at is not None


def test_retry_picks_up_failed_doctors(search_doubles):
    sql("UPDATE public.doctor_profiles SET sync_status = 'failed' WHERE id = %s", (APPROVED_NEURO,))
    assert sync_module.retry_unsynced() >= 1
    status = sql("SELECT sync_status FROM public.doctor_profiles WHERE id = %s", (APPROVED_NEURO,))[
        0
    ][0]
    assert status == "synced"


def test_approval_returns_before_a_slow_vector_sync(monkeypatch):
    monkeypatch.setattr(settings, "SYNC_IN_BACKGROUND", True)
    release = threading.Event()
    finished = threading.Event()

    def slow_sync(_doctor_id):
        release.wait(5)
        finished.set()

    monkeypatch.setattr(doctor_events, "sync_doctor_vector", slow_sync)
    doctor_events.on_doctor_approved(APPROVED_NEURO, "admin")
    assert not finished.is_set()
    release.set()
    assert finished.wait(5)


def test_a_failing_background_sync_is_recorded(monkeypatch, search_doubles):
    monkeypatch.setattr(settings, "SYNC_IN_BACKGROUND", True)
    search_doubles.delete.side_effect = RuntimeError("pinecone down")
    sql("UPDATE public.doctor_profiles SET sync_status = 'synced' WHERE id = %s", (SUSPENDED,))

    doctor_events.on_doctor_suspended(SUSPENDED, "admin", "reason")
    sync_module.wait_for_background_syncs()

    assert (
        sql("SELECT sync_status FROM public.doctor_profiles WHERE id = %s", (SUSPENDED,))[0][0]
        == "failed"
    )


def test_editing_a_specialty_reindexes_its_doctors(client, admin_token, search_doubles):
    res = client.put(
        f"/admin/specialties/{NEUROLOGY_ID}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"description": f"Brain and nerves {uuid.uuid4().hex[:6]}"},
    )
    assert res.status_code == 200
    assert search_doubles.upsert.called


def test_vector_search_asks_for_approved_doctors_only(search_doubles):
    recommend_doctors(criteria())
    kwargs = search_doubles.query.call_args.kwargs
    assert kwargs["filter"] == {"status": {"$eq": "approved"}}


def test_enough_candidates_are_fetched_for_large_requests(search_doubles):
    recommend_doctors(criteria(), top_k=20)
    assert search_doubles.query.call_args.kwargs["top_k"] >= 20


def test_a_stale_suspended_vector_stays_out_even_as_the_top_match(search_doubles):
    search_doubles.query.return_value = vector_result((SUSPENDED, 0.99), (APPROVED_NEURO, 0.5))
    ids = [r.id for r in recommend_doctors(criteria()).recommendations]
    assert SUSPENDED not in ids
    assert APPROVED_NEURO in ids


def test_few_vector_matches_are_topped_up_not_thrown_away(search_doubles):
    res = recommend_doctors(criteria())
    ids = [r.id for r in res.recommendations]
    assert ids[0] == APPROVED_NEURO
    assert len(ids) >= 2
    assert res.retrieval_mode == "hybrid"
    assert len(ids) == len(set(ids))


def test_missing_fee_does_not_outrank_a_real_fee():
    args = {
        "vector_sim": 0.5,
        "doctor_specialties": ["Neurology"],
        "candidate_specialties": ["Neurology"],
        "years_experience": 10,
        "max_fee": None,
        "available_slots_count": 5,
    }
    assert _calculate_score(fee=0.0, **args) <= _calculate_score(fee=500.0, **args)


def test_sql_fallback_is_bounded(monkeypatch):
    monkeypatch.setattr(recommend_module, "MAX_SQL_CANDIDATES", 1)
    assert (
        len(recommend_module._sql_fallback_search(["General Medicine"], "Bangladesh", limit=5)) <= 1
    )


def test_mistyped_provider_fails_instead_of_using_fake_vectors(monkeypatch):
    set_embedding_provider(None)
    monkeypatch.setattr(settings, "EMBEDDING_PROVIDER", "pincone")
    with pytest.raises(ValueError):
        get_embedding_provider()


def test_fake_embeddings_are_refused_in_production(monkeypatch):
    set_embedding_provider(None)
    monkeypatch.setattr(settings, "EMBEDDING_PROVIDER", "fake")
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    with pytest.raises(ValueError):
        get_embedding_provider()


def test_ranking_weights_must_add_up():
    with pytest.raises(ValueError):
        Settings(WEIGHT_VECTOR=0.9, _env_file=None)


def test_calls_match_the_real_pinecone_client():
    """A plain mock accepts any argument, which once sent every real search to the SQL fallback."""
    index = create_autospec(_Index, instance=True)
    index.query.return_value = vector_result((APPROVED_NEURO, 0.9))
    index.upsert.return_value = None
    index.delete.return_value = None
    set_pinecone_index_client(index)

    assert recommend_doctors(criteria()).retrieval_mode == "hybrid"
    assert sync_doctor_vector(APPROVED_NEURO) is True
    assert sync_module.delete_doctor_vector(SUSPENDED) is True
