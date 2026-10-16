"""Unit tests for Regulatory Document Ingestion and Retriever Pipeline.

Task ID: S1-AI-02
"""

import pytest
from ai.rag.ingestion import format_citation, ingest_corpus_documents
from ai.rag.retriever import RegulatoryDocumentRetriever


def test_ingest_corpus_documents():
    chunks = ingest_corpus_documents()
    assert len(chunks) == 11, f"Expected 11 sections across 3 documents, got {len(chunks)}"

    for c in chunks:
        assert c.chunk_id.startswith("chk_")
        assert c.document_id in ["SEBI-ED-2024-01", "NSE-FACT-NIFTY50-2026", "RBI-FLG-2024-02"]
        assert c.page_number is not None and c.page_number > 0
        assert len(c.content) > 50
        assert c.title


@pytest.mark.asyncio
async def test_retriever_emergency_fund_query():
    retriever = RegulatoryDocumentRetriever()
    results = await retriever.retrieve_relevant_chunks("emergency fund liquid buffer savings", top_k=3)

    assert len(results) > 0
    top_result = results[0]
    assert top_result.document_id == "SEBI-ED-2024-01"
    assert "Foundations of Financial Planning" in top_result.section
    citation = format_citation(top_result)
    assert "SEBI Guide to Financial Education for Beginners" in citation
    assert "p. 4" in citation


@pytest.mark.asyncio
async def test_retriever_nifty50_free_float_query():
    retriever = RegulatoryDocumentRetriever()
    results = await retriever.retrieve_relevant_chunks("NIFTY 50 index free-float market capitalization", top_k=2)

    assert len(results) > 0
    top_result = results[0]
    assert top_result.document_id == "NSE-FACT-NIFTY50-2026"
    assert "NIFTY" in top_result.title


@pytest.mark.asyncio
async def test_retriever_rbi_budgeting_query():
    retriever = RegulatoryDocumentRetriever()
    results = await retriever.retrieve_relevant_chunks("50-30-20 principle household budgeting expense", top_k=2)

    assert len(results) > 0
    top_result = results[0]
    assert top_result.document_id == "RBI-FLG-2024-02"
    assert "Household Cashflow and Budgeting" in top_result.section


@pytest.mark.asyncio
async def test_retriever_metadata_filtering():
    retriever = RegulatoryDocumentRetriever()
    # Filter strictly to RBI
    results = await retriever.retrieve_relevant_chunks(
        "inflation purchasing power",
        top_k=5,
        filters={"document_id": "RBI-FLG-2024-02"},
    )

    assert len(results) > 0
    for r in results:
        assert r.document_id == "RBI-FLG-2024-02"


def test_format_citation():
    chunks = ingest_corpus_documents()
    sebi_chunk = [c for c in chunks if c.document_id == "SEBI-ED-2024-01"][0]
    cit = format_citation(sebi_chunk)
    assert cit == "[SEBI Guide to Financial Education for Beginners, Chapter 1: The Foundations of Financial Planning, p. 4]"
