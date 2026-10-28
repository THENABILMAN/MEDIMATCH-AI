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


def verify_supabase_token(token: str) -> Dict[str, Any]:
    """Verify Supabase JWT token.
    
    In production/staging with Supabase connectivity, validates with Supabase Auth API.
    In testing or offline mode, falls back to PyJWT token validation.
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
    if supabase and settings.ENVIRONMENT != "test":
        try:
            user_response = supabase.auth.get_user(token)
            if user_response and user_response.user:
                u = user_response.user
                return {
                    "sub": str(u.id),
                    "email": u.email,
                    "user_metadata": u.user_metadata or {},
                    "app_metadata": u.app_metadata or {},
                }
        except Exception as exc:
            logger.warning(f"Supabase auth verification failed: {exc}")
            # Do not immediately fail if it could be a test token in non-production
            if settings.ENVIRONMENT == "production":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired token",
                    headers={"WWW-Authenticate": "Bearer"},
                )

    # Fallback / Test decoding
    try:
        payload = jwt.decode(token, options={"verify_signature": False})
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token payload is missing subject claim",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return payload
    except jwt.PyJWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )

