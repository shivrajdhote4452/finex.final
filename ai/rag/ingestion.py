"""Document Ingestion & Chunking Pipeline.

Task ID: S1-AI-02, S4-AI-01, Defect Area 5
Processes genuine regulatory and source documents into structured DocumentChunk records
with verifiable citations, byte-level content hashing, and durable DB persistence.
"""

import hashlib
import io
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import pypdf
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from ai.rag.corpus import REGULATORY_DOCUMENTS
from backend.app.models.rag import DocumentChunk as DocumentChunkModel
from backend.app.models.rag import DocumentRegistry as DocumentRegistryModel
from backend.app.ports.retriever import DocumentChunk

# Approved local document catalog with genuine local file paths and official metadata
APPROVED_LOCAL_DOCUMENTS = [
    {
        "document_id": "SEBI-ED-2024-01",
        "title": "SEBI Guide to Financial Education for Beginners",
        "doc_type": "REGULATORY_GUIDE",
        "publisher": "Securities and Exchange Board of India (SEBI)",
        "publishing_date": date(2024, 1, 15),
        "source_url": "https://investor.sebi.gov.in/financial-education/beginners-guide.html",
        "local_file": "data/documents/sebi_financial_education_guide.txt",
    },
    {
        "document_id": "NSE-FACT-NIFTY50-2026",
        "title": "NIFTY 50 Index Methodology and Selection Criteria",
        "doc_type": "INDEX_METHODOLOGY",
        "publisher": "NSE Indices Limited",
        "publishing_date": date(2026, 3, 31),
        "source_url": "https://www.niftyindices.com/indices/equity/broad-based-indices/NIFTY-50",
        "local_file": "data/documents/nse_nifty50_methodology.txt",
    },
    {
        "document_id": "RBI-FLG-2024-02",
        "title": "RBI Financial Literacy Guide - Savings, Borrowing, and Budgeting",
        "doc_type": "LITERACY_GUIDE",
        "publisher": "Reserve Bank of India",
        "publishing_date": date(2024, 2, 20),
        "source_url": "https://rbi.org.in/financialeducation/literacy-guide.html",
        "local_file": "data/documents/rbi_financial_literacy_guide.txt",
    },
    {
        "document_id": "FINEX-SOLO-SPRINT-PLAN-2026",
        "title": "FinEx Solo Project Blueprint and Real Data Sprint Plan",
        "doc_type": "PLANNING_BLUEPRINT",
        "publisher": "FinEx Engineering / Shivraj Dhote",
        "publishing_date": date(2026, 10, 16),
        "source_url": "file://FinEx_Shivraj_Solo_Real_Data_Sprint_Plan (1).pdf",
        "local_file": "FinEx_Shivraj_Solo_Real_Data_Sprint_Plan (1).pdf",
    },
]


def estimate_token_count(text: str) -> int:
    """Rough estimation of token count (~4 characters per token)."""
    return max(1, len(text.split()) * 4 // 3)


def parse_text_document(raw_bytes: bytes) -> Tuple[str, List[Dict[str, Any]]]:
    """Extract sections from structured text / markdown document bytes."""
    content_hash = hashlib.sha256(raw_bytes).hexdigest()
    text = raw_bytes.decode("utf-8", errors="replace")
    sections: List[Dict[str, Any]] = []

    parts = re.split(r"\n(?=##\s+)", text.strip())
    for idx, part in enumerate(parts):
        lines = part.strip().split("\n")
        title = lines[0].replace("##", "").strip() if lines else f"Section {idx + 1}"
        page = None
        content_lines = []
        for line in lines[1:]:
            if line.startswith("Page:"):
                try:
                    page = int(line.replace("Page:", "").strip())
                except ValueError:
                    page = idx + 1
            else:
                content_lines.append(line)
        body = "\n".join(content_lines).strip()
        sections.append(
            {
                "section": title[:190],
                "page_number": page or (idx + 1),
                "content": body,
                "word_count": len(body.split()),
            }
        )
    return content_hash, sections


def parse_pdf_document(raw_bytes: bytes) -> Tuple[str, List[Dict[str, Any]]]:
    """Extract pages from actual PDF document bytes."""
    content_hash = hashlib.sha256(raw_bytes).hexdigest()
    reader = pypdf.PdfReader(io.BytesIO(raw_bytes))
    sections: List[Dict[str, Any]] = []

    for page_idx, page in enumerate(reader.pages):
        text = page.extract_text()
        if not text or not text.strip():
            continue
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        section_title = lines[0] if lines else f"Page {page_idx + 1}"
        clean_text = "\n".join(lines)
        sections.append(
            {
                "section": section_title[:190],
                "page_number": page_idx + 1,
                "content": clean_text,
                "word_count": len(clean_text.split()),
            }
        )
    return content_hash, sections


def extract_document_from_file(file_path: Union[str, Path]) -> Tuple[str, List[Dict[str, Any]]]:
    """Read actual document bytes from local filesystem and extract verifiable sections with SHA-256 hash."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Local document not found at {path.resolve()}")

    with open(path, "rb") as f:
        raw_bytes = f.read()

    if path.suffix.lower() == ".pdf":
        return parse_pdf_document(raw_bytes)
    else:
        return parse_text_document(raw_bytes)


async def ingest_document_file_to_db(
    meta: Dict[str, Any],
    db: AsyncSession,
    base_dir: Optional[Path] = None,
) -> Optional[DocumentRegistryModel]:
    """Idempotently ingest a genuine local document file into PostgreSQL."""
    base = base_dir or Path.cwd()
    file_rel = meta.get("local_file")
    if not file_rel:
        return None

    file_path = base / file_rel
    if not file_path.exists():
        return None

    content_hash, sections = extract_document_from_file(file_path)
    doc_id = meta["document_id"]
    now = datetime.now(timezone.utc)

    # 1. Check existing record
    existing = await db.get(DocumentRegistryModel, doc_id)
    if existing:
        if existing.content_hash == content_hash:
            # Document is already current and indexed
            return existing

        # Document updated: replace chunks
        await db.execute(delete(DocumentChunkModel).where(DocumentChunkModel.document_id == doc_id))
        existing.content_hash = content_hash
        existing.title = meta.get("title", existing.title)
        existing.publisher = meta.get("publisher", existing.publisher)
        existing.source_url = meta.get("source_url", existing.source_url)
        existing.created_at = now
        doc_reg = existing
    else:
        doc_reg = DocumentRegistryModel(
            id=doc_id,
            title=meta["title"],
            doc_type=meta.get("doc_type", "REGULATORY_GUIDE"),
            publisher=meta.get("publisher", "Regulatory Authority"),
            publishing_date=meta.get("publishing_date", date.today()),
            reporting_period=meta.get("reporting_period"),
            security_symbol=meta.get("security_symbol"),
            isin=meta.get("isin"),
            source_url=meta.get("source_url"),
            content_hash=content_hash,
            status="ACTIVE",
            created_at=now,
        )
        db.add(doc_reg)

    # Insert chunks
    for idx, sec in enumerate(sections):
        p_num = sec.get("page_number", idx + 1)
        chunk_id = f"chk_{hashlib.sha256(f'{doc_id}:{idx}:{p_num}'.encode()).hexdigest()[:12]}"
        chunk = DocumentChunkModel(
            id=chunk_id,
            document_id=doc_id,
            chunk_index=idx,
            content=sec["content"],
            section_title=sec.get("section"),
            page_number=p_num,
            word_count=sec.get("word_count", len(sec["content"].split())),
            status="ACTIVE",
            created_at=now,
        )
        db.add(chunk)

    await db.commit()
    await db.refresh(doc_reg)
    return doc_reg


async def ensure_documents_indexed_db(
    db: Optional[AsyncSession] = None,
    base_dir: Optional[Path] = None,
) -> List[DocumentRegistryModel]:
    """Ensure all approved local documents are extracted and indexed in the PostgreSQL database."""
    from backend.app.database import AsyncSessionLocal

    results = []
    if db is not None:
        for doc_meta in APPROVED_LOCAL_DOCUMENTS:
            doc = await ingest_document_file_to_db(doc_meta, db, base_dir)
            if doc:
                results.append(doc)
    else:
        async with AsyncSessionLocal() as session:
            for doc_meta in APPROVED_LOCAL_DOCUMENTS:
                doc = await ingest_document_file_to_db(doc_meta, session, base_dir)
                if doc:
                    results.append(doc)
    return results


def ingest_corpus_documents() -> List[DocumentChunk]:
    """Legacy/demo fallback: Ingest hardcoded regulatory documents for isolated tests without DB."""
    chunks: List[DocumentChunk] = []
    seen_ids = set()

    for doc in REGULATORY_DOCUMENTS:
        doc_id = doc["document_id"]
        doc_title = doc["title"]
        publisher = doc.get("publisher", "SEBI / Regulatory Authority")
        source_url = doc.get("source_url")
        doc_date = doc.get("document_date")

        for sec in doc.get("sections", []):
            section_title = sec["section"]
            page_num = sec["page_number"]
            raw_content = sec["content"].strip()

            chunk_hash_input = f"{doc_id}:{section_title}:{page_num}"
            chunk_id = f"chk_{hashlib.sha256(chunk_hash_input.encode('utf-8')).hexdigest()[:12]}"

            if chunk_id in seen_ids:
                continue
            seen_ids.add(chunk_id)

            content_hash = hashlib.sha256(raw_content.encode("utf-8")).hexdigest()

            chunk = DocumentChunk(
                chunk_id=chunk_id,
                document_id=doc_id,
                title=doc_title,
                publisher=publisher,
                source_url=source_url,
                section=section_title,
                page_number=page_num,
                content=raw_content,
                score=0.0,
                document_date=doc_date,
                content_hash=content_hash,
            )
            chunks.append(chunk)

    return chunks


def ingest_document_payload(doc: dict) -> List[DocumentChunk]:
    """Idempotently ingest an official document payload and return verifiable DocumentChunks."""
    doc_id = doc["document_id"]
    doc_title = doc["title"]
    publisher = doc.get("publisher", "Regulatory Authority")
    source_url = doc.get("source_url")
    doc_date = doc.get("document_date")

    chunks: List[DocumentChunk] = []
    for sec in doc.get("sections", []):
        section_title = sec.get("section", "General")
        page_num = sec.get("page_number", 1)
        raw_content = sec.get("content", "").strip()

        chunk_hash_input = f"{doc_id}:{section_title}:{page_num}"
        chunk_id = f"chk_{hashlib.sha256(chunk_hash_input.encode('utf-8')).hexdigest()[:12]}"
        content_hash = hashlib.sha256(raw_content.encode("utf-8")).hexdigest()

        chunks.append(
            DocumentChunk(
                chunk_id=chunk_id,
                document_id=doc_id,
                title=doc_title,
                publisher=publisher,
                source_url=source_url,
                section=section_title,
                page_number=page_num,
                content=raw_content,
                score=0.0,
                document_date=doc_date,
                content_hash=content_hash,
            )
        )
    return chunks


def format_citation(chunk: DocumentChunk) -> str:
    """Format citation according to SEBI/NSE educational answer policy."""
    return f"[{chunk.title}, {chunk.section}, p. {chunk.page_number}]"
