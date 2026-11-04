"""Doctor Recommendation API Endpoints.

Provides direct programmatic access to hybrid doctor recommendations based on
structured clinical criteria, keywords, budget, and location.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from app.ai.safety import check_emergency
from app.api.deps import require_patient
from app.schemas.common import MAX_CONSULTATION_FEE, ShortText
from app.schemas.profile import UserMeResponse
from app.search.recommend import (
    DoctorRecommendation,
    RecommendationResponse,
    recommend_doctors,
)

router = APIRouter(prefix="/recommendations", tags=["Doctor Recommendations"])


class RecommendationQueryRequest(BaseModel):
    """Payload for requesting doctor recommendations."""

    candidate_specialties: List[ShortText] = Field(
        default_factory=lambda: ["General Medicine"],
        max_length=10,
        description="Target medical specialties from DB (e.g. Neurology, Cardiology)",
    )
    city: str = Field(default="Dhaka", max_length=100, description="Target city for doctor consultation")
    max_fee: Optional[float] = Field(default=None, ge=0, le=MAX_CONSULTATION_FEE, description="Maximum consultation fee filter in BDT")
    keywords: List[ShortText] = Field(default_factory=list, max_length=10, description="Symptom keywords for semantic retrieval")
    top_k: int = Field(default=5, ge=1, le=20, description="Maximum number of recommendations to return")


@router.post(
    "",
    response_model=RecommendationResponse,
    status_code=status.HTTP_200_OK,
    summary="Get hybrid doctor recommendations",
)
def api_get_recommendations(
    payload: RecommendationQueryRequest,
    _current_user: UserMeResponse = Depends(require_patient),
) -> RecommendationResponse:
    """Combines Pinecone semantic similarity with Supabase verification, budget limits,

    and upcoming schedule availability to rank and return suitable doctors.
    """
    # Booking a doctor is the wrong answer to an emergency, however this route was reached
    if any(check_emergency(keyword)[0] for keyword in payload.keywords):
        return RecommendationResponse(
            recommendations=[],
            total_found=0,
            query_specialties=payload.candidate_specialties,
            query_city=payload.city,
            retrieval_mode="emergency_blocked",
        )

    search_criteria = {
        "candidate_specialties": payload.candidate_specialties,
        "city": payload.city,
        "max_fee": payload.max_fee,
        "keywords": payload.keywords,
    }
    return recommend_doctors(search_criteria=search_criteria, top_k=payload.top_k)

