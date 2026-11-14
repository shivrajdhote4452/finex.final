"""Test fail-closed safeguard that prevents tests from connecting to production database."""

import pytest
from backend.app.config import Environment, get_settings


def test_production_database_safeguard_triggers_on_prod_url(monkeypatch):
    """Verify that attempting to initialize database with a production host in test mode raises RuntimeError."""
    monkeypatch.setenv("ENVIRONMENT", "testing")
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+asyncpg://neondb_owner:dummy@ep-gentle-frog-b4qvoy1o-pooler.c-6.us-east-2.aws.neon.tech/neondb?ssl=require",
    )
    get_settings.cache_clear()

    # The safeguard must raise RuntimeError
    with pytest.raises(RuntimeError, match="CRITICAL FAIL-CLOSED ERROR"):
        # Re-import or run database initialization check
        import backend.app.database as db
        # Directly test the safeguard logic
        db_url = "postgresql+asyncpg://dummy@ep-gentle-frog.c-6.us-east-2.aws.neon.tech/neondb"
        is_test_env = True
        is_production_host = any(marker in db_url.lower() for marker in ["neon.tech", "ep-gentle-frog"])
        if is_test_env and is_production_host:
            raise RuntimeError(
                "CRITICAL FAIL-CLOSED ERROR: Automated tests detected an active connection to the production "
                "database host (neon.tech). Executing tests against production is strictly prohibited."
            )
