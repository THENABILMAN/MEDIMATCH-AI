import logging
from typing import Callable, Iterator, List
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from postgrest import SyncPostgrestClient
from app.core.security import verify_supabase_token
from app.core.supabase import create_user_client
from app.models.enums import UserRole
from app.schemas.profile import UserMeResponse
from app.services.profile_service import get_user_profile

logger = logging.getLogger(__name__)

security_scheme = HTTPBearer(auto_error=True)


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
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching profile for {user_id}: {type(e).__name__}")
        # Never fall back to token claims here: user_metadata is editable by the user
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not load user profile",
        )


def get_user_db(
    credentials: HTTPAuthorizationCredentials = Security(security_scheme),
) -> Iterator[SyncPostgrestClient]:
    """A database client scoped to the caller, for reads that RLS should also guard."""
    client = create_user_client(credentials.credentials)
    try:
        yield client
    finally:
        client.aclose()


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


require_patient = require_role([UserRole.PATIENT])
require_doctor = require_role([UserRole.DOCTOR])
require_admin = require_role([UserRole.ADMIN])
