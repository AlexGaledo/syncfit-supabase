"""
User routes
"""
from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from app.database import get_db
from app.dependencies import get_current_user, get_current_db_user
from app.models.user import (
    User, UserRole as UserRoleModel,
    User_Profile, User_Supplements, User_Limitations,
    Weight_Loss_Progress,
)
from app.models.item import User_Badges, Badges
from app.schemas.user import (
    UserResponse, UserCreateRequest, UserUpdate,
    UserProfileUpdate, UserProfileResponse,
    UserSupplementCreate, UserSupplementResponse,
    UserLimitationCreate, UserLimitationResponse,
    WeightLossProgressBase, WeightLossProgressResponse,
)
from app.schemas.item import UserBadgeResponse

router = APIRouter(prefix="/users", tags=["Users"])


# ============================================================================
# HELPERS
# ============================================================================

def _get_user_or_404(db: Session, user_id: UUID) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


def _assert_self_or_admin(user: User, current_user: dict, db: Session) -> None:
    """Raises 403 if the caller is neither the account owner nor an admin."""
    sub = current_user["sub"]
    is_owner = (
        db.query(User.id)
        .filter(User.supabase_user_id == sub, User.id == user.id)
        .first()
        is not None
    )
    is_admin = (
        db.query(User.id)
        .filter(User.supabase_user_id == sub, User.role == UserRoleModel.admin)
        .first()
        is not None
    )
    if not (is_owner or is_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access your own data"
        )


# ============================================================================
# USER ENDPOINTS
# ============================================================================

@router.get("/get_users", response_model=List[UserResponse])
async def get_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get all users — admin only.
    """
    is_admin = (
        db.query(User.id)
        .filter(
            User.supabase_user_id == current_user["sub"],
            User.role == UserRoleModel.admin,
        )
        .first()
        is not None
    )
    if not is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return db.query(User).offset(skip).limit(limit).all()


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    db: Session = Depends(get_db),
):
    """Get a specific user by ID."""
    return _get_user_or_404(db, user_id)


@router.post("/create-user", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: Optional[UserCreateRequest] = Body(default=None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new user record linked to the authenticated Supabase account.
    email and supabase_user_id are taken from the verified JWT token.
    """
    supabase_user_id = current_user["sub"]
    email = current_user["email"]

    existing_user = db.query(User).filter(User.supabase_user_id == supabase_user_id).first()
    if existing_user:
        return existing_user

    extra = user_data.model_dump() if user_data else {}
    db_user = User(supabase_user_id=supabase_user_id, email=email, **extra)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Update a user. Only the account owner or an admin may do this."""
    user = _get_user_or_404(db, user_id)

    _assert_self_or_admin(user, current_user, db)

    is_admin = (
        db.query(User.id)
        .filter(
            User.supabase_user_id == current_user["sub"],
            User.role == UserRoleModel.admin,
        )
        .first()
        is not None
    )

    if not is_admin and user_data.role is not None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can change user roles")

    update_data = user_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Delete a user. Only the account owner or an admin may do this."""
    user = _get_user_or_404(db, user_id)
    _assert_self_or_admin(user, current_user, db)

    db.delete(user)
    db.commit()
    return None


# ============================================================================
# PROFILE ENDPOINTS
# ============================================================================

@router.get("/{user_id}/profile", response_model=UserProfileResponse)
async def get_profile(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get a user's profile."""
    user = _get_user_or_404(db, user_id)
    if not user.profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    return user.profile


@router.post("/{user_id}/profile", response_model=UserProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_profile(
    user_id: UUID,
    profile_data: UserProfileUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create a profile for a user. Idempotent — returns existing profile if already created."""
    user = _get_user_or_404(db, user_id)
    _assert_self_or_admin(user, current_user, db)

    if user.profile:
        return user.profile

    profile = User_Profile(user_id=user_id, **profile_data.model_dump(exclude_unset=True))
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


@router.patch("/{user_id}/profile", response_model=UserProfileResponse)
async def update_profile(
    user_id: UUID,
    profile_data: UserProfileUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Update a user's profile."""
    user = _get_user_or_404(db, user_id)
    _assert_self_or_admin(user, current_user, db)

    if not user.profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found. Create it first.")

    update_data = profile_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user.profile, field, value)

    db.commit()
    db.refresh(user.profile)
    return user.profile


# ============================================================================
# SUPPLEMENTS ENDPOINTS
# ============================================================================

@router.get("/{user_id}/supplements", response_model=List[UserSupplementResponse])
async def get_supplements(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """List a user's supplements."""
    user = _get_user_or_404(db, user_id)
    _assert_self_or_admin(user, current_user, db)
    if not user.profile:
        return []
    return user.profile.supplements


@router.post("/{user_id}/supplements", response_model=UserSupplementResponse, status_code=status.HTTP_201_CREATED)
async def add_supplement(
    user_id: UUID,
    supplement_data: UserSupplementCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Add a supplement to a user's profile."""
    user = _get_user_or_404(db, user_id)
    _assert_self_or_admin(user, current_user, db)

    if not user.profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found. Create it first.")

    supplement = User_Supplements(
        user_id=user.profile.id,
        supplement_name=supplement_data.supplement_name,
    )
    db.add(supplement)
    db.commit()
    db.refresh(supplement)
    return supplement


@router.delete("/{user_id}/supplements/{supplement_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_supplement(
    user_id: UUID,
    supplement_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Remove a supplement from a user's profile."""
    user = _get_user_or_404(db, user_id)
    _assert_self_or_admin(user, current_user, db)

    if user.profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")

    supplement = db.query(User_Supplements).filter(
        User_Supplements.id == supplement_id,
        User_Supplements.user_id == user.profile.id,
    ).first()
    if not supplement:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplement not found")

    db.delete(supplement)
    db.commit()
    return None


# ============================================================================
# LIMITATIONS ENDPOINTS
# ============================================================================

@router.get("/{user_id}/limitations", response_model=List[UserLimitationResponse])
async def get_limitations(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """List a user's physical limitations."""
    user = _get_user_or_404(db, user_id)
    _assert_self_or_admin(user, current_user, db)
    if not user.profile:
        return []
    return user.profile.limitations


@router.post("/{user_id}/limitations", response_model=UserLimitationResponse, status_code=status.HTTP_201_CREATED)
async def add_limitation(
    user_id: UUID,
    limitation_data: UserLimitationCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Add a physical limitation to a user's profile."""
    user = _get_user_or_404(db, user_id)
    _assert_self_or_admin(user, current_user, db)

    if not user.profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found. Create it first.")

    limitation = User_Limitations(
        user_id=user.profile.id,
        limitation_description=limitation_data.limitation_description,
    )
    db.add(limitation)
    db.commit()
    db.refresh(limitation)
    return limitation


@router.delete("/{user_id}/limitations/{limitation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_limitation(
    user_id: UUID,
    limitation_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Remove a physical limitation from a user's profile."""
    user = _get_user_or_404(db, user_id)
    _assert_self_or_admin(user, current_user, db)

    if user.profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")

    limitation = db.query(User_Limitations).filter(
        User_Limitations.id == limitation_id,
        User_Limitations.user_id == user.profile.id,
    ).first()
    if not limitation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Limitation not found")

    db.delete(limitation)
    db.commit()
    return None


# ============================================================================
# WEIGHT PROGRESS ENDPOINTS
# ============================================================================

@router.get("/{user_id}/weight-progress", response_model=List[WeightLossProgressResponse])
async def get_weight_progress(
    user_id: UUID,
    skip: int = 0,
    limit: int = 90,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get a user's weight progress history, ordered from newest to oldest."""
    user = _get_user_or_404(db, user_id)
    _assert_self_or_admin(user, current_user, db)

    entries = (
        db.query(Weight_Loss_Progress)
        .filter(Weight_Loss_Progress.user_id == user_id)
        .order_by(Weight_Loss_Progress.date.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return entries


@router.post("/{user_id}/weight-progress", response_model=WeightLossProgressResponse, status_code=status.HTTP_201_CREATED)
async def log_weight(
    user_id: UUID,
    progress_data: WeightLossProgressBase,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Log a new weight entry for a user."""
    user = _get_user_or_404(db, user_id)
    _assert_self_or_admin(user, current_user, db)

    entry = Weight_Loss_Progress(user_id=user_id, weight=progress_data.weight)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


# ============================================================================
# BADGES ENDPOINTS
# ============================================================================

@router.get("/{user_id}/badges", response_model=List[UserBadgeResponse])
async def get_badges(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get all badges earned by a user."""
    _get_user_or_404(db, user_id)
    badges = db.query(User_Badges).filter(User_Badges.user_id == user_id).all()
    return badges
