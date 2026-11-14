"""Comprehensive Integration Tests for Fail-Closed Isolated Test Database Policy.

Verifies:
1. Strict allowlist policy: Only explicitly approved local test databases (with 'test' in the db name) or SQLite are permitted.
2. Immediate fail-closed rejection: Remote hosts (Neon, AWS, Render, Supabase), non-local IPs,
   and local non-test databases (e.g. finex_db) raise RuntimeError without opening connections.
"""

import pytest
from backend.app.database import validate_test_database_allowlist


def test_allowlist_rejects_remote_neon_host():
    """Verify that remote Neon PostgreSQL host raises fatal fail-closed RuntimeError."""
    url = "postgresql+asyncpg://neondb_owner:dummy@ep-gentle-frog-b4qvoy1o-pooler.c-6.us-east-2.aws.neon.tech/neondb?ssl=require"
    with pytest.raises(RuntimeError, match="remote/cloud database host"):
        validate_test_database_allowlist(url)


def test_allowlist_rejects_remote_aws_rds_host():
    """Verify that generic cloud host (e.g. AWS RDS) raises fatal fail-closed RuntimeError."""
    url = "postgresql+asyncpg://admin:pass@db-instance.123456.us-east-1.rds.amazonaws.com:5432/test_db"
    with pytest.raises(RuntimeError, match="remote/cloud database host"):
        validate_test_database_allowlist(url)


def test_allowlist_rejects_remote_render_host():
    """Verify that Render PostgreSQL host raises fatal fail-closed RuntimeError."""
    url = "postgresql+asyncpg://user:pass@dpg-abc123-a.oregon-postgres.render.com/finex_test_db"
    with pytest.raises(RuntimeError, match="remote/cloud database host"):
        validate_test_database_allowlist(url)


def test_allowlist_rejects_local_non_test_database():
    """Verify that local development database (without 'test' in name) is blocked to prevent wiping dev data."""
    url = "postgresql+asyncpg://postgres:pass@127.0.0.1:5432/finex_db"
    with pytest.raises(RuntimeError, match="does not contain 'test' in its name"):
        validate_test_database_allowlist(url)


def test_allowlist_rejects_non_local_network_ip():
    """Verify that network IP address is rejected."""
    url = "postgresql+asyncpg://postgres:pass@192.168.1.100:5432/finex_test_db"
    with pytest.raises(RuntimeError, match="non-local host '192.168.1.100'"):
        validate_test_database_allowlist(url)


def test_allowlist_rejects_empty_url():
    """Verify that empty URL raises RuntimeError."""
    with pytest.raises(RuntimeError, match="empty or invalid DATABASE_URL"):
        validate_test_database_allowlist("")


def test_allowlist_accepts_local_test_database():
    """Verify that approved local test database with 'test' in its name passes validation."""
    url = "postgresql+asyncpg://postgres:pass@127.0.0.1:5432/finex_test_db"
    # Should not raise any exception
    validate_test_database_allowlist(url)


def test_allowlist_accepts_disposable_test_database():
    """Verify that disposable migration test databases (e.g. finex_test_clean_uuid) pass validation."""
    url = "postgresql+asyncpg://postgres:pass@localhost:5432/finex_test_clean_8f3a92b1"
    # Should not raise any exception
    validate_test_database_allowlist(url)


def test_allowlist_accepts_sqlite():
    """Verify that in-memory or file-based SQLite test databases pass validation."""
    validate_test_database_allowlist("sqlite+aiosqlite:///:memory:")
    validate_test_database_allowlist("sqlite:///test.db")
    validate_test_database_allowlist("sqlite+aiosqlite:///./finex_test.db")


def test_allowlist_rejects_remote_postgres_with_sqlite_in_username():
    """Verify that remote PostgreSQL URL with 'sqlite' in username is rejected."""
    url = "postgresql+asyncpg://sqlite:pass@remote.neon.tech/prod"
    with pytest.raises(RuntimeError, match="remote/cloud database host"):
        validate_test_database_allowlist(url)


def test_allowlist_rejects_remote_postgres_with_sqlite_in_host():
    """Verify that remote PostgreSQL URL with 'sqlite' in hostname is rejected."""
    url = "postgresql+asyncpg://user:pass@sqlite-cloud.rds.amazonaws.com/test_db"
    with pytest.raises(RuntimeError, match="remote/cloud database host"):
        validate_test_database_allowlist(url)


def test_allowlist_rejects_remote_postgres_with_sqlite_in_path():
    """Verify that remote PostgreSQL URL with 'sqlite' in database path is rejected."""
    url = "postgresql+asyncpg://admin:pass@remote-cloud.com/sqlite_db"
    with pytest.raises(RuntimeError, match="non-local host"):
        validate_test_database_allowlist(url)


def test_allowlist_rejects_remote_postgres_with_sqlite_in_query():
    """Verify that remote PostgreSQL URL with 'sqlite' in query string is rejected."""
    url = "postgresql+asyncpg://admin:pass@remote-cloud.com/test_db?engine=sqlite"
    with pytest.raises(RuntimeError, match="non-local host"):
        validate_test_database_allowlist(url)


def test_allowlist_rejects_local_postgres_with_sqlite_in_non_test_path():
    """Verify that local PostgreSQL URL with 'sqlite' in a non-test path is rejected."""
    url = "postgresql+asyncpg://postgres:pass@127.0.0.1:5432/sqlite_prod"
    with pytest.raises(RuntimeError, match="does not contain 'test' in its name"):
        validate_test_database_allowlist(url)


def test_allowlist_rejects_local_postgres_with_sqlite_in_username_for_non_test_db():
    """Verify that local PostgreSQL URL with 'sqlite' in username for non-test db is rejected."""
    url = "postgresql+asyncpg://sqlite:pass@127.0.0.1:5432/finex_db"
    with pytest.raises(RuntimeError, match="does not contain 'test' in its name"):
        validate_test_database_allowlist(url)


def test_allowlist_rejects_non_test_sqlite_files():
    """Verify that file-based SQLite databases without 'test' in the filename are rejected."""
    with pytest.raises(RuntimeError, match="does not contain 'test' in its name"):
        validate_test_database_allowlist("sqlite+aiosqlite:///production.db")
    with pytest.raises(RuntimeError, match="does not contain 'test' in its name"):
        validate_test_database_allowlist("sqlite:///users_data.db")


def test_allowlist_rejects_malformed_and_unsupported_schemes():
    """Verify that unsupported schemes (mysql, mongo, ftp) or garbage strings are rejected."""
    with pytest.raises(RuntimeError, match="Unsupported or unapproved database scheme"):
        validate_test_database_allowlist("mysql://root:pass@localhost:3306/test_db")
    with pytest.raises(RuntimeError, match="Unsupported or unapproved database scheme"):
        validate_test_database_allowlist("mongodb://127.0.0.1:27017/test_db")
    with pytest.raises(RuntimeError, match="Unsupported or unapproved database scheme"):
        validate_test_database_allowlist("ftp://127.0.0.1/test_db")
    with pytest.raises(RuntimeError, match="Unsupported or unapproved database scheme"):
        validate_test_database_allowlist("not_a_valid_url")


def test_direct_create_async_engine_call_intercepted_and_blocked():
    """Verify that direct create_async_engine calls cannot bypass the safety check."""
    import sqlalchemy.ext.asyncio
    url = "postgresql+asyncpg://admin:pass@ep-gentle-frog-remote.neon.tech/prod"
    with pytest.raises(RuntimeError, match="remote/cloud database host"):
        sqlalchemy.ext.asyncio.create_async_engine(url)


def test_direct_create_engine_sync_call_intercepted_and_blocked():
    """Verify that direct create_engine (sync) calls cannot bypass the safety check."""
    import sqlalchemy
    url = "postgresql://admin:pass@remote-cloud.com/test_db"
    with pytest.raises(RuntimeError, match="non-local host"):
        sqlalchemy.create_engine(url)


def test_maintenance_database_access_enforcement():
    """Verify that maintenance databases require explicit allow_maintenance flag on local host only."""
    url_local = "postgresql+asyncpg://postgres:pass@127.0.0.1:5432/postgres"
    # Fails by default
    with pytest.raises(RuntimeError, match="does not contain 'test' in its name"):
        validate_test_database_allowlist(url_local, allow_maintenance=False)

    # Passes with allow_maintenance on local host
    validate_test_database_allowlist(url_local, allow_maintenance=True)

    # Fails even with allow_maintenance on remote cloud host
    url_remote = "postgresql+asyncpg://postgres:pass@ep-gentle-frog.neon.tech/postgres"
    with pytest.raises(RuntimeError, match="remote/cloud database host"):
        validate_test_database_allowlist(url_remote, allow_maintenance=True)
