"""Doctors listed from a public directory, against local Supabase.

They have no account, are labelled unverified, cannot be booked online, and keep unknown facts
unknown. A missing city keeps them out of any search for a specific city.
"""

import uuid
from collections.abc import Iterator
from unittest.mock import MagicMock

import psycopg2
import pytest
from fastapi.testclient import TestClient
from psycopg2 import errors

from app.core.config import settings
from app.search.embeddings import FakeEmbeddingProvider, set_embedding_provider
from app.search.recommend import recommend_doctors
from app.search.vector_store import set_vector_store

ENT = "11111111-0000-0000-0000-000000000010"


def sql(query: str, params: tuple = ()) -> list[tuple]:
    with psycopg2.connect(settings.DATABASE_URL) as conn, conn.cursor() as cur:
        cur.execute(query, params)
        return cur.fetchall() if cur.description else []


def add_listing(name: str, city: str | None) -> str:
    """Inserted the way scripts/import_directory.py does, with unknown facts written as NULL."""
    doctor_id = str(uuid.uuid4())
    sql(
        """
        INSERT INTO public.doctor_profiles (
            id, listing_source, listed_name, source_url, verification_status, city,
            clinic_name, specialty_text, designation, qualifications,
            consultation_fee, years_experience
        ) VALUES (%s, 'directory', %s, %s, 'approved', %s, 'Example Hospital',
                  'ENT Specialist & Head Neck Surgeon', 'Consultant', ARRAY['MBBS', 'DLO'],
                  NULL, NULL)
        """,
        (doctor_id, name, f"https://directory.test/{doctor_id}/", city),
    )
    sql(
        "INSERT INTO public.doctor_specialties (doctor_id, specialty_id) VALUES (%s, %s)",
        (doctor_id, ENT),
    )
    return doctor_id


@pytest.fixture
def listings() -> Iterator[dict[str, str]]:
    made = {
        "sylhet": add_listing("Dr. Sylhet Listing", "Sylhet"),
        "chattogram": add_listing("Dr. Chattogram Listing", "Chattogram"),
        "nowhere": add_listing("Dr. Unknown City Listing", None),
    }
    yield made
    sql("DELETE FROM public.doctor_profiles WHERE id = ANY(%s::uuid[])", (list(made.values()),))


@pytest.fixture
def no_vectors() -> Iterator[MagicMock]:
    """MongoDB fails, so recommendations come from the database alone."""
    set_embedding_provider(FakeEmbeddingProvider(dimension=1024))
    index = MagicMock()
    index.query.side_effect = RuntimeError("down")
    set_vector_store(index)
    yield index
    set_embedding_provider(None)
    set_vector_store(None)


def names(response) -> set[str]:
    return {item["full_name"] for item in response.json()["items"]}


def test_listings_appear_with_unknown_facts_left_empty(client: TestClient, listings):
    res = client.get("/doctors/search", params={"specialty": "ENT", "page_size": 50})
    assert res.status_code == 200
    found = {item["full_name"]: item for item in res.json()["items"]}
    listed = found["Dr. Sylhet Listing"]
    assert listed["listing_source"] == "directory"
    assert listed["consultation_fee"] is None
    assert listed["years_experience"] is None
    assert listed["specialty_text"] == "ENT Specialist & Head Neck Surgeon"
    assert found["Dr. Unknown City Listing"]["city"] is None


def test_a_city_search_never_includes_a_listing_with_no_city(client: TestClient, listings):
    res = client.get("/doctors/search", params={"specialty": "ENT", "city": "Sylhet"})
    assert names(res) == {"Dr. Sylhet Listing"}


def test_city_spellings_find_the_same_doctors(client: TestClient, listings):
    res = client.get("/doctors/search", params={"specialty": "ENT", "city": "chittagong"})
    assert names(res) == {"Dr. Chattogram Listing"}


def test_a_listing_has_its_own_page(client: TestClient, listings):
    res = client.get(f"/doctors/{listings['sylhet']}")
    assert res.status_code == 200
    assert res.json()["source_url"].startswith("https://directory.test/")
    assert res.json()["specialties"][0]["name"] == "ENT"


def test_listings_are_suggested_with_no_online_booking(listings, no_vectors):
    found = recommend_doctors(
        {"candidate_specialties": ["ENT"], "city": "Sylhet", "strict_specialty": True}
    ).recommendations
    assert [doctor.full_name for doc in [found] for doctor in doc] == ["Dr. Sylhet Listing"]
    doctor = found[0]
    assert doctor.online_booking is False
    assert doctor.listing_source == "directory"
    assert doctor.user_id is None
    assert doctor.consultation_fee is None
    assert doctor.match_explanation == "Specializes in ENT."


def test_any_city_includes_listings_with_no_city(listings, no_vectors):
    found = recommend_doctors(
        {"candidate_specialties": ["ENT"], "city": "Bangladesh", "strict_specialty": True}
    ).recommendations
    assert "Dr. Unknown City Listing" in {doctor.full_name for doctor in found}


def test_a_listing_in_another_city_is_not_suggested(listings, no_vectors):
    found = recommend_doctors(
        {"candidate_specialties": ["ENT"], "city": "Rajshahi", "strict_specialty": True}
    ).recommendations
    assert found == []


def test_vector_search_is_filtered_by_specialty_and_city(listings):
    set_embedding_provider(FakeEmbeddingProvider(dimension=1024))
    index = MagicMock()
    index.query.return_value = [MagicMock(id=listings["sylhet"], score=0.9)]
    set_vector_store(index)
    try:
        found = recommend_doctors(
            {"candidate_specialties": ["ENT"], "city": "Sylhet", "strict_specialty": True}
        )
    finally:
        set_embedding_provider(None)
        set_vector_store(None)
    vector_filter = index.query.call_args.kwargs["where"]
    assert vector_filter["specialty_names"] == {"$in": ["ENT"]}
    assert vector_filter["city"] == {"$eq": "Sylhet"}
    assert found.retrieval_mode == "hybrid"
    assert found.recommendations[0].full_name == "Dr. Sylhet Listing"


def test_cities_with_doctors_come_from_one_short_view(listings):
    cities = {row[0] for row in sql("SELECT city FROM public.doctor_cities")}
    assert {"Sylhet", "Chattogram"} <= cities
    assert None not in cities


def test_a_listing_cannot_be_tied_to_an_account_or_lose_its_name():
    with pytest.raises(errors.CheckViolation):
        sql(
            "INSERT INTO public.doctor_profiles (listing_source, verification_status) "
            "VALUES ('directory', 'approved')"
        )
    with pytest.raises(errors.CheckViolation):
        sql(
            "INSERT INTO public.doctor_profiles (listing_source, listed_name, verification_status) "
            "VALUES ('registered', 'Dr. No Account', 'approved')"
        )
