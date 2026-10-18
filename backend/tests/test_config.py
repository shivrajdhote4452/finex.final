import pytest
from backend.app.config import Environment, Settings
from pydantic import ValidationError


def test_default_development_settings(monkeypatch):
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    settings = Settings(_env_file=None)
    assert settings.ENVIRONMENT == Environment.DEVELOPMENT
    assert settings.API_V1_PREFIX == "/api/v1"
    assert "localhost" in settings.ALLOWED_ORIGINS[0]
    assert settings.JWT_ALGORITHM == "HS256"


def test_production_rejects_weak_or_default_secret():
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            ENVIRONMENT=Environment.PRODUCTION,
            JWT_SECRET_KEY="short-key",
            DATABASE_URL="postgresql+asyncpg://prod_user:prod_pass@db.internal:5432/finex",
        )
    assert "at least 32 characters" in str(exc_info.value)


def test_production_accepts_strong_secret():
    settings = Settings(
        ENVIRONMENT=Environment.PRODUCTION,
        JWT_SECRET_KEY="very-strong-production-cryptographic-key-1234567890",
        DATABASE_URL="postgresql+asyncpg://prod_user:prod_pass@db.internal:5432/finex",
    )
    assert settings.ENVIRONMENT == Environment.PRODUCTION


def test_empty_database_url_rejected():
    with pytest.raises(ValidationError):
        Settings(DATABASE_URL="")


def test_cors_origins_assembled_from_string():
    settings = Settings(ALLOWED_ORIGINS="https://finex.app, https://admin.finex.app")
    assert "https://finex.app" in settings.ALLOWED_ORIGINS
    assert "https://admin.finex.app" in settings.ALLOWED_ORIGINS
