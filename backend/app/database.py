"""Operational Database Session Engine and Storage Port Implementation.

Task ID: S1-DAT-02, W0-PAL
Implements AbstractOperationalStorage from backend.app.ports.storage.
"""

from typing import Any, AsyncGenerator, Dict
from urllib.parse import urlparse

from backend.app.config import get_settings
from backend.app.ports.storage import AbstractOperationalStorage
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

settings = get_settings()

# Initialize Async SQLAlchemy Engine
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    echo=False,
    future=True,
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
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


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
