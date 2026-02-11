"""
Authentication middleware for Supabase
"""
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Optional

from app.supabase_client import verify_token


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Optional middleware to validate Supabase tokens globally
    Note: Generally, it's better to use dependencies (get_current_user) per route
    """
    
    async def dispatch(self, request: Request, call_next):
        # Skip auth for public endpoints
        public_paths = ["/", "/docs", "/redoc", "/openapi.json", "/api/v1/health"]
        
        if request.url.path in public_paths:
            return await call_next(request)
        
        # Get token from Authorization header
        auth_header = request.headers.get("Authorization")
        
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            payload = verify_token(token)
            
            if payload:
                # Attach user info to request state
                request.state.user = payload
            else:
                # Token is invalid
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication credentials"
                )
        
        response = await call_next(request)
        return response
