import os
import sys
from enum import Enum
from functools import lru_cache
from typing import List, Optional
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def sanitize_asyncpg_url(url_str: str) -> str:
    url_str = url_str.strip()
    if url_str.startswith("postgres://"):
        url_str = url_str.replace("postgres://", "postgresql+asyncpg://", 1)
    elif url_str.startswith("postgresql://") and not url_str.startswith("postgresql+"):
        url_str = url_str.replace("postgresql://", "postgresql+asyncpg://", 1)

    if "sqlite" in url_str:
        return url_str

    try:
        parsed = urlparse(url_str)
        allowed_params = {
            "ssl",
            "timeout",
            "command_timeout",
            "statement_cache_size",
            "prepared_statement_cache_size",
        }
        query_params = parse_qs(parsed.query)
        if "sslmode" in query_params and "ssl" not in query_params:
            query_params["ssl"] = query_params.pop("sslmode")
        sanitized_params = {
            k: v[0] if isinstance(v, list) else v for k, v in query_params.items() if k in allowed_params
        }
        sanitized_query = urlencode(sanitized_params)
        return urlunparse(parsed._replace(query=sanitized_query))
    except Exception:
        return url_str


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
    OWNER_EMAIL: str = Field(
        default="shivrajdhote4452@gmail.com",
        description="Platform owner email authorized for sandbox visibility and controls",
    )

    # Google OAuth
    GOOGLE_CLIENT_ID: Optional[str] = Field(
        default="71626572471-2333p55kgim64b3738oabca9l9ss9th0.apps.googleusercontent.com",
        description="Google OAuth web client ID",
    )
    GOOGLE_CLIENT_SECRET: Optional[str] = "placeholder-google-client-secret"
    GOOGLE_REDIRECT_URI: str = "http://localhost:3000/auth/callback"

    # Email & SMTP Settings
    SMTP_HOST: Optional[str] = Field(default=None, description="SMTP server hostname for email delivery")
    SMTP_PORT: int = Field(default=587, description="SMTP server port (e.g. 587 for STARTTLS, 465 for SSL)")
    SMTP_USER: Optional[str] = Field(default=None, description="SMTP server username")
    SMTP_PASSWORD: Optional[str] = Field(default=None, description="SMTP server password")
    SMTP_USE_TLS: bool = Field(default=True, description="Enable STARTTLS encryption for SMTP")
    EMAILS_FROM_EMAIL: str = Field(default="noreply@finexai.tech", description="Sender email address")
    EMAILS_FROM_NAME: str = Field(default="FinEx Financial Excellence", description="Sender display name")
    FRONTEND_URL: str = Field(default="http://localhost:3000", description="Frontend base URL for auth links")
    EMAIL_VERIFICATION_EXPIRE_HOURS: int = Field(default=24, description="Email verification link lifetime in hours")
    PASSWORD_RESET_EXPIRE_MINUTES: int = Field(default=30, description="Password reset link lifetime in minutes")

    # CORS
    ALLOWED_ORIGINS: List[str] = Field(
        default=[
            "http://localhost:3000",
            "http://localhost:5173",
            "http://127.0.0.1:3000",
            "http://localhost:8085",
            "http://127.0.0.1:8085",
            "http://localhost:8080",
            "http://127.0.0.1:8080",
        ]
    )

    # Provider Toggles & Modes
    MARKET_DATA_PROVIDER: str = "yfinance"
    MARKET_DATA_MODE: str = Field(
        default="INDIA_HISTORICAL_REPLAY",
        description="Market data mode: INDIA_HISTORICAL_REPLAY, US_ALPACA_PAPER, INDIAN_LIVE_DATA",
    )
    MARKET_ALLOW_FIXTURES: bool = Field(
        default=False, description="Allow fallback to static fixtures only in test/demo environments"
    )
    SEBI_EDUCATIONAL_LAG_DAYS: int = 30

    # AI Assistant Configuration (Groq only)
    LLM_PROVIDER: str = "groq"
    GROQ_API_KEY: Optional[str] = Field(default=None, description="Groq API Key")
    GROQ_MODEL: str = Field(default="openai/gpt-oss-120b", description="Configured Groq model ID")
    GROQ_TIMEOUT: float = Field(default=8.0, description="Groq API timeout in seconds")
    OPENAI_API_KEY: Optional[str] = None

    # Angel One SmartAPI Configuration
    ANGEL_API_KEY: Optional[str] = Field(default=None, description="Angel One SmartAPI Key")
    ANGEL_CLIENT_ID: Optional[str] = Field(default=None, description="Angel One Client ID")
    ANGEL_MPIN: Optional[str] = Field(default=None, description="Angel One 4-digit MPIN")
    ANGEL_TOTP_SECRET: Optional[str] = Field(default=None, description="Angel One TOTP base32 secret")

    # Optional Alpaca Paper Trading (US_ALPACA_PAPER mode)
    ALPACA_API_KEY: Optional[str] = None
    ALPACA_SECRET_KEY: Optional[str] = None
    ALPACA_BASE_URL: str = "https://paper-api.alpaca.markets"
    ALPACA_DATA_URL: str = "https://data.alpaca.markets"

    model_config = SettingsConfigDict(
        env_file=[".env", "../.env"], env_file_encoding="utf-8", case_sensitive=True, extra="ignore"
    )

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
        sanitized = sanitize_asyncpg_url(v)
        env = info.data.get("ENVIRONMENT", Environment.DEVELOPMENT)

        if env == Environment.PRODUCTION:
            if (
                "localhost" in sanitized.lower()
                or "127.0.0.1" in sanitized.lower()
                or "postgres:postgres@" in sanitized
            ):
                raise ValueError(
                    "Production requires a valid external DATABASE_URL provided via environment variables."
                )

        is_test = env == Environment.TESTING or "pytest" in sys.modules or "PYTEST_CURRENT_TEST" in os.environ
        if is_test:
            # Prevent remote database from silently becoming the test database
            if any(
                m in sanitized.lower()
                for m in ["neon.tech", "ep-gentle-frog", "aws.neon.tech", "render.com", "supabase.co"]
            ):
                from dotenv import dotenv_values

                _backend_env = dotenv_values("backend/.env")
                _local_url = os.environ.get("TEST_DATABASE_URL") or _backend_env.get(
                    "DATABASE_URL", "postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/finex_test_db"
                )
                if "test" not in _local_url.rsplit("/", 1)[-1]:
                    _local_url = _local_url.rsplit("/", 1)[0] + "/finex_test_db"
                return _local_url
        return sanitized

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v):
        origins = []
        if isinstance(v, str):
            try:
                import json

                parsed = json.loads(v)
                if isinstance(parsed, list):
                    origins = [str(i).strip() for i in parsed if str(i).strip()]
            except Exception:
                origins = [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            origins = [str(i).strip() for i in v if str(i).strip()]
        else:
            origins = ["http://localhost:3000"]

        standard_origins = [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:8085",
            "http://127.0.0.1:8085",
            "http://localhost:8080",
            "http://127.0.0.1:8080",
            "https://www.finexai.tech",
            "https://finexai.tech",
        ]
        for d in standard_origins:
            if d not in origins:
                origins.append(d)
        return origins


@lru_cache()
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
