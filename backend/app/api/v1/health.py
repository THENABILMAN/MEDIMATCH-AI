import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.core.config import settings
from app.core.supabase import get_supabase_client

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Health"])


class HealthResponse(BaseModel):
    status: str
    service: str


@router.get("/health", response_model=HealthResponse, summary="Liveness: the process is running")
def health_check() -> dict[str, str]:
    return {"status": "healthy", "service": "MediMatch AI"}


@router.get("/ready", summary="Readiness: the service can reach its database")
def readiness_check() -> JSONResponse:
    """Pinecone and OpenRouter are reported but optional, because both have fallbacks."""
    database = "unavailable"
    client = get_supabase_client()
    if client:
        try:
            client.table("specialties").select("id").limit(1).execute()
            database = "ok"
        except Exception as e:
            logger.error(f"Readiness check failed: {type(e).__name__}")

    ready = database == "ok"
    return JSONResponse(
        status_code=200 if ready else 503,
        content={
            "status": "ready" if ready else "unavailable",
            "checks": {
                "database": database,
                "vector_search": "configured" if settings.PINECONE_API_KEY else "fallback",
                "llm": "configured" if settings.OPENROUTER_API_KEY else "fallback",
            },
        },
    )
