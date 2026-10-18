"""Regulatory Document Retriever implementing AbstractDocumentRetriever port.

Task ID: S1-AI-02, S4-AI-01, Defect Area 5
Deterministic keyword & semantic density scoring across genuine regulatory documents
persisted in PostgreSQL, with optional fallback for isolated unit tests.
"""

import re
from typing import Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ai.rag.ingestion import ingest_corpus_documents
from backend.app.ports.retriever import AbstractDocumentRetriever, DocumentChunk

STOPWORDS = {
    "a",
    "about",
    "above",
    "after",
    "again",
    "against",
    "all",
    "am",
    "an",
    "and",
    "any",
    "are",
    "as",
    "at",
    "be",
    "because",
    "been",
    "before",
    "being",
    "below",
    "between",
    "both",
    "but",
    "by",
    "did",
    "do",
    "does",
    "doing",
    "down",
    "during",
    "each",
    "few",
    "for",
    "from",
    "further",
    "had",
    "has",
    "have",
    "having",
    "he",
    "her",
    "here",
    "hers",
    "him",
    "his",
    "how",
    "i",
    "if",
    "in",
    "into",
    "is",
    "it",
    "its",
    "me",
    "more",
    "most",
    "my",
    "myself",
    "no",
    "nor",
    "not",
    "of",
    "off",
    "on",
    "once",
    "only",
    "or",
    "other",
    "our",
    "ours",
    "out",
    "over",
    "own",
    "same",
    "she",
    "so",
    "some",
    "such",
    "than",
    "that",
    "the",
    "their",
    "theirs",
    "them",
    "then",
    "there",
    "these",
    "they",
    "this",
    "those",
    "through",
    "to",
    "too",
    "under",
    "until",
    "up",
    "very",
    "was",
    "we",
    "were",
    "what",
    "when",
    "where",
    "which",
    "while",
    "who",
    "whom",
    "why",
    "with",
    "you",
    "your",
}


def tokenize(text: str) -> List[str]:
    """Normalize text into lowercase alphanumeric tokens."""
    return re.findall(r"\b[a-z0-9]+\b", text.lower())


class RegulatoryDocumentRetriever(AbstractDocumentRetriever):
    """Port adapter for retrieving relevant regulatory chunks with citation tracking."""

    def __init__(
        self,
        chunks: Optional[List[DocumentChunk]] = None,
        allow_fixture_fallback: bool = False,
    ):
        self._chunks = chunks
        self.allow_fixture_fallback = allow_fixture_fallback

    async def _fetch_db_chunks(self, db: Optional[AsyncSession] = None) -> List[DocumentChunk]:
        """Fetch active document chunks from PostgreSQL database."""
        try:
            from sqlalchemy import select

            from backend.app.database import AsyncSessionLocal
            from backend.app.models.rag import DocumentChunk as DocumentChunkModel
            from backend.app.models.rag import DocumentRegistry as DocumentRegistryModel

            async def _query(session: AsyncSession) -> List[DocumentChunk]:
                stmt = (
                    select(DocumentChunkModel, DocumentRegistryModel)
                    .join(DocumentRegistryModel, DocumentChunkModel.document_id == DocumentRegistryModel.id)
                    .where(
                        DocumentChunkModel.status == "ACTIVE",
                        DocumentRegistryModel.status == "ACTIVE",
                    )
                )
                res = await session.execute(stmt)
                rows = res.all()
                return [
                    DocumentChunk(
                        chunk_id=c.id,
                        document_id=c.document_id,
                        title=d.title,
                        publisher=d.publisher,
                        source_url=d.source_url,
                        section=c.section_title,
                        page_number=c.page_number,
                        content=c.content,
                        score=0.0,
                        document_date=d.publishing_date.isoformat() if d.publishing_date else None,
                        content_hash=d.content_hash,
                    )
                    for c, d in rows
                ]

            if db is not None:
                return await _query(db)
            else:
                async with AsyncSessionLocal() as session:
                    return await _query(session)
        except Exception:
            return []

    async def retrieve_relevant_chunks(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, str]] = None,
        db: Optional[AsyncSession] = None,
    ) -> List[DocumentChunk]:
        """Rank and return top_k chunks matching query terms subject to metadata filters."""
        all_tokens = set(tokenize(query))
        query_tokens = {t for t in all_tokens if t not in STOPWORDS}
        if not query_tokens:
            return []

        # 1. Determine candidate pool
        if self._chunks is not None:
            candidate_chunks = self._chunks
        else:
            db_chunks = await self._fetch_db_chunks(db)
            if db_chunks:
                candidate_chunks = db_chunks
            elif self.allow_fixture_fallback:
                candidate_chunks = ingest_corpus_documents()
            else:
                candidate_chunks = []

        if not candidate_chunks:
            return []

        scored_chunks: List[DocumentChunk] = []

        for chunk in candidate_chunks:
            # Apply metadata filters if provided
            if filters:
                match = True
                for k, v in filters.items():
                    attr_val = getattr(chunk, k, None)
                    if attr_val is None or str(attr_val).lower() != str(v).lower():
                        match = False
                        break
                if not match:
                    continue

            content_tokens = tokenize(chunk.content)
            title_tokens = tokenize(chunk.title)
            section_tokens = tokenize(chunk.section or "")

            if not content_tokens:
                continue

            # Term frequency scoring with title/section weighting
            content_token_set = set(content_tokens)
            overlap = query_tokens.intersection(content_token_set)
            title_overlap = query_tokens.intersection(set(title_tokens))
            section_overlap = query_tokens.intersection(set(section_tokens))

            if not overlap and not title_overlap and not section_overlap:
                continue

            # BM25-style saturation scoring
            tf_score = 0.0
            for token in overlap:
                count = content_tokens.count(token)
                tf_score += (count * 2.2) / (count + 1.2 * (0.25 + 0.75 * len(content_tokens) / 100))

            # Boost for title and section matches
            tf_score += len(title_overlap) * 2.5
            tf_score += len(section_overlap) * 1.8

            # Normalize to 0.0 - 1.0 range
            normalized_score = min(1.0, round(tf_score / (len(query_tokens) * 3.0), 3))

            # Minimum relevance threshold to avoid irrelevant matches
            if normalized_score < 0.04:
                continue

            scored_chunks.append(
                DocumentChunk(
                    chunk_id=chunk.chunk_id,
                    document_id=chunk.document_id,
                    title=chunk.title,
                    publisher=chunk.publisher,
                    source_url=chunk.source_url,
                    section=chunk.section,
                    page_number=chunk.page_number,
                    content=chunk.content,
                    score=normalized_score,
                    document_date=chunk.document_date,
                    content_hash=chunk.content_hash,
                )
            )

        # Sort descending by score
        scored_chunks.sort(key=lambda c: c.score, reverse=True)
        return scored_chunks[:top_k]
