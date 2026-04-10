"""
FastAPI application entry point
"""
from app import create_app

app = create_app()

if __name__ == "__main__":
    import uvicorn
    from app.config import settings

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
    )
