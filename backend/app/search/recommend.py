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

import uuid
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.ai.privacy import redact_pii
from app.core.config import settings
from app.core.supabase import get_supabase_admin_client, get_supabase_client
from app.models.enums import VerificationStatus
from app.search.embeddings import get_embedding_provider
from app.search.sync import get_pinecone_index

logger = logging.getLogger("medimatch.search.recommend")


class DoctorRecommendation(BaseModel):
    """Structured representation of a recommended doctor card."""

    id: str
    user_id: str
    full_name: str
    specialties: List[Dict[str, Any]]
    bio: Optional[str] = None
    qualifications: List[str] = Field(default_factory=list)
    years_experience: int = 0
    consultation_fee: float = 0.0
    clinic_name: Optional[str] = None
    city: str
    match_score: float = Field(description="Normalized match score (0-100%)")
    available_slots_count: int = 0
    soonest_slot: Optional[str] = None
    match_explanation: str

    model_config = ConfigDict(extra="ignore")


class RecommendationResponse(BaseModel):
    """API and chat recommendation response model."""

    recommendations: List[DoctorRecommendation]
    total_found: int
    query_specialties: List[str]
    query_city: str
    retrieval_mode: str  # "hybrid" | "sql_fallback"


def _generate_safe_explanation(
    specialty_names: List[str],
    city: str,
    years_experience: int,
    fee: float,
    soonest_slot: Optional[str],
) -> str:
    """Generates a template-based explanation for why this doctor matches.

    Strict Rule: Never makes medical diagnoses, clinical efficacy claims,
    or reassurances that symptoms are harmless.
    """
    specs = ", ".join(specialty_names) if specialty_names else "General Medicine"
    explanation = (
        f"Specializes in {specs} in {city}. Has {years_experience} years of clinical experience "
        f"with consultation fee of {int(fee)} BDT."
    )
    if soonest_slot:
        try:
            dt = datetime.fromisoformat(soonest_slot.replace("Z", "+00:00"))
            time_str = dt.strftime("%b %d at %I:%M %p UTC")
            explanation += f" Earliest appointment available on {time_str}."
        except Exception:
            explanation += " Has upcoming appointments available."
    return explanation


def _calculate_score(
    vector_sim: float,
    doctor_specialties: List[str],
    candidate_specialties: List[str],
    years_experience: int,
    fee: float,
    max_fee: Optional[float],
    available_slots_count: int,
    soonest_slot: Optional[str],
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

    # 4. Fee fit score
    if max_fee and max_fee > 0:
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


def _sql_fallback_search(
    candidate_specialties: List[str],
    city: str,
    max_fee: Optional[float] = None,
    limit: int = 5,
) -> List[DoctorRecommendation]:
    """Graceful fallback query when Pinecone is down or yields insufficient results."""
    logger.info("[RECOMMENDATION] Executing SQL fallback search")
    client = get_supabase_admin_client() or get_supabase_client()
    if not client:
        return []

    now_iso = datetime.now(timezone.utc).isoformat()

    # Query approved doctors with upcoming slots
    query = (
        client.table("doctor_profiles")
        .select(
            "id, user_id, bio, qualifications, years_experience, consultation_fee, clinic_name, city, "
            "verification_status, profiles!inner(full_name), "
            "doctor_specialties(specialties(id, name, description)), "
            "availability_slots(id, start_time, is_booked)"
        )
        .eq("verification_status", VerificationStatus.APPROVED.value)
    )

    if city and city.lower() != "bangladesh":
        query = query.ilike("city", f"%{city.strip()}%")

    if max_fee is not None:
        query = query.lte("consultation_fee", max_fee)

    res = query.execute()
    raw_doctors = res.data or []

    recommendations: List[DoctorRecommendation] = []
    for doc in raw_doctors:
        doc_id = str(doc["id"])
        specs = [item["specialties"] for item in doc.get("doctor_specialties", []) if item.get("specialties")]
        spec_names = [s["name"] for s in specs]

        # Extract future unbooked slots
        all_slots = doc.get("availability_slots") or []
        future_slots = [
            s for s in all_slots if not s.get("is_booked") and s.get("start_time", "") > now_iso
        ]
        if not future_slots:
            continue

        future_slots.sort(key=lambda s: s["start_time"])
        soonest = future_slots[0]["start_time"] if future_slots else None

        score = _calculate_score(
            vector_sim=0.5,  # neutral default for SQL fallback
            doctor_specialties=spec_names,
            candidate_specialties=candidate_specialties,
            years_experience=doc.get("years_experience", 0),
            fee=float(doc.get("consultation_fee", 0.0)),
            max_fee=max_fee,
            available_slots_count=len(future_slots),
            soonest_slot=soonest,
        )

        full_name = doc.get("profiles", {}).get("full_name") or "Medical Specialist"
        explanation = _generate_safe_explanation(
            specialty_names=spec_names,
            city=doc.get("city", "Dhaka"),
            years_experience=doc.get("years_experience", 0),
            fee=float(doc.get("consultation_fee", 0.0)),
            soonest_slot=soonest,
        )

        recommendations.append(
            DoctorRecommendation(
                id=doc_id,
                user_id=str(doc["user_id"]),
                full_name=full_name,
                specialties=specs,
                bio=doc.get("bio"),
                qualifications=doc.get("qualifications") or [],
                years_experience=doc.get("years_experience", 0),
                consultation_fee=float(doc.get("consultation_fee", 0.0)),
                clinic_name=doc.get("clinic_name"),
                city=doc.get("city", "Dhaka"),
                match_score=round(score * 100, 1),
                available_slots_count=len(future_slots),
                soonest_slot=soonest,
                match_explanation=explanation,
            )
        )

    recommendations.sort(key=lambda r: r.match_score, reverse=True)
    return recommendations[:limit]


def recommend_doctors(
    search_criteria: Dict[str, Any],
    top_k: int = 5,
) -> RecommendationResponse:
    """Performs hybrid vector retrieval + PostgreSQL filtering and ranking.

    Args:
        search_criteria: {candidate_specialties: [...], city: "...", max_fee: ..., keywords: [...]}
        top_k: Number of ranked recommendations to return (default: 5)
    """
    candidate_specialties: List[str] = search_criteria.get("candidate_specialties") or ["General Medicine"]
    city: str = search_criteria.get("city") or "Dhaka"
    max_fee: Optional[float] = search_criteria.get("max_fee")
    raw_keywords: List[str] = search_criteria.get("keywords") or []

    # 1. Redact keywords before submitting to vector query
    redacted_keywords = [redact_pii(k) for k in raw_keywords if k]
    query_text = " ".join(redacted_keywords) if redacted_keywords else ", ".join(candidate_specialties)

    client = get_supabase_admin_client() or get_supabase_client()
    now_iso = datetime.now(timezone.utc).isoformat()

    vector_matches: Dict[str, float] = {}
    used_sql_fallback = False

    # 2. Query Pinecone vector index
    try:
        provider = get_embedding_provider()
        query_vector = provider.embed_query(query_text)

        index = get_pinecone_index()
        # Query with top_k=15 to leave room for post-filtering
        pinecone_res = index.query(
            vector=query_vector,
            top_k=15,
            include_metadata=True,
        )

        for match in getattr(pinecone_res, "matches", []):
            m_id = getattr(match, "id", None) or match.get("id")
            m_score = getattr(match, "score", 0.0) or match.get("score", 0.0)
            if m_id:
                vector_matches[str(m_id)] = float(m_score)

    except Exception as e:
        logger.warning(f"[RECOMMENDATION] Pinecone query failed ({e}); switching to SQL fallback.")
        used_sql_fallback = True

    # 3. If Pinecone returned candidates, re-fetch and strictly verify from Supabase
    recommendations: List[DoctorRecommendation] = []
    if vector_matches and not used_sql_fallback and client:
        # Filter for valid UUIDs to prevent Postgres syntax errors
        matched_ids = []
        for raw_id in vector_matches.keys():
            try:
                uuid.UUID(str(raw_id))
                matched_ids.append(str(raw_id))
            except (ValueError, TypeError):
                continue

        if matched_ids:
            res = (
                client.table("doctor_profiles")
                .select(
                    "id, user_id, bio, qualifications, years_experience, consultation_fee, clinic_name, city, "
                    "verification_status, profiles!inner(full_name), "
                    "doctor_specialties(specialties(id, name, description)), "
                    "availability_slots(id, start_time, is_booked)"
                )
                .in_("id", matched_ids)
                .execute()
            )
            raw_docs = res.data or []
        else:
            raw_docs = []

        for doc in raw_docs:
            doc_id = str(doc["id"])

            # Rule 1: Verification status MUST be 'approved' (discards stale vectors)
            if doc.get("verification_status") != VerificationStatus.APPROVED.value:
                logger.info(f"[RECOMMENDATION] Rejecting doctor {doc_id}: not approved")
                continue

            # Rule 2: Budget constraint
            fee = float(doc.get("consultation_fee", 0.0))
            if max_fee is not None and fee > max_fee:
                logger.info(f"[RECOMMENDATION] Rejecting doctor {doc_id}: fee {fee} > max_fee {max_fee}")
                continue

            # Rule 3: Must have active upcoming slots
            all_slots = doc.get("availability_slots") or []
            future_slots = [
                s for s in all_slots if not s.get("is_booked") and s.get("start_time", "") > now_iso
            ]
            if not future_slots:
                logger.info(f"[RECOMMENDATION] Rejecting doctor {doc_id}: no future availability slots")
                continue

            future_slots.sort(key=lambda s: s["start_time"])
            soonest = future_slots[0]["start_time"] if future_slots else None

            specs = [item["specialties"] for item in doc.get("doctor_specialties", []) if item.get("specialties")]
            spec_names = [s["name"] for s in specs]

            sim = vector_matches.get(doc_id, 0.5)
            score = _calculate_score(
                vector_sim=sim,
                doctor_specialties=spec_names,
                candidate_specialties=candidate_specialties,
                years_experience=doc.get("years_experience", 0),
                fee=fee,
                max_fee=max_fee,
                available_slots_count=len(future_slots),
                soonest_slot=soonest,
            )

            full_name = doc.get("profiles", {}).get("full_name") or "Medical Specialist"
            explanation = _generate_safe_explanation(
                specialty_names=spec_names,
                city=doc.get("city", "Dhaka"),
                years_experience=doc.get("years_experience", 0),
                fee=fee,
                soonest_slot=soonest,
            )

            recommendations.append(
                DoctorRecommendation(
                    id=doc_id,
                    user_id=str(doc["user_id"]),
                    full_name=full_name,
                    specialties=specs,
                    bio=doc.get("bio"),
                    qualifications=doc.get("qualifications") or [],
                    years_experience=doc.get("years_experience", 0),
                    consultation_fee=fee,
                    clinic_name=doc.get("clinic_name"),
                    city=doc.get("city", "Dhaka"),
                    match_score=round(score * 100, 1),
                    available_slots_count=len(future_slots),
                    soonest_slot=soonest,
                    match_explanation=explanation,
                )
            )

    # 4. If fewer than 3 qualifying recommendations found, fall back to SQL search
    if len(recommendations) < 3:
        fallback_results = _sql_fallback_search(
            candidate_specialties=candidate_specialties,
            city=city,
            max_fee=max_fee,
            limit=top_k,
        )
        if fallback_results:
            recommendations = fallback_results
            used_sql_fallback = True

    # Sort descending by match score
    recommendations.sort(key=lambda r: r.match_score, reverse=True)
    final_recs = recommendations[:top_k]

    return RecommendationResponse(
        recommendations=final_recs,
        total_found=len(final_recs),
        query_specialties=candidate_specialties,
        query_city=city,
        retrieval_mode="sql_fallback" if used_sql_fallback else "hybrid",
    )
