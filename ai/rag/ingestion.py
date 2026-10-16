"""Document Ingestion & Chunking Pipeline.

Task ID: S1-AI-02, S4-AI-01
Processes approved regulatory documents into structured DocumentChunk records with verifiable citations.
"""

import hashlib
from typing import List

from ai.rag.corpus import REGULATORY_DOCUMENTS
from backend.app.ports.retriever import DocumentChunk


def estimate_token_count(text: str) -> int:
    """Rough estimation of token count (~4 characters per token)."""
    return max(1, len(text.split()) * 4 // 3)


def ingest_corpus_documents() -> List[DocumentChunk]:
    """Ingest and chunk all approved regulatory documents into verifiable DocumentChunks."""
    chunks: List[DocumentChunk] = []

    for doc in REGULATORY_DOCUMENTS:
        doc_id = doc["document_id"]
        doc_title = doc["title"]
        source_url = doc.get("source_url")
        doc_date = doc.get("document_date")

        for sec in doc.get("sections", []):
            section_title = sec["section"]
            page_num = sec["page_number"]
            raw_content = sec["content"].strip()

            # Generate unique reproducible chunk hash
            chunk_hash_input = f"{doc_id}:{section_title}:{page_num}"
            chunk_id = f"chk_{hashlib.sha256(chunk_hash_input.encode('utf-8')).hexdigest()[:12]}"

            chunk = DocumentChunk(
                chunk_id=chunk_id,
                document_id=doc_id,
                title=doc_title,
                source_url=source_url,
                section=section_title,
                page_number=page_num,
                content=raw_content,
                score=0.0,
                document_date=doc_date,
            )
            chunks.append(chunk)

    return chunks


def format_citation(chunk: DocumentChunk) -> str:
    """Format citation according to SEBI/NSE educational answer policy."""
    return f"[{chunk.title}, {chunk.section}, p. {chunk.page_number}]"
