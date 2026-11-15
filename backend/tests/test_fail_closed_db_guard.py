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
    url = "postgresql+asyncpg://postgres:pass@127.0.0.1:5432/my_dev_database"
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
    validate_test_database_allowlist("sqlite:///:memory:?cache=shared")
    validate_test_database_allowlist("sqlite://")
    validate_test_database_allowlist("sqlite:///var/test_data/my_test.db")


def test_allowlist_rejects_non_test_sqlite_with_memory_in_query():
    """Verify that SQLite file targets cannot bypass allowlist by putting ':memory:' in query parameters."""
    with pytest.raises(RuntimeError, match="does not contain 'test' in its filename"):
        validate_test_database_allowlist("sqlite:///production.db?:memory:")
    with pytest.raises(RuntimeError, match="does not contain 'test' in its filename"):
        validate_test_database_allowlist("sqlite:///production.db?cache=:memory:")
    with pytest.raises(RuntimeError, match="does not contain 'test' in its filename"):
        validate_test_database_allowlist("sqlite+aiosqlite:///production.db?mode=:memory:")


def test_allowlist_rejects_non_test_sqlite_in_test_directory():
    """Verify that SQLite files in 'test' directories are rejected if filename does not contain 'test'."""
    with pytest.raises(RuntimeError, match="does not contain 'test' in its filename"):
        validate_test_database_allowlist("sqlite:///test/production.db")
    with pytest.raises(RuntimeError, match="does not contain 'test' in its filename"):
        validate_test_database_allowlist("sqlite:///tests/fixtures/live_data.db")
    with pytest.raises(RuntimeError, match="does not contain 'test' in its filename"):
        validate_test_database_allowlist("sqlite+aiosqlite:///var/test/production.db?:memory:")


def test_allowlist_rejects_postgres_with_test_in_path_prefix_only():
    """Verify that PostgreSQL URLs with 'test' only in directory/path prefix but not in database name are rejected."""
    url = "postgresql+asyncpg://postgres:pass@127.0.0.1:5432/test/production_db"
    with pytest.raises(RuntimeError, match="does not contain 'test' in its name"):
        validate_test_database_allowlist(url)


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
    url = "postgresql+asyncpg://sqlite:pass@127.0.0.1:5432/my_dev_database"
    with pytest.raises(RuntimeError, match="does not contain 'test' in its name"):
        validate_test_database_allowlist(url)


def test_allowlist_rejects_non_test_sqlite_files():
    """Verify that file-based SQLite databases without 'test' in the filename are rejected."""
    with pytest.raises(RuntimeError, match="does not contain 'test' in its filename"):
        validate_test_database_allowlist("sqlite+aiosqlite:///production.db")
    with pytest.raises(RuntimeError, match="does not contain 'test' in its filename"):
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


def test_allowlist_rejects_production_credentials_even_on_localhost():
    """Verify that production credentials (e.g. neondb_owner, cloud_admin) are rejected even on localhost."""
    url1 = "postgresql+asyncpg://neondb_owner:secret@127.0.0.1:5432/finex_test_db"
    with pytest.raises(RuntimeError, match="prohibited production database user 'neondb_owner'"):
        validate_test_database_allowlist(url1)

    url2 = "postgresql+asyncpg://cloud_admin:secret@localhost:5432/test_db"
    with pytest.raises(RuntimeError, match="prohibited production database user 'cloud_admin'"):
        validate_test_database_allowlist(url2)


def test_allowlist_rejects_sqlite_directory_traversal():
    """Verify that directory traversal sequences ('..') are blocked in SQLite paths."""
    with pytest.raises(RuntimeError, match="Directory traversal"):
        validate_test_database_allowlist("sqlite:///tests/../production.db")
    with pytest.raises(RuntimeError, match="Directory traversal"):
        validate_test_database_allowlist("sqlite:///./fixtures/../../test.db")


def test_allowlist_rejects_explicit_production_database_names():
    """Verify that known production database names (e.g. neondb, finex_db) are rejected."""
    url1 = "postgresql+asyncpg://postgres:pass@127.0.0.1:5432/neondb"
    with pytest.raises(RuntimeError, match="prohibited production database 'neondb'"):
        validate_test_database_allowlist(url1)

    url2 = "postgresql+asyncpg://postgres:pass@127.0.0.1:5432/finex_db"
    with pytest.raises(RuntimeError, match="prohibited production database 'finex_db'"):
        validate_test_database_allowlist(url2)


def test_allowlist_rejects_symlink_to_non_test_target(tmp_path):
    """Verify that symlinks named with 'test' but pointing to non-test database targets are rejected."""
    target_non_test = tmp_path / "production_vault.db"
    target_non_test.write_text("dummy")
    symlink_test = tmp_path / "test_link.db"
    try:
        import os
        os.symlink(target_non_test, symlink_test)
    except (OSError, NotImplementedError):
        pytest.skip("Symlink creation not supported in current execution environment")

    with pytest.raises(RuntimeError, match="points to non-test target"):
        validate_test_database_allowlist(f"sqlite:///{symlink_test}")


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


def test_allowlist_rejects_remote_network_ips_even_with_test_name_and_clean_user():
    """Verify that remote network IPs are blocked by host boundary alone, regardless of db name or username."""
    # Public IP
    url1 = "postgresql+asyncpg://safe_test_user:pass@198.51.100.22:5432/finex_test_clean_8f3a92b1"
    with pytest.raises(RuntimeError, match="non-local host '198.51.100.22'"):
        validate_test_database_allowlist(url1)

    # Private LAN IP
    url2 = "postgresql+asyncpg://safe_test_user:pass@10.0.0.50:5432/test_db"
    with pytest.raises(RuntimeError, match="non-local host '10.0.0.50'"):
        validate_test_database_allowlist(url2)

    # Alternate private LAN IP
    url3 = "postgresql+asyncpg://safe_test_user:pass@172.16.20.10:5432/test_db"
    with pytest.raises(RuntimeError, match="non-local host '172.16.20.10'"):
        validate_test_database_allowlist(url3)


def test_allowlist_rejects_unapproved_driver_schemes():
    """Verify that unapproved driver schemes are rejected immediately, preventing non-approved driver invocations."""
    unapproved_urls = [
        "mysql://safe_user:pass@127.0.0.1:3306/finex_test_db",
        "oracle://safe_user:pass@127.0.0.1:1521/finex_test_db",
        "redis://127.0.0.1:6379/test_db",
        "mongodb://safe_user:pass@127.0.0.1:27017/test_db",
        "http://127.0.0.1:8000/test.db",
    ]
    for url in unapproved_urls:
        with pytest.raises(RuntimeError, match="Unsupported or unapproved database scheme"):
            validate_test_database_allowlist(url)


def test_allowlist_rejects_remote_sqlite_hosts():
    """Verify that SQLite connection strings cannot specify remote network shares or hosts."""
    url = "sqlite://remote-fileshare.corp.internal/test.db"
    with pytest.raises(RuntimeError, match="unexpected non-local host"):
        validate_test_database_allowlist(url)


def test_allowlist_rejects_sqlite_query_parameter_memory_spoofing():
    """Verify that query parameters attempting to fake in-memory SQLite do not approve non-test files."""
    url = "sqlite:///production_vault.db?mode=memory&cache=shared"
    with pytest.raises(RuntimeError, match="does not contain 'test' in its filename"):
        validate_test_database_allowlist(url)


def test_active_test_environment_database_isolation():
    """Verify that the currently active test environment DATABASE_URL is verified safe and isolated."""
    import os
    from urllib.parse import urlparse
    from backend.app.config import get_settings

    active_url = os.environ.get("DATABASE_URL", "")
    assert active_url, "DATABASE_URL must be configured in active test environment"

    # Must pass validation without raising
    validate_test_database_allowlist(active_url)

    # Confirm host is strictly local
    parsed = urlparse(active_url)
    scheme = parsed.scheme.lower()
    if "postgres" in scheme:
        assert parsed.hostname in ("127.0.0.1", "localhost"), f"Postgres test host must be loopback, got {parsed.hostname}"
    elif "sqlite" in scheme:
        assert parsed.hostname in ("", None, "127.0.0.1", "localhost"), f"SQLite host must be empty or loopback, got {parsed.hostname}"

    # Confirm no remote cloud markers in environment
    for marker in ("neon.tech", "ep-gentle-frog", "aws.neon.tech", "render.com"):
        assert marker not in active_url.lower(), f"Detected cloud marker {marker} in active test DATABASE_URL"

