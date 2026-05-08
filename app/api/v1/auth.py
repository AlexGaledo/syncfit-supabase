"""
Authentication routes
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.schemas.user import (
    UserResponse,
    UserProfileBase,
    UserProfileUpdate,
    UserProfileResponse,
)
from app.models.user import User, User_Profile  # <-- use your real model names


router = APIRouter(prefix="/auth", tags=["Authentication"])



# ============================================================================
# AUTH: CURRENT USER PROFILE
# ============================================================================


@router.get("/me", response_model=UserProfileResponse)
async def get_current_user_info(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get current authenticated user's profile

    - Reads Supabase user id from JWT (current_user["sub"])
    - Resolves the corresponding User row (via User.supabase_user_id)
    - Returns the associated User_Profile (creating an empty one if missing)
    """
    sub = current_user.get("sub")
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
        )

    # Find the User by Supabase user id (UUID)
    user = db.query(User).filter(User.supabase_user_id == sub).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Find or create the User_Profile for this user
    profile = db.query(User_Profile).filter(User_Profile.user_id == user.id).first()
    if not profile:
        profile = User_Profile(user_id=user.id)
        db.add(profile)
        db.commit()
        db.refresh(profile)

    return profile



@router.post("/me", response_model=UserProfileResponse)
async def update_current_user_profile(
    payload: UserProfileUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update current authenticated user's profile

    - Uses Supabase user id from JWT to resolve the User
    - Applies partial updates from UserProfileUpdate (bio, address, macros, etc.)
    - Returns the updated User_Profile
    """
    sub = current_user.get("sub")
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
        )

    # Find the User by Supabase user id
    user = db.query(User).filter(User.supabase_user_id == sub).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Find or create the User_Profile for this user
    profile = db.query(User_Profile).filter(User_Profile.user_id == user.id).first()
    if not profile:
        profile = User_Profile(user_id=user.id)
        db.add(profile)
        db.commit()
        db.refresh(profile)

    # Apply only fields that were provided
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(profile, field, value)

    db.commit()
    db.refresh(profile)

    return profile



# ============================================================================
# AUTH: TOKEN VERIFICATION
# ============================================================================


@router.post("/verify")
async def verify_token(
    current_user: dict = Depends(get_current_user),
):
    """
    Verify if the provided token is valid
    """
    return {
        "valid": True,
        "user_id": current_user.get("sub"),
        "email": current_user.get("email"),
    }