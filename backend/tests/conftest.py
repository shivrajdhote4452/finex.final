"""Pytest Shared Fixtures for FinEx Backend Integration Tests.

Task ID: CH-01, CH-02
Provides cryptographically signed JWT authorization headers, preventing
runtime mock-token backdoors.
"""

import os
import sys

# Fail-closed test environment setup: Ensure tests never point to production
from dotenv import dotenv_values
_backend_env = dotenv_values("backend/.env")
_local_url = _backend_env.get("DATABASE_URL", "postgresql+asyncpg://postgres:Shivraj4452@127.0.0.1:5432/finex_db")
DEFAULT_TEST_DB_URL = os.environ.get("TEST_DATABASE_URL") or (_local_url.rsplit("/", 1)[0] + "/finex_test_db")

current_db = os.environ.get("DATABASE_URL", "")
if not current_db or any(k in current_db.lower() for k in ["neon.tech", "ep-gentle-frog", "aws.neon.tech"]):
    os.environ["DATABASE_URL"] = DEFAULT_TEST_DB_URL
os.environ["ENVIRONMENT"] = "testing"

import pytest
from backend.app.config import get_settings
from backend.app.factory import create_app
from backend.app.routers.auth import create_access_token


@pytest.fixture(autouse=True)
def configure_test_environment(monkeypatch):
    """Ensure consistent isolated test environment without external dependencies."""
    monkeypatch.setenv("ENVIRONMENT", "testing")
    monkeypatch.setenv("MARKET_ALLOW_FIXTURES", "true")
    monkeypatch.setenv("GROQ_API_KEY", "")
    monkeypatch.setenv("LLM_PROVIDER", "offline")
    monkeypatch.setenv("DATABASE_URL", DEFAULT_TEST_DB_URL)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
def auth_headers():
    """Valid signed JWT for primary user Shivraj Dhote (Platform Owner)."""
    token = create_access_token(
        user_id="usr-shivraj-001",
        email="shivrajdhote4452@gmail.com",
        name="Shivraj Dhote",
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def other_user_headers():
    """Valid signed JWT for second tenant user to test two-user authorization."""
    token = create_access_token(
        user_id="usr-other-002",
        email="other.investor@finex.internal",
        name="Other Investor",
    )
    return {"Authorization": f"Bearer {token}"}
