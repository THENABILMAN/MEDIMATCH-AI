import logging
from typing import Any, Dict, Optional
import jwt
from fastapi import HTTPException, status
from app.core.config import settings
from app.core.supabase import get_supabase_client

logger = logging.getLogger(__name__)


def decode_token_unverified(token: str) -> Dict[str, Any]:
    """Decode JWT payload without verifying signature (useful for inspecting claims)."""
    try:
        return jwt.decode(token, options={"verify_signature": False, "verify_exp": False})
    except Exception as e:
        logger.warning(f"Failed to decode token unverified: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token format",
            headers={"WWW-Authenticate": "Bearer"},
        )


def _decode_test_token(token: str) -> Dict[str, Any]:
    """Decode a test fixture token. Must only be called when ENVIRONMENT is 'test'."""
    try:
        payload = jwt.decode(token, options={"verify_signature": False})
    except jwt.PyJWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not payload.get("sub"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload is missing subject claim",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload


def verify_supabase_token(token: str) -> Dict[str, Any]:
    """Verify a Supabase JWT with the Supabase Auth API.

    Signatures are never skipped outside ENVIRONMENT='test'. In every other
    environment, a token that Supabase does not confirm is rejected.
    """
    if not token or not isinstance(token, str):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token is missing",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Clean bearer prefix if accidentally passed
    token = token.replace("Bearer ", "").strip()

    if settings.ENVIRONMENT == "test":
        return _decode_test_token(token)

    supabase = get_supabase_client()
    if not supabase:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable",
        )

    try:
        user_response = supabase.auth.get_user(token)
    except Exception as exc:
        logger.warning(f"Supabase auth verification failed: {exc}")
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
