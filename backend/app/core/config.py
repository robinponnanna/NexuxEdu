import os
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "NexusEdu ERP & SafeTransit"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Security
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "nexusedu-super-secret-jwt-key-2026-secure-hackathon")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 # 24 hours
    
    # Database (defaults to persistent SQLite in backend/campus.db)
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./campus.db")
    
    # LLM Inference (Optional external API keys, fallback to local deterministic RAG)
    GROQ_API_KEY: Optional[str] = os.getenv("GROQ_API_KEY", None)
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY", None)
    
    # Telemetry
    TELEMETRY_INTERVAL_SECONDS: float = 3.0
    GEOFENCE_RADIUS_METERS: float = 500.0

    class Config:
        case_sensitive = True

settings = Settings()
