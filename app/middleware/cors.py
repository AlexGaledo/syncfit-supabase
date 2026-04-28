"""
CORS middleware configuration
"""
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI

from app.config import settings


def setup_cors(app: FastAPI) -> None:
    """
    Setup CORS middleware for the application
    
    Args:
        app: FastAPI application instance
    """
    app.add_middleware(
        CORSMiddleware,
        # Use the parsed list from settings (`cors_origins`) so a single
        # string like "*" isn't treated as an iterable of characters.
        allow_origins=settings.cors_origins,
        # Note: if `cors_origins` is ["*"] and you set `allow_credentials=True`,
        # browsers will reject the wildcard for credentialed requests. If you
        # need credentials with multiple origins, list them explicitly in
        # `ALLOWED_ORIGINS` instead of using "*".
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
