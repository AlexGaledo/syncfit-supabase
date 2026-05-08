"""Auth/permission helpers shared across services."""
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.user import User, UserRole as UserRoleModel


def get_user_or_404(db: Session, user_id: UUID) -> User:
    user = db.query(User).filter(User.supabase_user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


def is_admin(db: Session, supabase_user_id: str) -> bool:
    return (
        db.query(User.id)
        .filter(
            User.supabase_user_id == supabase_user_id,
            User.role == UserRoleModel.admin,
        )
        .first()
        is not None
    )


def assert_admin(db: Session, current_user: dict) -> None:
    if not is_admin(db, current_user["sub"]):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")


def assert_self_or_admin(db: Session, user: User, current_user: dict) -> None:
    """Raise 403 unless caller owns the account or is admin."""
    sub = current_user["sub"]
    is_owner = (
        db.query(User.id)
        .filter(User.supabase_user_id == sub, User.id == user.id)
        .first()
        is not None
    )
    if is_owner or is_admin(db, sub):
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You can only access your own data",
    )
