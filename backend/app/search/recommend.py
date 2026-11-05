"""Hybrid Recommendation Service for MediMatch AI.

Combines Pinecone vector semantic retrieval with authoritative Supabase PostgreSQL
filtering and multi-factor ranking.

Guarantees:
1. Supabase is the single source of truth: doctors must be 'approved', within budget,
   and possess future unbooked availability slots.
2. Stale or invalid vectors from Pinecone are immediately discarded.
3. If Pinecone fails or returns insufficient candidates, gracefully falls back to SQL search.
4. Generates transparent, non-diagnostic match explanations.
"""

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.ai.privacy import redact_pii
from app.core.config import settings
from app.core.supabase import contains_pattern, get_supabase_admin_client
from app.models.enums import VerificationStatus
from app.search.embeddings import get_embedding_provider
from app.search.sync import get_pinecone_index

logger = logging.getLogger("medimatch.search.recommend")

MIN_HYBRID_RESULTS = 3
MAX_SQL_CANDIDATES = 200
NEUTRAL_VECTOR_SCORE = 0.5


def _is_uuid(value: str) -> bool:
    try:
        uuid.UUID(value)
        return True
    except ValueError:
        return False


class DoctorRecommendation(BaseModel):
    """Structured representation of a recommended doctor card."""

    id: str
    user_id: str
    full_name: str
    specialties: list[dict[str, Any]]
    bio: str | None = None
    qualifications: list[str] = Field(default_factory=list)
    years_experience: int = 0
    consultation_fee: float = 0.0
    clinic_name: str | None = None
    city: str
    match_score: float = Field(description="Normalized match score (0-100%)")
    available_slots_count: int = 0
    soonest_slot: str | None = None
    match_explanation: str

    model_config = ConfigDict(extra="ignore")


class RecommendationResponse(BaseModel):
    """API and chat recommendation response model."""

    recommendations: list[DoctorRecommendation]
    total_found: int
    query_specialties: list[str]
    query_city: str
    retrieval_mode: str  # "hybrid" | "sql_fallback" | "emergency_blocked"


def _generate_safe_explanation(
    specialty_names: list[str],
    years_experience: int,
) -> str:
    """Generates a template-based explanation for why this doctor matches.

    Strict Rule: Never makes medical diagnoses, clinical efficacy claims,
    or reassurances that symptoms are harmless.
    """
    specs = ", ".join(specialty_names) if specialty_names else "General Medicine"
    return f"Specializes in {specs}, with {years_experience} years of clinical experience."


def _fits_request(
    doctor_specialties: list[str],
    candidate_specialties: list[str],
    doctor_city: str | None,
    city: str,
    strict: bool = False,
) -> bool:
    """Hard filter shared by both search paths. Scoring alone can rank a wrong match first.

    A general physician is an acceptable first visit for any specialty; a doctor from an
    unrelated specialty or another city is not. The assistant searches strictly, so a person in
    emotional distress is only shown General Medicine when routing chose it.
    """
    wanted = city.strip().lower()
    if wanted and wanted != "bangladesh" and wanted not in (doctor_city or "").lower():
        return False

    cand_lower = [c.lower() for c in candidate_specialties]
    doc_lower = [s.lower() for s in doctor_specialties]
    return any(s in cand_lower or (not strict and "general" in s) for s in doc_lower)


def _calculate_score(
    vector_sim: float,
    doctor_specialties: list[str],
    candidate_specialties: list[str],
    years_experience: int,
    fee: float,
    max_fee: float | None,
    available_slots_count: int,
) -> float:
    """Calculates transparent multi-factor weighted score (0.0 to 1.0).

    Formula:
    Score = w_v * S_vector + w_s * S_specialty + w_e * S_experience + w_f * S_fee + w_a * S_availability
    """
    # 1. Vector similarity (0 to 1)
    s_vector = max(0.0, min(float(vector_sim), 1.0))

    # 2. Specialty match score
    cand_lower = [c.lower() for c in candidate_specialties]
    doc_specs_lower = [s.lower() for s in doctor_specialties]

    if any(spec in cand_lower for spec in doc_specs_lower):
        s_specialty = 1.0
    elif any("general" in s for s in doc_specs_lower):
        s_specialty = 0.5
    else:
        s_specialty = 0.2

    # 3. Clinical experience score (capped at 25 years)
    s_experience = min(years_experience / 25.0, 1.0)

    # 4. Fee fit score. A missing fee is unknown, not free, so it scores in the middle
    if fee <= 0:
        s_fee = 0.5
    elif max_fee and max_fee > 0:
        s_fee = max(0.0, 1.0 - (fee / max_fee))
    else:
        s_fee = max(0.0, 1.0 - (fee / 3000.0))

    # 5. Availability score
    if available_slots_count > 0:
        s_availability = min(0.5 + (available_slots_count * 0.05), 1.0)
    else:
        s_availability = 0.0

    total = (
        settings.WEIGHT_VECTOR * s_vector
        + settings.WEIGHT_SPECIALTY * s_specialty
        + settings.WEIGHT_EXPERIENCE * s_experience
        + settings.WEIGHT_FEE * s_fee
        + settings.WEIGHT_AVAILABILITY * s_availability
    )

    return max(0.0, min(total, 1.0))


def _doctor_query(client: Any, now_iso: str) -> Any:
    """Approved doctors with their specialties and open future slots, ready for scoring."""
    return (
        client.table("doctor_profiles")
        .select(
            "id, user_id, bio, qualifications, years_experience, consultation_fee, clinic_name, city, "
            "verification_status, profiles!inner(full_name), "
            "doctor_specialties(specialties(id, name, description)), "
            "availability_slots(id, start_time, is_booked)"
        )
        .eq("verification_status", VerificationStatus.APPROVED.value)
        .eq("availability_slots.is_booked", False)
        .gt("availability_slots.start_time", now_iso)
    )


def _to_recommendation(
    doc: dict[str, Any],
    vector_sim: float,
    candidate_specialties: list[str],
    city: str,
    max_fee: float | None,
    now_iso: str,
    strict: bool = False,
) -> DoctorRecommendation | None:
    """Applies every hard rule to a database row, or returns None if the doctor does not qualify."""
    doc_id = str(doc["id"])

    # Rule 1: Verification status MUST be 'approved' (discards stale vectors)
    if doc.get("verification_status") != VerificationStatus.APPROVED.value:
        logger.info(f"[RECOMMENDATION] Rejecting doctor {doc_id}: not approved")
        return None

    # Rule 2: Budget constraint
    fee = float(doc.get("consultation_fee", 0.0))
    if max_fee is not None and fee > max_fee:
        return None

    # Rule 3: Must match the requested city and a suitable specialty
    specs = [
        item["specialties"] for item in doc.get("doctor_specialties", []) if item.get("specialties")
    ]
    spec_names = [s["name"] for s in specs]
    if not _fits_request(spec_names, candidate_specialties, doc.get("city"), city, strict):
        return None

    # Rule 4: Must have active upcoming slots
    future_slots = sorted(
        (
            s
            for s in doc.get("availability_slots") or []
            if not s.get("is_booked") and s.get("start_time", "") > now_iso
        ),
        key=lambda s: s["start_time"],
    )
    if not future_slots:
        return None

    years = doc.get("years_experience", 0)
    soonest = future_slots[0]["start_time"]
    score = _calculate_score(
        vector_sim=vector_sim,
        doctor_specialties=spec_names,
        candidate_specialties=candidate_specialties,
        years_experience=years,
        fee=fee,
        max_fee=max_fee,
        available_slots_count=len(future_slots),
    )

    return DoctorRecommendation(
        id=doc_id,
        user_id=str(doc["user_id"]),
        full_name=(doc.get("profiles") or {}).get("full_name") or "Medical Specialist",
        specialties=specs,
        bio=doc.get("bio"),
        qualifications=doc.get("qualifications") or [],
        years_experience=years,
        consultation_fee=fee,
        clinic_name=doc.get("clinic_name"),
        city=doc.get("city", "Dhaka"),
        match_score=round(score * 100, 1),
        available_slots_count=len(future_slots),
        soonest_slot=soonest,
        match_explanation=_generate_safe_explanation(
            specialty_names=spec_names,
            years_experience=years,
        ),
    )


def _sql_fallback_search(
    candidate_specialties: list[str],
    city: str,
    max_fee: float | None = None,
    limit: int = 5,
    strict: bool = False,
) -> list[DoctorRecommendation]:
    """Graceful fallback query when Pinecone is down or yields insufficient results."""
    logger.info("[RECOMMENDATION] Executing SQL fallback search")
    client = get_supabase_admin_client()
    if not client:
        return []

    now_iso = datetime.now(UTC).isoformat()
    query = (
        _doctor_query(client, now_iso)
        .order("years_experience", desc=True)
        .limit(MAX_SQL_CANDIDATES)
    )

    if city and city.lower() != "bangladesh":
        query = query.ilike("city", contains_pattern(city))
    if max_fee is not None:
        query = query.lte("consultation_fee", max_fee)

    recommendations = [
        rec
        for doc in query.execute().data or []
        if (
            rec := _to_recommendation(
                doc, NEUTRAL_VECTOR_SCORE, candidate_specialties, city, max_fee, now_iso, strict
            )
        )
    ]
    recommendations.sort(key=lambda r: r.match_score, reverse=True)
    return recommendations[:limit]


def recommend_doctors(
    search_criteria: dict[str, Any],
    top_k: int = 5,
) -> RecommendationResponse:
    """Performs hybrid vector retrieval + PostgreSQL filtering and ranking.

    Args:
        search_criteria: {candidate_specialties: [...], city: "...", max_fee: ..., keywords: [...]}
        top_k: Number of ranked recommendations to return (default: 5)
    """
    candidate_specialties: list[str] = search_criteria.get("candidate_specialties") or [
        "General Medicine"
    ]
    city: str = search_criteria.get("city") or "Dhaka"
    max_fee: float | None = search_criteria.get("max_fee")
    raw_keywords: list[str] = search_criteria.get("keywords") or []
    strict: bool = bool(search_criteria.get("strict_specialty"))

    # 1. Redact keywords before submitting to vector query
    redacted_keywords = [redact_pii(k) for k in raw_keywords if k]
    query_text = (
        " ".join(redacted_keywords) if redacted_keywords else ", ".join(candidate_specialties)
    )

    client = get_supabase_admin_client()
    now_iso = datetime.now(UTC).isoformat()
    vector_matches: dict[str, float] = {}

    # 2. Query Pinecone vector index
    try:
        query_vector = get_embedding_provider().embed_query(query_text)
        pinecone_res = get_pinecone_index().query(
            vector=query_vector,
            top_k=max(settings.VECTOR_CANDIDATES, top_k * 3),
            filter={"status": {"$eq": VerificationStatus.APPROVED.value}},
        )
        for match in getattr(pinecone_res, "matches", []):
            m_id = getattr(match, "id", None)
            if m_id:
                vector_matches[str(m_id)] = float(getattr(match, "score", 0.0) or 0.0)
    except Exception as e:
        logger.warning(
            f"[RECOMMENDATION] Pinecone query failed ({type(e).__name__}); using SQL search."
        )

    # 3. Re-fetch every candidate from Supabase, the source of truth
    recommendations: list[DoctorRecommendation] = []
    matched_ids = [doc_id for doc_id in vector_matches if _is_uuid(doc_id)]
    if matched_ids and client:
        rows = _doctor_query(client, now_iso).in_("id", matched_ids).execute().data or []
        recommendations = [
            rec
            for doc in rows
            if (
                rec := _to_recommendation(
                    doc,
                    vector_matches[str(doc["id"])],
                    candidate_specialties,
                    city,
                    max_fee,
                    now_iso,
                    strict,
                )
            )
        ]
    retrieval_mode = "hybrid" if recommendations else "sql_fallback"

    # 4. Too few matches: add qualifying doctors from SQL, keeping the vector matches
    if len(recommendations) < MIN_HYBRID_RESULTS:
        seen = {rec.id for rec in recommendations}
        recommendations += [
            rec
            for rec in _sql_fallback_search(
                candidate_specialties, city, max_fee, limit=top_k, strict=strict
            )
            if rec.id not in seen
        ]

    recommendations.sort(key=lambda r: r.match_score, reverse=True)
    final_recs = recommendations[:top_k]

    return RecommendationResponse(
        recommendations=final_recs,
        total_found=len(final_recs),
        query_specialties=candidate_specialties,
        query_city=city,
        retrieval_mode=retrieval_mode,
    )
