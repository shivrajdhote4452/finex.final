"""Pytest Fixtures for FinEx AI Module Tests.

Ensures consistent isolated test environment without external dependencies or live LLM calls.
"""

import pytest

from backend.app.config import get_settings


@pytest.fixture(autouse=True)
def configure_ai_test_environment(monkeypatch):
    """Ensure consistent isolated test environment without external dependencies."""
    monkeypatch.setenv("ENVIRONMENT", "testing")
    monkeypatch.setenv("MARKET_ALLOW_FIXTURES", "true")
    monkeypatch.setenv("GEMINI_API_KEY", "")
    monkeypatch.setenv("GROQ_API_KEY", "")
    monkeypatch.setenv("LLM_PROVIDER", "offline")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
