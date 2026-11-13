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


@pytest.mark.asyncio
async def test_diversification_query_does_not_assert_unsupported_sebi_caps():
    """Verify diversification answer does not claim SEBI mandates percentage caps for retail investors."""
    retriever = RegulatoryDocumentRetriever(chunks=ingest_corpus_documents())
    orchestrator = AIOrchestrator(retriever=retriever)

    resp = await orchestrator.answer_query("What are the single stock and single sector limits under SEBI diversification rules?")
    assert resp.intent == AIIntent.FINANCIAL_EDUCATION
    assert resp.is_fallback is False
    assert len(resp.citations) >= 1

    content_lower = resp.content.lower()

    # 1. Must NOT claim SEBI mandates/recommends these caps as a rule for retail investors
    assert "sebi guidelines recommend capping single-stock" not in content_lower
    assert "sebi rules mandate 10%" not in content_lower

    # 2. Must explicitly clarify that SEBI does not prescribe mandatory caps for retail investors
    assert "no statutory percentage holding limits" in content_lower or \
           "sebi regulations do not prescribe mandatory percentage" in content_lower or \
           "not as a statutory sebi regulation" in content_lower or \
           "illustrative" in content_lower

    # 3. Must accurately explain mutual fund Seventh Schedule concentration limits with scope and exceptions
    assert "clause 1 of the seventh schedule" in content_lower or "seventh schedule" in content_lower
    assert "actively managed mutual fund schemes" in content_lower or "mutual fund scheme" in content_lower
    assert "does not apply to individual" in content_lower
    assert "index funds" in content_lower or "etfs" in content_lower

    # 4. Must describe diversification as reducing some risks, not guaranteeing protection against losses
    assert "reduces some risks" in content_lower or "reduce some risks" in content_lower or "unsystematic" in content_lower
    assert "not guarantee protection against" in content_lower or "does not eliminate market risk" in content_lower

    # 5. Verified citations must include SEBI education document and NEVER reference internal blueprints
    doc_ids = [cit.document_id for cit in resp.citations]
    assert "SEBI-ED-2024-01" in doc_ids
    for cit in resp.citations:
        assert "FINEX" not in cit.document_id
        assert "blueprint" not in cit.title.lower()
        assert "sprint plan" not in cit.title.lower()


@pytest.mark.asyncio
async def test_sebi_document_excludes_team_written_heuristics():
    """Verify the SEBI-attributed document contains only verified official guidance and excludes project heuristics."""
    chunks = ingest_corpus_documents()
    sebi_chunks = [c for c in chunks if c.document_id == "SEBI-ED-2024-01"]
    assert len(sebi_chunks) == 5

    ch3 = [c for c in sebi_chunks if "Diversification" in c.section][0]

    # Team-written heuristics (10-15% single-stock, 25-30% single-sector) must NOT be attributed to SEBI
    assert "10% to 15%" not in ch3.content
    assert "25% to 30%" not in ch3.content
    assert "capping single-stock" not in ch3.content.lower()

    # Must contain verified official SEBI mutual fund concentration limits and exceptions
    assert "Seventh Schedule of the SEBI (Mutual Funds) Regulations, 1996" in ch3.content
    assert "Clause 1" in ch3.content
    assert "actively managed mutual fund schemes" in ch3.content
    assert "Index Funds and Exchange Traded Funds (ETFs)" in ch3.content
    assert "does not apply to individual retail investors" in ch3.content

    # Must state diversification reduces some risks without guaranteeing protection against losses
    assert "reduces some risks" in ch3.content or "reduce some risks" in ch3.content
    assert "does not guarantee protection against investment losses" in ch3.content


@pytest.mark.asyncio
async def test_finex_educational_summary_source_attribution():
    """Verify FinEx educational summaries are clearly attributed to FinEx and never presented as SEBI documents."""
    from ai.rag.corpus import FINEX_EDUCATIONAL_DOCUMENTS

    all_chunks = ingest_corpus_documents(include_educational_summaries=True)
    finex_chunks = [c for c in all_chunks if c.document_id == "FINEX-ED-DIVERSIFICATION-2026"]
    assert len(finex_chunks) == 1

    chk = finex_chunks[0]
    assert chk.publisher == "FinEx Educational Summary"
    assert "FinEx Educational Summary" in chk.title
    assert "SEBI" not in chk.publisher

    # Orchestrator formats FinEx summary with Educational Summary headline, not Regulatory
    retriever = RegulatoryDocumentRetriever(chunks=[chk])
    orchestrator = AIOrchestrator(retriever=retriever)
    resp = await orchestrator.answer_query("What are FinEx diversification heuristics?")

    assert resp.headline.startswith("Educational Summary:")
    assert "Based on educational summary from FinEx Educational Summary" in resp.content
    assert len(resp.citations) == 1
    assert resp.citations[0].publisher == "FinEx Educational Summary"


@pytest.mark.asyncio
async def test_engineering_blueprint_excluded_from_retrieval_and_citations():
    """Verify that internal planning blueprints are never returned or cited to investors."""
    from backend.app.ports.retriever import DocumentChunk

    mixed_chunks = [
        DocumentChunk(
            chunk_id="chk_blueprint_01",
            document_id="FINEX-SOLO-SPRINT-PLAN-2026",
            title="FinEx Solo Project Blueprint and Real Data Sprint Plan",
            publisher="FinEx Engineering / Shivraj Dhote",
            source_url="file://FinEx_Shivraj_Solo_Real_Data_Sprint_Plan (1).pdf",
            section="Sprint 4: Portfolio Diversification Architecture",
            page_number=1,
            content="Architecture sprint plan for portfolio diversification and single-stock exposure calculation engine.",
            score=0.0,
        ),
        DocumentChunk(
            chunk_id="chk_sebi_01",
            document_id="SEBI-ED-2024-01",
            title="SEBI Guide to Financial Education for Beginners",
            publisher="Securities and Exchange Board of India (SEBI)",
            source_url="https://investor.sebi.gov.in/financial-education/beginners-guide.html",
            section="Chapter 3: Asset Allocation and Diversification Principles",
            page_number=12,
            content="Diversification is the primary protection against unsystematic risk in capital markets.",
            score=0.0,
        ),
    ]

    retriever = RegulatoryDocumentRetriever(chunks=mixed_chunks)
    results = await retriever.retrieve_relevant_chunks("portfolio diversification sprint plan architecture", top_k=5)

    # Blueprint chunk must be completely filtered out
    assert len(results) > 0
    for r in results:
        assert r.document_id != "FINEX-SOLO-SPRINT-PLAN-2026"
        assert "blueprint" not in r.title.lower()
        assert "sprint plan" not in r.title.lower()


@pytest.mark.asyncio
async def test_groq_synthesis_receives_anti_hallucination_diversification_instructions():
    """Verify system prompt passed to Groq contains explicit directives against inventing SEBI retail caps."""
    from unittest.mock import AsyncMock, patch
    from backend.app.domain.gemini_assistant import gemini_assistant

    retriever = RegulatoryDocumentRetriever(chunks=ingest_corpus_documents())
    orchestrator = AIOrchestrator(retriever=retriever)

    captured_sys_instruct = None

    async def mock_call_llm(prompt, sys_instruct):
        nonlocal captured_sys_instruct
        captured_sys_instruct = sys_instruct
        return (
            "According to SEBI investor education, diversification protects against unsystematic risk. "
            "SEBI does not prescribe mandatory percentage exposure limits for individual retail investors. "
            "Holding no more than 10-15% in a single stock is an illustrative financial planning rule of thumb, "
            "whereas statutory 10% caps apply to mutual fund schemes under SEBI regulations."
        )

    with patch.object(gemini_assistant, "is_llm_ready", return_value=True), \
         patch.object(gemini_assistant, "call_llm_api", side_effect=mock_call_llm):
        resp = await orchestrator.answer_query("Explain SEBI rules on 10% stock diversification")

        assert resp.intent == AIIntent.FINANCIAL_EDUCATION
        assert "does not prescribe mandatory percentage" in resp.content
        assert captured_sys_instruct is not None
        # Assert strict compliance prompt directives are present
        assert "Accurate Source Attribution" in captured_sys_instruct
        assert "Never attribute project-written explanations" in captured_sys_instruct
        assert "Clearly Label Educational Summaries" in captured_sys_instruct
        assert "Mutual Fund Concentration Limit Scope & Exceptions" in captured_sys_instruct
        assert "Prudent Risk Characterization" in captured_sys_instruct
        assert "Do NOT state or imply that SEBI mandates percentage holding caps" not in captured_sys_instruct or "SEBI does NOT prescribe mandatory percentage holding caps" in captured_sys_instruct
        assert "Never cite internal engineering blueprints" in captured_sys_instruct

