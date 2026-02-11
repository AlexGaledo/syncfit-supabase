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
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
