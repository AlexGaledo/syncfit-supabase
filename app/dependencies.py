"""
Common dependencies for FastAPI routes
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.supabase_client import verify_token, get_user_from_token

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> dict:
    """
    Dependency to get current authenticated user from Supabase token
    
    Usage:
        @router.get("/protected")
        def protected_route(current_user: dict = Depends(get_current_user)):
            user_id = current_user["sub"]
            ...
    """
    token = credentials.credentials
    
    # Verify token with Supabase
    payload = verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return payload


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
) -> Optional[dict]:
    """
    Optional authentication - returns None if no token provided
    
    Usage:
        @router.get("/public-or-private")
        def route(current_user: Optional[dict] = Depends(get_current_user_optional)):
            if current_user:
                # User is authenticated
                ...
            else:
                # Anonymous access
                ...
    """
    if not credentials:
        return None
    
    token = credentials.credentials
    payload = verify_token(token)
    return payload
