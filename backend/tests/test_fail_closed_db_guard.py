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
    with pytest.raises(RuntimeError, match="empty DATABASE_URL"):
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
