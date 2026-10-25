"""Pytest Shared Fixtures for FinEx Backend Integration Tests.

Task ID: CH-01, CH-02
Provides cryptographically signed JWT authorization headers, preventing
runtime mock-token backdoors.
"""

import pytest
from backend.app.config import get_settings
from backend.app.factory import create_app
from backend.app.routers.auth import create_access_token


@pytest.fixture(autouse=True)
def configure_test_environment(monkeypatch):
    """Ensure consistent isolated test environment without external dependencies."""
    monkeypatch.setenv("ENVIRONMENT", "testing")
    monkeypatch.setenv("MARKET_ALLOW_FIXTURES", "true")
    monkeypatch.setenv("GEMINI_API_KEY", "")
    monkeypatch.setenv("GROQ_API_KEY", "")
    monkeypatch.setenv("LLM_PROVIDER", "offline")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
def auth_headers():
    """Valid signed JWT for primary user Shivraj Dhote."""
    token = create_access_token(
        user_id="usr-shivraj-001",
        email="shivraj.dhote@finex.internal",
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
