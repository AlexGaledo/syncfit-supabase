"""
FastAPI application entry point
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.database import init_db
from app.middleware.cors import setup_cors
from app.api.v1 import health, auth, users, meal_plan, socials, workout



@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan events
    Handles startup and shutdown
    """
    # Startup: Initialize database
    print("🚀 Starting up application...")
    try:
        init_db()
        print("✅ Database initialized")
    except Exception as e:
        print(f"⚠️  Database initialization failed: {e}")
        print("   The API will start but database operations will fail.")
        print("   Please ensure PostgreSQL is running and DATABASE_URL is correct.")
    
    yield
    
    # Shutdown
    print("👋 Shutting down application...")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="FastAPI backend with SQLAlchemy and Supabase Auth",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Setup CORS
setup_cors(app)

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to SyncFit API",
        "version": settings.APP_VERSION,
        "docs": "/docs"
    }


# Include routers
app.include_router(health.router, prefix=settings.API_V1_PREFIX, tags=["Health"])
app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(users.router, prefix=settings.API_V1_PREFIX)
app.include_router(meal_plan.router, prefix=settings.API_V1_PREFIX)
app.include_router(socials.router, prefix=settings.API_V1_PREFIX)
app.include_router(workout.router, prefix=settings.API_V1_PREFIX)


if __name__ == "__main__":
    import uvicorn
    from app.config import settings

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
    )
