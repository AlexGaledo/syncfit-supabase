"""
Configuration settings for the application
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
from dotenv import load_dotenv
import os

load_dotenv()  # Load environment variables from .env file


class Settings(BaseSettings):
    """Application settings"""
    
    # App Settings
    APP_NAME: str = "SyncFit Backend API"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    
    # Database Settings
    DATABASE_URL: str = os.getenv("DATABASE_URL") or ''
    
    # Supabase Settings
    SUPABASE_URL: str = os.getenv("SUPABASE_URL") or ''
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY") or ''
    SUPABASE_JWT_SECRET: str = os.getenv("SUPABASE_JWT_SECRET") or ''
    
    # CORS Settings
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:8081"
    
    # AI/Gemini settings
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY") or ''
    
    # API Settings
    API_V1_PREFIX: str = "/api/v1"
    
    @property
    def cors_origins(self) -> list[str]:
        """Parse ALLOWED_ORIGINS into a list"""
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


# Global settings instance
settings = Settings()
