"""
Supabase client and authentication utilities.
Token verification is delegated to the Supabase SDK so algorithm
details (HS256 / RS256 / ES256) are handled automatically.
"""
from typing import Optional
import logging


from supabase import create_client, Client
from app.config import settings

logger = logging.getLogger(__name__)

# Shared Supabase client (initialised once at import time)
supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)


def verify_token(token: str) -> Optional[dict]:
    """
    Verify a Supabase JWT by calling auth.get_user().
    Returns the user payload dict on success, None on failure.
    """
    try:
        response = supabase.auth.get_user(token)
        user = response.user if response else None
        if user is None:
            logger.error("verify_token: get_user returned no user")
            return None
        # Return a dict that mirrors the JWT payload shape the rest of
        # the app expects (sub, email, role).
        return {
            "sub": user.id,
            "email": user.email,
            "role": user.role,
        }
    except Exception as e:
        logger.error("verify_token failed: %s", e)
        return None


def get_user_from_token(token: str) -> Optional[dict]:
    return verify_token(token)
