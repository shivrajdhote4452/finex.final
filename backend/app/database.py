"""Operational Database Session Engine and Storage Port Implementation.

Task ID: S1-DAT-02, W0-PAL
Implements AbstractOperationalStorage from backend.app.ports.storage.
"""

import logging
import os
import sys
from typing import Any, AsyncGenerator, Dict
from urllib.parse import urlparse

from backend.app.config import Environment, get_settings, sanitize_asyncpg_url
from backend.app.ports.storage import AbstractOperationalStorage
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

settings = get_settings()
logger = logging.getLogger(__name__)

# Initialize Async SQLAlchemy Engine
engine_kwargs: Dict[str, Any] = {
    "echo": False,
    "future": True,
}

# Normalize and sanitize DATABASE_URL to asyncpg dialect defensively
db_url = sanitize_asyncpg_url(settings.DATABASE_URL)

# FAIL-CLOSED SAFEGUARD: Enforce isolated test database allowlist policy
is_test_env = (
    "pytest" in sys.modules or settings.ENVIRONMENT == Environment.TESTING or "PYTEST_CURRENT_TEST" in os.environ
)

APPROVED_SQLITE_SCHEMES = frozenset({"sqlite", "sqlite+aiosqlite", "sqlite+pysqlite"})
APPROVED_POSTGRES_SCHEMES = frozenset(
    {
        "postgresql",
        "postgresql+asyncpg",
        "postgresql+psycopg",
        "postgresql+psycopg2",
        "postgres",
    }
)

DISALLOWED_PROD_USERNAMES = frozenset(
    {
        "neondb_owner",
        "cloud_admin",
        "render",
        "rds_admin",
        "prod_admin",
        "prod_user",
    }
)

DISALLOWED_PROD_DBNAMES = frozenset(
    {
        "neondb",
        "finex_db",
        "finex",
        "production",
        "prod",
        "live",
    }
)

REMOTE_CLOUD_MARKERS = (
    "neon.tech",
    "ep-gentle-frog",
    "aws.neon.tech",
    "render.com",
    "onrender.com",
    "amazonaws.com",
    "rds.amazonaws.com",
    "supabase.co",
    "supabase.com",
    "google.com",
    "cloud.google.com",
    "azure.com",
    "digitalocean.com",
    "clever-cloud.com",
)


def validate_test_database_allowlist(url_str: str, allow_maintenance: bool = False) -> None:
    """Validate that the database connection points to an approved isolated test database.

    Fail-Closed Policy:
    1. Parse the actual database scheme/driver:
       - Approved SQLite schemes: 'sqlite', 'sqlite+aiosqlite', 'sqlite+pysqlite'
       - Approved PostgreSQL schemes: 'postgresql', 'postgresql+asyncpg', 'postgresql+psycopg', 'postgresql+psycopg2', 'postgres'
       - Any unsupported, remote, or malformed scheme raises a fatal RuntimeError.
    2. Check for remote/cloud host markers across the entire URL (including username, password, host, path, query):
       - If any cloud host marker is detected, raises a fatal RuntimeError.
    3. Dedicated Test Credentials & Explicit Test Database Designation (PostgreSQL):
       - Host must strictly be '127.0.0.1' or 'localhost'.
       - Production credentials (e.g. 'neondb_owner', 'cloud_admin') are strictly forbidden.
       - Target database name must explicitly contain 'test' (e.g. 'finex_test_db', 'finex_test_clean_8f3a92b1')
         and cannot match known production database names (e.g. 'finex_db', 'neondb').
       - If allow_maintenance is True, maintenance databases ('postgres', 'template1') on local host are permitted
         exclusively for test lifecycle database creation/dropping.
    4. Path Traversal & Symlink Protection (SQLite):
       - Host must be empty or local (127.0.0.1 / localhost). Remote network hosts are forbidden.
       - Database target must either be in-memory (':memory:' or empty) OR the file path must explicitly
         contain 'test' in its filename (e.g. 'test.db', 'finex_test.db').
       - Directory traversal ('..') is strictly rejected.
       - Symlinks pointing to non-test target databases are strictly rejected.
       - Non-test SQLite files (e.g. 'production.db') are rejected.

    LIMITATION & ARCHITECTURAL BOUNDARY NOTICE:
    Application-level URL validation, scheme allowlisting, and monkeypatching provide
    essential defense-in-depth within python runtime and pytest runners. However,
    application-level checks alone CANNOT guarantee absolute database isolation:
    - They cannot prevent external host processes, direct CLI tools (e.g. psql, sqlite3),
      or unmonitored scripts from accessing production if credentials exist in the environment.
    - Genuine isolation requires physical or network infrastructure separation:
      1. Distinct database instances/clusters for testing vs production (no shared endpoints).
      2. Dedicated test credentials with zero permissions or network routes to production VPCs.
      3. Network firewall / security group boundaries restricting test runners to local or ephemeral containers.
    """
    if not url_str or not isinstance(url_str, str) or not url_str.strip():
        raise RuntimeError("CRITICAL FAIL-CLOSED ERROR: Automated tests received an empty or invalid DATABASE_URL.")

    clean_url = url_str.strip()
    try:
        parsed = urlparse(clean_url)
    except Exception as exc:
        raise RuntimeError(f"CRITICAL FAIL-CLOSED ERROR: Failed to parse database URL: {exc}")

    scheme = (parsed.scheme or "").lower().strip()
    if scheme not in APPROVED_SQLITE_SCHEMES and scheme not in APPROVED_POSTGRES_SCHEMES:
        raise RuntimeError(
            f"CRITICAL FAIL-CLOSED ERROR: Unsupported or unapproved database scheme '{scheme}'. "
            f"Tests must use an approved PostgreSQL or SQLite test driver."
        )

    url_lower = clean_url.lower()

    # Reject any remote cloud host markers anywhere in the URL
    matched_marker = next((m for m in REMOTE_CLOUD_MARKERS if m in url_lower), None)
    if matched_marker:
        raise RuntimeError(
            f"CRITICAL FAIL-CLOSED ERROR: Automated tests detected a remote/cloud database host ({matched_marker}). "
            f"Executing tests against remote or production databases is strictly prohibited to prevent data loss. "
            f"Tests must run against an isolated test database (e.g. finex_test_db on localhost or SQLite)."
        )

    # Validate SQLite targets
    if scheme in APPROVED_SQLITE_SCHEMES:
        host = (parsed.hostname or "").lower().strip()
        if host and host not in ("127.0.0.1", "localhost"):
            raise RuntimeError(
                f"CRITICAL FAIL-CLOSED ERROR: SQLite test database specified unexpected non-local host '{host}'."
            )

        raw_path = (parsed.path or "").strip()
        clean_path = raw_path.lstrip("/")

        # In-memory SQLite: target path must explicitly be :memory: or empty
        # Note: Query parameters containing ':memory:' MUST NOT approve a file-based path.
        if clean_path in (":memory:", ""):
            return

        # Path traversal rejection
        if ".." in clean_path:
            raise RuntimeError(
                "CRITICAL FAIL-CLOSED ERROR: Directory traversal ('..') is strictly prohibited in SQLite test database paths."
            )

        # File-based SQLite: the database filename itself must explicitly contain 'test'
        norm_path = clean_path.replace("\\", "/")
        if norm_path.endswith("/"):
            raise RuntimeError("CRITICAL FAIL-CLOSED ERROR: SQLite database file target is invalid or missing.")

        filename = os.path.basename(norm_path).lower()
        if not filename or "test" not in filename:
            target_name = filename or clean_path
            raise RuntimeError(
                f"CRITICAL FAIL-CLOSED ERROR: SQLite database file '{target_name}' does not contain 'test' in its filename. "
                f"File-based SQLite test databases must contain 'test' in their filename to prevent modifying non-test or production database files."
            )

        # Symlink target inspection: prevent symlinks from pointing to non-test target files
        candidate_paths = [p for p in (raw_path, norm_path, clean_path) if p]
        try:
            for path_to_check in candidate_paths:
                if os.path.islink(path_to_check):
                    real_target = os.path.realpath(path_to_check)
                    real_filename = os.path.basename(real_target.replace("\\", "/")).lower()
                    if "test" not in real_filename:
                        raise RuntimeError(
                            f"CRITICAL FAIL-CLOSED ERROR: SQLite database symlink '{path_to_check}' points to non-test target '{real_target}'. "
                            f"Symlinks targeting non-test database files are strictly prohibited in automated tests."
                        )
                    break
        except OSError:
            pass

        return

    # Validate PostgreSQL targets
    if scheme in APPROVED_POSTGRES_SCHEMES:
        host = (parsed.hostname or "").lower().strip()
        if not host or host not in ("127.0.0.1", "localhost"):
            raise RuntimeError(
                f"CRITICAL FAIL-CLOSED ERROR: Automated tests attempted to connect to non-local host '{host}'. "
                f"Tests are strictly restricted to local test databases on 127.0.0.1 or localhost."
            )

        # Dedicated test credentials enforcement: reject production roles/credentials
        username = (parsed.username or "").lower().strip()
        if username in DISALLOWED_PROD_USERNAMES:
            raise RuntimeError(
                f"CRITICAL FAIL-CLOSED ERROR: Automated tests detected prohibited production database user '{username}'. "
                f"Tests must use dedicated isolated test credentials with no access to production data."
            )

        raw_path = (parsed.path or "").strip()
        clean_path = raw_path.lstrip("/")
        if not clean_path:
            raise RuntimeError(
                "CRITICAL FAIL-CLOSED ERROR: Automated tests attempted to connect without specifying a database name."
            )

        norm_path = clean_path.replace("\\", "/")
        dbname = os.path.basename(norm_path).lower()
        if not dbname:
            raise RuntimeError(
                "CRITICAL FAIL-CLOSED ERROR: Automated tests attempted to connect without specifying a database name."
            )

        if allow_maintenance and dbname in ("postgres", "template1"):
            return

        if dbname in DISALLOWED_PROD_DBNAMES:
            raise RuntimeError(
                f"CRITICAL FAIL-CLOSED ERROR: Automated tests attempted to connect to prohibited production database '{dbname}'. "
                f"Tests are forbidden from connecting to production databases."
            )

        if "test" not in dbname:
            raise RuntimeError(
                f"CRITICAL FAIL-CLOSED ERROR: Automated tests attempted to connect to database '{dbname}', "
                f"which does not contain 'test' in its name. Tests must use an explicitly designated test database "
                f"(e.g. finex_test_db) to prevent modifying local development or production data."
            )
        return


if is_test_env:
    validate_test_database_allowlist(db_url)

is_sqlite_scheme = urlparse(db_url).scheme.lower() in APPROVED_SQLITE_SCHEMES
if is_sqlite_scheme or settings.ENVIRONMENT == Environment.TESTING or "pytest" in sys.modules:
    engine_kwargs["poolclass"] = NullPool
else:
    engine_kwargs["pool_size"] = settings.DATABASE_POOL_SIZE
    engine_kwargs["max_overflow"] = settings.DATABASE_MAX_OVERFLOW
    engine_kwargs["pool_pre_ping"] = True

if "sslmode=" in db_url:
    db_url = db_url.replace("sslmode=", "ssl=")

if "-pooler" in db_url or "pgbouncer" in db_url or "neon.tech" in db_url:
    connect_args = engine_kwargs.get("connect_args", {})
    connect_args["statement_cache_size"] = 0
    connect_args["prepared_statement_cache_size"] = 0
    engine_kwargs["connect_args"] = connect_args

engine = create_async_engine(
    db_url,
    **engine_kwargs,
)

# Async Session Factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding an isolated async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            try:
                await session.commit()
            except Exception as commit_exc:
                logger.warning("Database session post-yield commit rolled back: %s", commit_exc)
                try:
                    await session.rollback()
                except Exception:
                    pass
        except Exception:
            try:
                await session.rollback()
            except Exception:
                pass
            raise
        finally:
            try:
                await session.close()
            except Exception:
                pass


class SQLAlchemyOperationalStorage(AbstractOperationalStorage):
    """PostgreSQL operational database storage adapter."""

    def __init__(self, session_factory=AsyncSessionLocal, db_engine=engine):
        self._session_factory = session_factory
        self._engine = db_engine

    async def is_healthy(self) -> bool:
        """Execute lightweight probe query to verify pool connectivity."""
        try:
            async with self._session_factory() as session:
                result = await session.execute(text("SELECT 1"))
                return result.scalar() == 1
        except Exception:
            return False

    async def get_connection_info(self) -> Dict[str, Any]:
        """Return safe database status metrics without leaking passwords or host credentials."""
        parsed = urlparse(settings.DATABASE_URL)
        driver = parsed.scheme.split("+")[0] if "+" in parsed.scheme else parsed.scheme
        healthy = await self.is_healthy()

        return {
            "status": "UP" if healthy else "DEGRADED",
            "dialect": "postgresql",
            "driver": driver,
            "database_name": parsed.path.lstrip("/"),
            "pool_size": settings.DATABASE_POOL_SIZE,
            "max_overflow": settings.DATABASE_MAX_OVERFLOW,
        }
