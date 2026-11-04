import logging
from typing import Any, Callable, Dict, List, Optional
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.core.config import settings
from app.core.security import verify_supabase_token
from app.models.enums import UserRole
from app.schemas.profile import UserMeResponse
from app.services.profile_service import get_user_profile

logger = logging.getLogger(__name__)

security_scheme = HTTPBearer(auto_error=True)


def _test_user_from_claims(
    payload: Dict[str, Any], user_id: str, email: Optional[str]
) -> UserMeResponse:
    """Builds a user from token claims. Claims are user-editable, so this is test-only."""
    role_claim = (
        payload.get("user_metadata", {}).get("role")
        or payload.get("app_metadata", {}).get("role")
        or payload.get("role")
        or "patient"
    )
    try:
        valid_role = UserRole(role_claim)
    except ValueError:
        valid_role = UserRole.PATIENT

    full_name = payload.get("user_metadata", {}).get("full_name") or "User"
    return UserMeResponse(
        id=user_id,
        email=email,
        role=valid_role,
        full_name=full_name,
        phone=None,
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security_scheme),
) -> UserMeResponse:
    """FastAPI dependency to extract and validate the current authenticated user."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    payload = verify_supabase_token(token)
    user_id = payload.get("sub")
    email = payload.get("email")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Subject claim missing in token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        return get_user_profile(user_id=user_id, email=email)
    except HTTPException as e:
        if settings.ENVIRONMENT == "test" and e.status_code == status.HTTP_404_NOT_FOUND:
            return _test_user_from_claims(payload, user_id, email)
        raise
    except Exception as e:
        logger.error(f"Error fetching profile for {user_id}: {e}")
        if settings.ENVIRONMENT == "test":
            return _test_user_from_claims(payload, user_id, email)
        # Never fall back to token claims here: user_metadata is editable by the user
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not load user profile",
        )


def require_role(allowed_roles: List[UserRole]) -> Callable[[UserMeResponse], UserMeResponse]:
    """Dependency factory restricting route access to specified roles."""
    def role_checker(current_user: UserMeResponse = Depends(get_current_user)) -> UserMeResponse:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access forbidden: requires one of {[r.value for r in allowed_roles]} roles",
            )
        return current_user

    return role_checker


require_patient = require_role([UserRole.PATIENT, UserRole.ADMIN])
require_doctor = require_role([UserRole.DOCTOR, UserRole.ADMIN])
require_admin = require_role([UserRole.ADMIN])
