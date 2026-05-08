"""User routes. Thin handlers — logic in app/services/user_service."""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Body, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.schemas.user import (
    UserResponse,
    UserCreateRequest,
    UserUpdate,
    UserProfileUpdate,
    UserProfileResponse,
    UserSupplementCreate,
    UserSupplementResponse,
    UserLimitationCreate,
    UserLimitationResponse,
    WeightLossProgressBase,
    WeightLossProgressResponse,
    UserListItem,
)
from app.schemas.item import UserBadgeResponse
from app.services import user_service, auth_service

router = APIRouter(prefix="/users", tags=["Users"])


# ---- Users ----

@router.get("/get_users", response_model=List[UserResponse])
async def get_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    return user_service.list_users(db, skip, limit, current_user)


@router.get("/get-all-trainees", response_model=List[UserListItem])
def get_all_trainees(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    return user_service.list_trainees(db, skip, limit)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: UUID, db: Session = Depends(get_db)):
    return auth_service.get_user_or_404(db, user_id)


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: Optional[UserCreateRequest] = Body(default=None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    return user_service.get_or_create_for_supabase(db, current_user, user_data)


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    return user_service.update_user(db, user_id, user_data, current_user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_service.delete_user(db, user_id, current_user)
    return None


# ---- Profile ----

@router.get("/{user_id}/profile", response_model=UserProfileResponse)
async def get_profile(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    return user_service.get_profile(db, user_id)


@router.post(
    "/{user_id}/profile",
    response_model=UserProfileResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_profile(
    user_id: UUID,
    profile_data: UserProfileUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    return user_service.create_profile(db, user_id, profile_data, current_user)


@router.patch("/{user_id}/profile", response_model=UserProfileResponse)
async def update_profile(
    user_id: UUID,
    profile_data: UserProfileUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    return user_service.update_profile(db, user_id, profile_data, current_user)


# ---- Supplements ----

@router.get("/{user_id}/supplements", response_model=List[UserSupplementResponse])
async def get_supplements(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    return user_service.list_supplements(db, user_id, current_user)


@router.post(
    "/{user_id}/supplements",
    response_model=UserSupplementResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_supplement(
    user_id: UUID,
    supplement_data: UserSupplementCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    return user_service.add_supplement(db, user_id, supplement_data, current_user)


@router.delete(
    "/{user_id}/supplements/{supplement_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_supplement(
    user_id: UUID,
    supplement_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_service.remove_supplement(db, user_id, supplement_id, current_user)
    return None


# ---- Limitations ----

@router.get("/{user_id}/limitations", response_model=List[UserLimitationResponse])
async def get_limitations(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    return user_service.list_limitations(db, user_id, current_user)


@router.post(
    "/{user_id}/limitations",
    response_model=UserLimitationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_limitation(
    user_id: UUID,
    limitation_data: UserLimitationCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    return user_service.add_limitation(db, user_id, limitation_data, current_user)


@router.delete(
    "/{user_id}/limitations/{limitation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_limitation(
    user_id: UUID,
    limitation_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_service.remove_limitation(db, user_id, limitation_id, current_user)
    return None


# ---- Weight progress ----

@router.get(
    "/{user_id}/weight-progress",
    response_model=List[WeightLossProgressResponse],
)
async def get_weight_progress(
    user_id: UUID,
    skip: int = 0,
    limit: int = 90,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    return user_service.list_weight_progress(db, user_id, skip, limit, current_user)


@router.post(
    "/{user_id}/weight-progress",
    response_model=WeightLossProgressResponse,
    status_code=status.HTTP_201_CREATED,
)
async def log_weight(
    user_id: UUID,
    progress_data: WeightLossProgressBase,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    return user_service.log_weight(db, user_id, progress_data, current_user)


# ---- Badges ----

@router.get("/{user_id}/badges", response_model=List[UserBadgeResponse])
async def get_badges(user_id: UUID, db: Session = Depends(get_db)):
    return user_service.list_user_badges(db, user_id)
