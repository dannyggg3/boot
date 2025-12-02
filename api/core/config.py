"""
Configuración de la aplicación.
"""

from pydantic_settings import BaseSettings
from typing import List
import os

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/sath_platform"

    # Redis
    REDIS_URL: str = "redis://localhost:6379"

    # JWT
    JWT_SECRET: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_MINUTES: int = 15
    JWT_REFRESH_EXPIRATION_DAYS: int = 7

    # Encryption (para API keys)
    ENCRYPTION_KEY: str = "your-encryption-key-change-in-production"

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]

    # Stripe
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""

    # Paths
    TENANTS_PATH: str = "/app/tenants"

    # Bot Image
    BOT_IMAGE: str = "sath-bot:latest"

    class Config:
        env_file = ".env"
        extra = "allow"

settings = Settings()
