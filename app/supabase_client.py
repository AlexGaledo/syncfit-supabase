"""
Supabase authentication utilities (lightweight - no SDK needed)
"""
from jose import jwt, JWTError
from typing import Optional
import httpx

from app.config import settings


def verify_token(token: str) -> Optional[dict]:
    """
    Verify JWT token from Supabase
    
    Args:
        token: JWT token string
        
    Returns:
        Decoded token payload if valid, None otherwise
    """
    try:
        payload = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            options={"verify_aud": False}
        )
        return payload
    except JWTError:
        return None


async def get_user_from_supabase(user_id: str) -> Optional[dict]:
    """
    Get user information from Supabase API
    
    Args:
        user_id: User ID from JWT token
        
    Returns:
        User data if successful, None otherwise
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.SUPABASE_URL}/auth/v1/user",
                headers={
                    "apikey": settings.SUPABASE_KEY,
                    "Authorization": f"Bearer {settings.SUPABASE_KEY}"
                }
            )
            if response.status_code == 200:
                return response.json()
            return None
    except Exception:
        return None


def get_user_from_token(token: str) -> Optional[dict]:
    """
    Get user information from token payload
    (No API call needed - info is in the JWT)
    
    Args:
        token: JWT token string
        
    Returns:
        User data from token payload if valid, None otherwise
    """
    return verify_token(token)
