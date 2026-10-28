from fastapi import APIRouter, Depends
from app.api.deps import get_current_user
from app.schemas.profile import ProfileUpdate, UserMeResponse
from app.services.profile_service import update_user_profile

router = APIRouter(tags=["Users"])


@router.get("/me", response_model=UserMeResponse, summary="Get current authenticated user profile")
def get_me(current_user: UserMeResponse = Depends(get_current_user)) -> UserMeResponse:
    return current_user


@router.patch("/me", response_model=UserMeResponse, summary="Update current user profile")
def update_me(
    payload: ProfileUpdate,
    current_user: UserMeResponse = Depends(get_current_user),
) -> UserMeResponse:
    return update_user_profile(
        user_id=current_user.id,
        payload=payload,
        email=current_user.email,
    )
