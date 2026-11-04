import logging
from typing import Any

import httpx
from fastapi import HTTPException, status
from supabase_auth.errors import AuthRetryableError

from app.core.supabase import get_supabase_client

logger = logging.getLogger(__name__)


def verify_supabase_token(token: str) -> dict[str, Any]:
    """Verify a Supabase JWT with the Supabase Auth API.

    A token that Supabase does not confirm is rejected. If Supabase cannot be reached, the
    answer is 503, so an outage does not look like an expired session and sign people out.
    """
    if not token or not isinstance(token, str):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token is missing",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Clean bearer prefix if accidentally passed
    token = token.replace("Bearer ", "").strip()

    supabase = get_supabase_client()
    if not supabase:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable",
        )

    try:
        user_response = supabase.auth.get_user(token)
    except (httpx.TransportError, AuthRetryableError) as exc:
        logger.error(f"Supabase auth unreachable: {type(exc).__name__}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable",
        ) from exc
    except Exception as exc:
        logger.warning(f"Supabase auth verification failed: {type(exc).__name__}")
        user_response = None

    if not user_response or not user_response.user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    u = user_response.user
    return {
        "sub": str(u.id),
        "email": u.email,
        "user_metadata": u.user_metadata or {},
        "app_metadata": u.app_metadata or {},
    }
