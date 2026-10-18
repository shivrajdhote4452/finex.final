"""Integration and Acceptance Tests for Live Market Ingestion and RAG Grounding.

Defect Area 6 Acceptance Tests:
1. Live external market ingestion with source evidence and raw payload hashing.
2. Source outage behavior: cache serving with freshness recalculation and explicit 404 on un-cached source outage.
3. Official regulatory document ingestion, content hashing, indexing, retrieval, and grounded citations.
4. Insufficient evidence behavior: withholding ungrounded answers when evidence is missing.
"""

import hashlib
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from ai.rag.ingestion import ingest_corpus_documents, ingest_document_payload
from ai.rag.retriever import RegulatoryDocumentRetriever
from backend.app.adapters.market_data_provider import RealMarketDataProvider
from backend.app.domain.ai_orchestration import AIIntent, AIOrchestrator
from backend.app.ports.market_data import Quote


@pytest.mark.live
@pytest.mark.asyncio
async def test_live_external_market_ingestion_with_source_evidence():
    """Demonstrate external market ingestion with real source evidence and hash verification."""
    provider = RealMarketDataProvider(force_cache=False, allow_fixture_fallback=False)

    # Ingest RELIANCE from public market data API
    quote = await provider.get_latest_quote("RELIANCE")
    assert quote is not None, "Failed to retrieve quote from external provider"
    assert quote.canonical_id == "NSE:RELIANCE"
    assert quote.currency == "INR"
    assert quote.price > Decimal("0")
    assert quote.source == "yahoo_finance_public_v8"
    assert "https://query1.finance.yahoo.com" in quote.source_uri
    assert quote.source_evidence is not None
    assert len(quote.source_evidence) == 64  # SHA-256 hexadecimal string
    assert quote.served_from_cache is False
    assert quote.observed_at is not None
    assert quote.ingested_at is not None


@pytest.mark.asyncio
async def test_source_outage_and_staleness_failover():
    """Demonstrate source-outage behavior: served from cache with recalculated freshness, or 404 when un-cached."""
    provider = RealMarketDataProvider(force_cache=False, allow_fixture_fallback=False)

    # 1. Warm cache with a known quote
    test_obs_time = datetime(2026, 10, 10, 10, 0, 0, tzinfo=timezone.utc)
    old_quote = Quote(
        canonical_id="NSE:INFY",
        symbol="INFY.NS",
        price=Decimal("1450.00"),
        currency="INR",
        observed_at=test_obs_time,
        ingested_at=datetime.now(timezone.utc),
        source="test_origin",
        source_uri="urn:test:infy",
        source_evidence="a" * 64,
        served_from_cache=False,
        is_delayed=False,
        is_stale=False,
        data_status="fresh",
    )
    provider.set_quote_override("INFY", old_quote)

    # 2. Simulate source outage
    provider.simulate_source_outage(True)

    # 3. Request INFY during outage -> must be served from cache and freshness dynamically recalculated as stale
    cached_quote = await provider.get_latest_quote("INFY")
    assert cached_quote is not None
    assert cached_quote.served_from_cache is True
    assert cached_quote.is_stale is True  # Because test_obs_time is > 24 hours ago
    assert cached_quote.data_status == "stale"

    # 4. Request an un-cached symbol during outage without fixture fallback -> returns None (explicit 404)
    provider.clear_cache()
    missing_quote = await provider.get_latest_quote("TATAMOTORS")
    assert missing_quote is None, "Should not fabricate synthetic prices during source outage"

    # Restore outage state
    provider.simulate_source_outage(False)


@pytest.mark.asyncio
async def test_official_document_ingestion_indexing_and_grounded_answer():
    """Demonstrate official document ingestion, hashing, indexing, retrieval, and grounded answer with citations."""
    official_doc = {
        "document_id": "SEBI-CIR-2026-99",
        "title": "SEBI Master Circular on Surveillance and Risk Containment in Equity Markets",
        "publisher": "Securities and Exchange Board of India",
        "source_url": "https://www.sebi.gov.in/legal/circulars/oct-2026/risk-containment.html",
        "document_date": "2026-10-01",
        "sections": [
            {
                "section": "Clause 4.2: Real-Time Price Band & Volatility Limits",
                "page_number": 14,
                "content": (
                    "Recognized stock exchanges must apply dynamic price bands of 10% on scrips in the Trade-for-Trade segment. "
                    "In the event of an extraordinary market-wide index movement of 15% or more before 1:00 PM, trading shall be "
                    "halted across all cash and derivative segments for a mandatory cooling period of 45 minutes."
                ),
            }
        ],
    }

    # 1. Ingest document payload
    chunks = ingest_document_payload(official_doc)
    assert len(chunks) == 1
    chk = chunks[0]
    assert chk.document_id == "SEBI-CIR-2026-99"
    assert chk.page_number == 14
    assert chk.content_hash == hashlib.sha256(chk.content.encode("utf-8")).hexdigest()

    # 2. Index into retriever
    retriever = RegulatoryDocumentRetriever(chunks=chunks)
    matched_chunks = await retriever.retrieve_relevant_chunks("price band cooling period trading halt", top_k=1)
    assert len(matched_chunks) == 1
    assert matched_chunks[0].chunk_id == chk.chunk_id
    assert matched_chunks[0].score > 0.0

    # 3. Generate grounded answer via AI Orchestrator
    orchestrator = AIOrchestrator(retriever=retriever)
    resp = await orchestrator.answer_query("What are the trading halt and price band rules under SEBI?")
    assert resp.intent == AIIntent.FINANCIAL_EDUCATION
    assert resp.is_fallback is False
    assert len(resp.citations) >= 1
    citation = resp.citations[0]
    assert citation.document_id == "SEBI-CIR-2026-99"
    assert citation.page_number == 14
    assert "Securities and Exchange Board of India" in citation.publisher
    assert "Trade-for-Trade" in resp.content or "price band" in resp.content.lower()


@pytest.mark.asyncio
async def test_insufficient_evidence_withholds_ungrounded_speculation():
    """Demonstrate that queries lacking official regulatory corpus evidence return INSUFFICIENT_EVIDENCE."""
    retriever = RegulatoryDocumentRetriever(chunks=ingest_corpus_documents())
    orchestrator = AIOrchestrator(retriever=retriever)

    # Query with nonexistent terms in regulatory corpus
    resp = await orchestrator.answer_query("how to mine interstellar helium cryptocurrency tokens on mars")
    assert resp.intent == AIIntent.INSUFFICIENT_EVIDENCE
    assert resp.is_fallback is True
    assert len(resp.citations) == 0
    assert "could not find sufficiently verified regulatory filings" in resp.content.lower()
