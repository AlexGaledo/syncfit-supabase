"""
FastAPI application package
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.config import settings
from app.database import init_db
from app.middleware.cors import setup_cors
from app.api.v1 import health, auth, users, meal_plan, socials
from app.api.v1.workout import workout_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan events
    Handles startup and shutdown
    """
    print("🚀 Starting up application...")
    try:
        init_db()
        print("✅ Database initialized")
    except Exception as e:
        print(f"⚠️  Database initialization failed: {e}")
        print("   The API will start but database operations will fail.")
        print("   Please ensure PostgreSQL is running and DATABASE_URL is correct.")

    yield

    print("👋 Shutting down application...")


def create_app() -> FastAPI:
    """
    Application factory — creates and configures the FastAPI instance.
    """
    application = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="FastAPI backend with SQLAlchemy and Supabase Auth",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    setup_cors(application)

    @application.get("/")
    async def root():
        """Root endpoint"""
        return {
            "message": "Welcome to SyncFit API",
            "version": settings.APP_VERSION,
            "docs": "/docs",
        }

    application.include_router(health.router, prefix=settings.API_V1_PREFIX, tags=["Health"])
    application.include_router(auth.router, prefix=settings.API_V1_PREFIX)
    application.include_router(users.router, prefix=settings.API_V1_PREFIX)
    application.include_router(meal_plan.router, prefix=settings.API_V1_PREFIX)
    application.include_router(socials.socials_router, prefix=settings.API_V1_PREFIX)
    application.include_router(workout_router, prefix=settings.API_V1_PREFIX)

    return application
