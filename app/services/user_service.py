"""User domain logic. Thin handlers in routers delegate here."""
from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.user import (
    User,
    User_Profile,
    User_Supplements,
    User_Limitations,
    Weight_Loss_Progress,
    UserType,
)
from app.models.item import User_Badges
from app.schemas.user import (
    UserCreateRequest,
    UserUpdate,
    UserProfileUpdate,
    UserSupplementCreate,
    UserLimitationCreate,
    WeightLossProgressBase,
)
from app.services import auth_service


# ---- Users ----

def list_users(db: Session, skip: int, limit: int, current_user: dict) -> List[User]:
    auth_service.assert_admin(db, current_user)
    return db.query(User).offset(skip).limit(limit).all()


def get_or_create_for_supabase(
    db: Session,
    current_user: dict,
    extra: Optional[UserCreateRequest],
) -> User:
    supabase_user_id = current_user["sub"]
    email = current_user["email"]

    existing = db.query(User).filter(User.supabase_user_id == supabase_user_id).first()
    if existing:
        return existing

    payload = extra.model_dump() if extra else {}
    user = User(supabase_user_id=supabase_user_id, email=email, **payload)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user(db: Session, user_id: UUID, payload: UserUpdate, current_user: dict) -> User:
    user = auth_service.get_user_or_404(db, user_id)
    auth_service.assert_self_or_admin(db, user, current_user)

    if payload.role is not None and not auth_service.is_admin(db, current_user["sub"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can change user roles",
        )

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)
    return user


def delete_user(db: Session, user_id: UUID, current_user: dict) -> None:
    user = auth_service.get_user_or_404(db, user_id)
    auth_service.assert_self_or_admin(db, user, current_user)
    db.delete(user)
    db.commit()


def list_trainees(db: Session, skip: int, limit: int) -> List[User]:
    return (
        db.query(User)
        .filter(User.type == UserType.trainee)
        .offset(skip)
        .limit(limit)
        .all()
    )


# ---- Profile ----

def get_profile(db: Session, user_id: UUID) -> User_Profile:
    user = auth_service.get_user_or_404(db, user_id)
    if not user.profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    return user.profile


def create_profile(
    db: Session, user_id: UUID, payload: UserProfileUpdate, current_user: dict
) -> User_Profile:
    user = auth_service.get_user_or_404(db, user_id)
    auth_service.assert_self_or_admin(db, user, current_user)

    existing = db.query(User_Profile).filter(User_Profile.user_id == user.id).first()
    if existing:
        return existing

    profile = User_Profile(user_id=user.id, **payload.model_dump(exclude_unset=True))
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def update_profile(
    db: Session, user_id: UUID, payload: UserProfileUpdate, current_user: dict
) -> User_Profile:
    user = auth_service.get_user_or_404(db, user_id)
    auth_service.assert_self_or_admin(db, user, current_user)

    if not user.profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found. Create it first.",
        )

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(user.profile, field, value)

    db.commit()
    db.refresh(user.profile)
    return user.profile


# ---- Supplements ----

def list_supplements(db: Session, user_id: UUID, current_user: dict) -> List[User_Supplements]:
    user = auth_service.get_user_or_404(db, user_id)
    auth_service.assert_self_or_admin(db, user, current_user)
    return user.profile.supplements if user.profile else []


def add_supplement(
    db: Session, user_id: UUID, payload: UserSupplementCreate, current_user: dict
) -> User_Supplements:
    user = auth_service.get_user_or_404(db, user_id)
    auth_service.assert_self_or_admin(db, user, current_user)

    if not user.profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found. Create it first.",
        )

    supplement = User_Supplements(
        user_id=user.profile.id,
        supplement_name=payload.supplement_name,
    )
    db.add(supplement)
    db.commit()
    db.refresh(supplement)
    return supplement


def remove_supplement(
    db: Session, user_id: UUID, supplement_id: UUID, current_user: dict
) -> None:
    user = auth_service.get_user_or_404(db, user_id)
    auth_service.assert_self_or_admin(db, user, current_user)

    if user.profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")

    supplement = (
        db.query(User_Supplements)
        .filter(
            User_Supplements.id == supplement_id,
            User_Supplements.user_id == user.profile.id,
        )
        .first()
    )
    if not supplement:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplement not found")

    db.delete(supplement)
    db.commit()


# ---- Limitations ----

def list_limitations(db: Session, user_id: UUID, current_user: dict) -> List[User_Limitations]:
    user = auth_service.get_user_or_404(db, user_id)
    auth_service.assert_self_or_admin(db, user, current_user)
    return user.profile.limitations if user.profile else []


def add_limitation(
    db: Session, user_id: UUID, payload: UserLimitationCreate, current_user: dict
) -> User_Limitations:
    user = auth_service.get_user_or_404(db, user_id)
    auth_service.assert_self_or_admin(db, user, current_user)

    if not user.profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found. Create it first.",
        )

    limitation = User_Limitations(
        user_id=user.profile.id,
        limitation_description=payload.limitation_description,
    )
    db.add(limitation)
    db.commit()
    db.refresh(limitation)
    return limitation


def remove_limitation(
    db: Session, user_id: UUID, limitation_id: UUID, current_user: dict
) -> None:
    user = auth_service.get_user_or_404(db, user_id)
    auth_service.assert_self_or_admin(db, user, current_user)

    if user.profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")

    limitation = (
        db.query(User_Limitations)
        .filter(
            User_Limitations.id == limitation_id,
            User_Limitations.user_id == user.profile.id,
        )
        .first()
    )
    if not limitation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Limitation not found")

    db.delete(limitation)
    db.commit()


# ---- Weight progress ----

def list_weight_progress(
    db: Session, user_id: UUID, skip: int, limit: int, current_user: dict
) -> List[Weight_Loss_Progress]:
    user = auth_service.get_user_or_404(db, user_id)
    auth_service.assert_self_or_admin(db, user, current_user)
    return (
        db.query(Weight_Loss_Progress)
        .filter(Weight_Loss_Progress.user_id == user.id)
        .order_by(Weight_Loss_Progress.date.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def log_weight(
    db: Session, user_id: UUID, payload: WeightLossProgressBase, current_user: dict
) -> Weight_Loss_Progress:
    user = auth_service.get_user_or_404(db, user_id)
    auth_service.assert_self_or_admin(db, user, current_user)

    entry = Weight_Loss_Progress(user_id=user.id, weight=payload.weight)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


# ---- Badges ----

def list_user_badges(db: Session, user_id: UUID) -> List[User_Badges]:
    user = auth_service.get_user_or_404(db, user_id)
    return db.query(User_Badges).filter(User_Badges.user_id == user.id).all()
