from enum import Enum
from functools import lru_cache
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


class Settings(BaseSettings):
    # Application Info
    APP_NAME: str = "FinEx - Financial Excellence"
    API_V1_PREFIX: str = "/api/v1"
    ENVIRONMENT: Environment = Environment.DEVELOPMENT

    # Database Settings
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/finex_db",
        description="Async database connection URL",
    )
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20

    # JWT & Auth
    JWT_SECRET_KEY: str = Field(
        default="finex-default-dev-secret-key-must-be-changed-in-prod-32chars",
        description="Secret key for signing JWT tokens",
    )
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Google OAuth
    GOOGLE_CLIENT_ID: Optional[str] = "placeholder-google-client-id"
    GOOGLE_CLIENT_SECRET: Optional[str] = "placeholder-google-client-secret"
    GOOGLE_REDIRECT_URI: str = "http://localhost:3000/auth/callback"

    # CORS
    ALLOWED_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:3000"]
    )

    # Provider Toggles
    MARKET_DATA_PROVIDER: str = "yfinance"
    LLM_PROVIDER: str = "mock"
    OPENAI_API_KEY: Optional[str] = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=True, extra="ignore")

    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def validate_jwt_secret(cls, v: str, info) -> str:
        env = info.data.get("ENVIRONMENT", Environment.DEVELOPMENT)
        if env == Environment.PRODUCTION:
            if not v or "default" in v.lower() or len(v) < 32:
                raise ValueError(
                    "Production requires a cryptographically strong JWT_SECRET_KEY of at least 32 characters."
                )
        return v

    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v: str, info) -> str:
        if not v or not v.strip():
            raise ValueError("DATABASE_URL is required and cannot be empty.")
        return v

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v):
        if isinstance(v, str):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return ["http://localhost:3000"]


@lru_cache()
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
