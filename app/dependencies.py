"""
Common dependencies for FastAPI routes
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.models.user import User
from app.supabase_client import verify_token, get_user_from_token

# security = HTTPBearer()


# async def get_current_user_real(
#     credentials: HTTPAuthorizationCredentials = Depends(security),
#     db: Session = Depends(get_db)
# ) -> dict:
#     """
#     Dependency to get current authenticated user from Supabase token
    
#     Usage:
#         @router.get("/protected")
#         def protected_route(current_user: dict = Depends(get_current_user)):
#             user_id = current_user["sub"]
#             ...
#     """
#     token = credentials.credentials
    
#     # Verify token with Supabase
#     payload = verify_token(token)
#     if not payload:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Invalid authentication credentials",
#             headers={"WWW-Authenticate": "Bearer"},
#         )
    
#     return payload


async def get_current_user() -> dict:                                                                                                                                                      
      return {"sub": "dev-bypass", "email": "dev@local", "role": "authenticated"}


def get_current_db_user(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
) -> User:
    """
    Reusable dependency to get the full User object from the database
    based on the JWT token's 'sub' claim.
    Ford Note: Added this because get_current_user doesn't return the full user object, and we often need to access user fields from the database in our routes. 
    """
    supabase_user_id = current_user.get("sub")
    if not supabase_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing 'sub' claim.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    db_user = db.query(User).filter(User.supabase_user_id == supabase_user_id).first()
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in internal database. Please create a user profile first."
        )
    return db_user