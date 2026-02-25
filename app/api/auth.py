"""
Authentication routes
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.schemas.user import UserResponse, UserProfileBase

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.get("/me", response_model=UserProfileBase)
async def get_current_user_info(
    current_user: dict = Depends(get_current_user)
):
    """
    Get current authenticated user information from token
    """
    return {
        "sub": current_user.get("sub"),
        "email": current_user.get("email"),
        "role": current_user.get("role"),
    }


@router.post("/verify")
async def verify_token(
    current_user: dict = Depends(get_current_user)
):
    """
    Verify if the provided token is valid
    """
    return {
        "valid": True,
        "user_id": current_user.get("sub"),
        "email": current_user.get("email")
    }
