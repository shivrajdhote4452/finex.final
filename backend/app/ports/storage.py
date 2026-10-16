from abc import ABC, abstractmethod
from typing import Any, Dict


class AbstractOperationalStorage(ABC):
    """Port interface for checking database readiness and running transactions."""

    @abstractmethod
    async def is_healthy(self) -> bool:
        """Check whether operational database connection pool is active."""
        pass

    @abstractmethod
    async def get_connection_info(self) -> Dict[str, Any]:
        """Return safe database status metrics without leaking credentials."""
        pass
