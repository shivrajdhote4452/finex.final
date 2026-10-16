from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from pydantic import BaseModel


class DocumentChunk(BaseModel):
    chunk_id: str
    document_id: str
    title: str
    source_url: Optional[str] = None
    section: Optional[str] = None
    page_number: Optional[int] = None
    content: str
    score: float = 0.0
    document_date: Optional[str] = None


class AbstractDocumentRetriever(ABC):
    """Port interface for vector / keyword document retrieval."""

    @abstractmethod
    async def retrieve_relevant_chunks(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, str]] = None,
    ) -> List[DocumentChunk]:
        """Retrieve top_k chunks matching query subject to metadata filters."""
        pass
