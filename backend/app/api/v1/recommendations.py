"""Doctor Recommendation API Endpoints.

Provides direct programmatic access to hybrid doctor recommendations based on
structured clinical criteria, keywords, budget, and location.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, status
from pydantic import BaseModel, Field
from app.search.recommend import (
    DoctorRecommendation,
    RecommendationResponse,
    recommend_doctors,
)

router = APIRouter(prefix="/recommendations", tags=["Doctor Recommendations"])


class RecommendationQueryRequest(BaseModel):
    """Payload for requesting doctor recommendations."""

    candidate_specialties: List[str] = Field(
        default_factory=lambda: ["General Medicine"],
        description="Target medical specialties from DB (e.g. Neurology, Cardiology)",
    )
    city: str = Field(default="Dhaka", description="Target city for doctor consultation")
    max_fee: Optional[float] = Field(default=None, description="Maximum consultation fee filter in BDT")
    keywords: List[str] = Field(default_factory=list, description="Symptom keywords for semantic retrieval")
    top_k: int = Field(default=5, ge=1, le=20, description="Maximum number of recommendations to return")


@router.post(
    "",
    response_model=RecommendationResponse,
    status_code=status.HTTP_200_OK,
    summary="Get hybrid doctor recommendations",
)
def api_get_recommendations(payload: RecommendationQueryRequest) -> RecommendationResponse:
    """Combines Pinecone semantic similarity with Supabase verification, budget limits,

    and upcoming schedule availability to rank and return suitable doctors.
    """
    search_criteria = {
        "candidate_specialties": payload.candidate_specialties,
        "city": payload.city,
        "max_fee": payload.max_fee,
        "keywords": payload.keywords,
    }
    return recommend_doctors(search_criteria=search_criteria, top_k=payload.top_k)

