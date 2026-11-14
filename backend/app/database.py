"""Operational Database Session Engine and Storage Port Implementation.

Task ID: S1-DAT-02, W0-PAL
Implements AbstractOperationalStorage from backend.app.ports.storage.
"""

import os
import sys
from typing import Any, AsyncGenerator, Dict
from urllib.parse import urlparse

from backend.app.config import Environment, get_settings
from backend.app.ports.storage import AbstractOperationalStorage
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

settings = get_settings()

# Initialize Async SQLAlchemy Engine
engine_kwargs: Dict[str, Any] = {
    "echo": False,
    "future": True,
}

from backend.app.config import sanitize_asyncpg_url

# Normalize and sanitize DATABASE_URL to asyncpg dialect defensively
db_url = sanitize_asyncpg_url(settings.DATABASE_URL)

# FAIL-CLOSED SAFEGUARD: Enforce isolated test database allowlist policy
is_test_env = (
    "pytest" in sys.modules
    or settings.ENVIRONMENT == Environment.TESTING
    or "PYTEST_CURRENT_TEST" in os.environ
)

def validate_test_database_allowlist(url_str: str) -> None:
    """Validate that the database connection points to an approved isolated test database.
    
    Allowlist Policy:
    1. SQLite databases (e.g., sqlite+aiosqlite:///:memory:) are approved.
    2. PostgreSQL databases are approved ONLY if:
       - Host is strictly '127.0.0.1' or 'localhost'.
       - Database name path explicitly contains 'test' (e.g., 'finex_test_db', 'finex_test_clean_...').
       - Host does NOT contain any remote, cloud, or production host markers.
    3. Any unapproved, remote, or production database raises a fatal RuntimeError.
    """
    if not url_str:
        raise RuntimeError("CRITICAL FAIL-CLOSED ERROR: Automated tests received an empty DATABASE_URL.")
    
    url_lower = url_str.lower()
    if "sqlite" in url_lower:
        return
        
    try:
        parsed = urlparse(url_str)
        host = (parsed.hostname or "").lower().strip()
        path = (parsed.path or "").lower().lstrip("/")
        
        # Disallow remote/cloud host markers
        remote_markers = [
            "neon.tech", "ep-gentle-frog", "aws.neon.tech", "render.com", 
            "onrender.com", "amazonaws.com", "supabase.co", "google.com", "azure.com"
        ]
        matched_marker = next((m for m in remote_markers if m in url_lower), None)
        if matched_marker:
            raise RuntimeError(
                f"CRITICAL FAIL-CLOSED ERROR: Automated tests detected a remote/cloud database host ({matched_marker}). "
                f"Executing tests against remote or production databases is strictly prohibited to prevent data loss. "
                f"Tests must run against an isolated test database (e.g. finex_test_db on localhost or SQLite)."
            )
            
        if host not in ("127.0.0.1", "localhost"):
            raise RuntimeError(
                f"CRITICAL FAIL-CLOSED ERROR: Automated tests attempted to connect to non-local host '{host}'. "
                f"Tests are strictly restricted to local test databases on 127.0.0.1/localhost or SQLite."
            )
            
        if "test" not in path:
            raise RuntimeError(
                f"CRITICAL FAIL-CLOSED ERROR: Automated tests attempted to connect to database '{path}', "
                f"which does not contain 'test' in its name. Tests must use an explicitly designated test database "
                f"(e.g. finex_test_db) to prevent modifying local development or production data."
            )
    except RuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError(f"CRITICAL FAIL-CLOSED ERROR: Failed to validate test database URL: {exc}")

if is_test_env:
    validate_test_database_allowlist(db_url)

if "sqlite" in db_url or settings.ENVIRONMENT == Environment.TESTING or "pytest" in sys.modules:
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
            except Exception:
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
