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

    # 2. Must clarify that the circular rule does not govern individual personal direct equity portfolios
    assert "no statutory percentage holding limits" in content_lower or \
           "sebi regulations do not prescribe mandatory percentage" in content_lower or \
           "not as a statutory sebi regulation" in content_lower or \
           "does not apply to individual" in content_lower or \
           "does not govern individual" in content_lower or \
           "illustrative" in content_lower

    # 3. Must accurately explain mutual fund concentration limits with current Master Circular, historical context, scope and exceptions
    assert "master circular for mutual funds" in content_lower or "seventh schedule" in content_lower or "1774024028162.pdf" in content_lower
    assert "actively managed mutual fund schemes" in content_lower or "mutual fund scheme" in content_lower
    assert "does not apply to individual" in content_lower or "does not govern individual" in content_lower
    assert "index funds" in content_lower or "etfs" in content_lower

    # 4. Must describe diversification as reducing some risks, not guaranteeing protection against losses
    assert "reduces some risks" in content_lower or "reduce some risks" in content_lower or "unsystematic" in content_lower
    assert "not guarantee protection against" in content_lower or "does not eliminate market risk" in content_lower

    # 5. Verified citations must include FinEx educational summary and NEVER reference internal blueprints
    doc_ids = [cit.document_id for cit in resp.citations]
    assert "SEBI-ED-2024-01" in doc_ids
    for cit in resp.citations:
        assert "blueprint" not in cit.title.lower()
        assert "sprint plan" not in cit.title.lower()


@pytest.mark.asyncio
async def test_returned_citation_publisher_source_link_and_attribution():
    """Verify returned citations and content provenance:
    - Project-written content is strictly labelled 'FinEx Educational Summary', never original SEBI.
    - Official SEBI risk management is registered separately, linking to official portal without false retail limit claims.
    - Official mutual fund circular is registered separately, linking directly to the official Master Circular PDF.
    - FinEx heuristics are labelled 'FinEx Educational Summary'."""
    retriever = RegulatoryDocumentRetriever(chunks=ingest_corpus_documents())
    orchestrator = AIOrchestrator(retriever=retriever)

    # 1. Project-written educational summary provenance check
    resp_sebi = await orchestrator.answer_query("What is the recommended emergency fund and asset allocation?")
    assert len(resp_sebi.citations) >= 1
    ed_cit = [c for c in resp_sebi.citations if c.document_id == "SEBI-ED-2024-01"][0]
    assert ed_cit.publisher == "FinEx Educational Summary"
    assert "FinEx Educational Summary" in ed_cit.title
    assert ed_cit.publisher != "Securities and Exchange Board of India (SEBI)"
    assert ed_cit.source_url == "local://finex/educational-summary/financial-planning"

    # 2. SEBI risk management explanation provenance check
    resp_risk = await orchestrator.answer_query("How to manage investment risks in capital markets according to SEBI?")
    assert len(resp_risk.citations) >= 1
    sebi_risk_cits = [c for c in resp_risk.citations if c.document_id == "SEBI-INVESTOR-ED-RISK"]
    assert len(sebi_risk_cits) > 0
    risk_cit = sebi_risk_cits[0]
    assert risk_cit.publisher == "Securities and Exchange Board of India (SEBI)"
    assert "How to Manage Investment Risks" in risk_cit.title
    assert risk_cit.source_url == "https://investor.sebi.gov.in/investment_risk_managment.html"
    assert risk_cit.page_number is None  # Unpaged web source has no page number
    # Must NOT claim this page proves a broad absence of statutory retail limits
    assert "statutory percentage holding limits" not in risk_cit.excerpt.lower()

    # 3. Mutual Fund concentration norms explanation provenance check
    resp_mf = await orchestrator.answer_query("What are mutual fund concentration limits according to SEBI?")
    assert len(resp_mf.citations) >= 1
    mf_cit = [c for c in resp_mf.citations if c.document_id == "SEBI-CIRC-MF-2026"][0]
    assert mf_cit.publisher == "Securities and Exchange Board of India (SEBI)"
    assert "SEBI Master Circular" in mf_cit.title
    assert mf_cit.source_url == "https://www.sebi.gov.in/sebi_data/attachdocs/mar-2026/1774024028162.pdf"
    assert mf_cit.page_number is None  # Unverified page number removed

    # 4. Verified content chunks inspection
    chunks = ingest_corpus_documents()
    sebi_risk_chunks = [c for c in chunks if c.document_id == "SEBI-INVESTOR-ED-RISK"]
    assert len(sebi_risk_chunks) > 0
    sr_chk = sebi_risk_chunks[0]
    assert "https://investor.sebi.gov.in/investment_risk_managment.html" in sr_chk.content
    assert "does not eliminate market risk" in sr_chk.content.lower()
    assert "no statutory percentage holding limits" not in sr_chk.content.lower()
    assert "statutory caps apply only to mutual funds" not in sr_chk.content.lower()

    mf_chunks = [c for c in chunks if c.document_id == "SEBI-CIRC-MF-2026"]
    assert len(mf_chunks) > 0
    mf_chk = mf_chunks[0]
    assert "https://www.sebi.gov.in/sebi_data/attachdocs/mar-2026/1774024028162.pdf" in mf_chk.content
    assert "Master Circular for Mutual Funds" in mf_chk.content
    assert "Clause 1 of the Seventh Schedule" in mf_chk.content
    assert "statutory caps apply only to mutual funds" not in mf_chk.content.lower()
    assert "actively managed mutual fund schemes" in mf_chk.content
    assert "Index Funds and Exchange Traded Funds (ETFs)" in mf_chk.content


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
            title="FinEx Educational Summary: Guide to Financial Planning & Regulatory Principles",
            publisher="FinEx Educational Summary",
            source_url="local://finex/educational-summary/financial-planning",
            section="Chapter 3: Asset Allocation and Diversification Principles",
            page_number=12,
            content="FinEx Educational Summary: Asset allocation and portfolio diversification are foundational risk-mitigation principles in securities markets.",
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
        assert "Avoid Overbroad Claims Regarding Retail Limits" in captured_sys_instruct
        assert "statutory caps apply only to mutual funds" in captured_sys_instruct
        assert "no retail limits exist" in captured_sys_instruct
        assert "SEBI Master Circular for Mutual Funds" in captured_sys_instruct
        assert "1774024028162.pdf" in captured_sys_instruct
        assert "investment_risk_managment.html" in captured_sys_instruct
        assert "Prudent Risk Characterization & No Guaranteed Offset" in captured_sys_instruct
        assert "unaffected or will offset losses" in captured_sys_instruct
        assert "FinEx Educational Summary" in captured_sys_instruct
        assert "Never cite internal engineering blueprints" in captured_sys_instruct


@pytest.mark.asyncio
async def test_sebi_explanation_source_labels_and_page_reference_removal():
    """Verify that SEBI regulatory records link to official sources, team explanations are labeled FinEx, and unverified page numbers are removed."""
    from ai.rag.corpus import REGULATORY_DOCUMENTS
    from ai.rag.ingestion import APPROVED_LOCAL_DOCUMENTS, extract_document_from_file, format_citation
    from backend.app.ports.retriever import DocumentChunk

    # 1. Check catalog entries
    doc_map = {d["document_id"]: d for d in APPROVED_LOCAL_DOCUMENTS}

    risk_meta = doc_map["SEBI-INVESTOR-ED-RISK"]
    assert risk_meta["publisher"] == "Securities and Exchange Board of India (SEBI)"
    assert "SEBI Investor Education" in risk_meta["title"]
    assert risk_meta["source_url"] == "https://investor.sebi.gov.in/investment_risk_managment.html"

    mf_meta = doc_map["SEBI-CIRC-MF-2026"]
    assert mf_meta["publisher"] == "Securities and Exchange Board of India (SEBI)"
    assert "SEBI Master Circular" in mf_meta["title"]
    assert mf_meta["source_url"] == "https://www.sebi.gov.in/sebi_data/attachdocs/mar-2026/1774024028162.pdf"

    # Team-written educational guides are labeled FinEx Educational Summary
    ed_meta = doc_map["SEBI-ED-2024-01"]
    assert ed_meta["publisher"] == "FinEx Educational Summary"
    assert "FinEx Educational Summary" in ed_meta["title"]

    heur_meta = doc_map["FINEX-ED-DIVERSIFICATION-2026"]
    assert heur_meta["publisher"] == "FinEx Educational Summary"
    assert "FinEx Educational Summary" in heur_meta["title"]

    # 2. Check extracted document files (verifying Page: 1 was removed and parsed as None)
    _, risk_sections = extract_document_from_file(risk_meta["local_file"])
    assert len(risk_sections) == 1
    assert risk_sections[0]["page_number"] is None
    assert "Official Publication: Securities and Exchange Board of India (SEBI) Investor Education" in risk_sections[0]["content"]
    assert "unaffected or will offset losses" in risk_sections[0]["content"]

    _, mf_sections = extract_document_from_file(mf_meta["local_file"])
    assert len(mf_sections) == 1
    assert mf_sections[0]["page_number"] is None  # Page 1 removed because Master Circular is 748 pages
    assert "Official Regulatory Publication: Securities and Exchange Board of India (SEBI) Master Circular" in mf_sections[0]["content"]
    assert "statutory caps apply only to mutual funds" not in mf_sections[0]["content"].lower()

    # 3. Check fallback corpus
    corpus_map = {d["document_id"]: d for d in REGULATORY_DOCUMENTS}
    c_risk = corpus_map["SEBI-INVESTOR-ED-RISK"]
    assert c_risk["publisher"] == "Securities and Exchange Board of India (SEBI)"
    assert c_risk["source_url"] == "https://investor.sebi.gov.in/investment_risk_managment.html"
    assert c_risk["sections"][0]["page_number"] is None

    c_mf = corpus_map["SEBI-CIRC-MF-2026"]
    assert c_mf["publisher"] == "Securities and Exchange Board of India (SEBI)"
    assert c_mf["source_url"] == "https://www.sebi.gov.in/sebi_data/attachdocs/mar-2026/1774024028162.pdf"
    assert c_mf["sections"][0]["page_number"] is None

    # 4. Check citation formatting for unpaged chunks
    chunk_unpaged = DocumentChunk(
        chunk_id="chk_test_01",
        document_id="SEBI-CIRC-MF-2026",
        title="SEBI Master Circular for Mutual Funds: Portfolio Concentration Norms",
        publisher="Securities and Exchange Board of India (SEBI)",
        source_url="https://www.sebi.gov.in/sebi_data/attachdocs/mar-2026/1774024028162.pdf",
        section="Section 1: Portfolio Concentration Limits for Mutual Fund Schemes",
        page_number=None,
        content="Test content",
        score=1.0,
    )
    formatted = format_citation(chunk_unpaged)
    assert "p." not in formatted
    assert "None" not in formatted
    assert formatted == "[SEBI Master Circular for Mutual Funds: Portfolio Concentration Norms, Section 1: Portfolio Concentration Limits for Mutual Fund Schemes]"


@pytest.mark.asyncio
async def test_regulatory_wording_no_broad_claims_and_accurate_circular_links():
    """Verify that:
    1. Broad claims ('statutory caps apply only to mutual funds', 'no retail limits exist') are eliminated.
    2. Mutual fund concentration claims link directly to the official circular PDF.
    3. Team explanations are labeled FinEx Educational Summary.
    4. Risk wording explicitly rejects guaranteed offset and affirms market risk remains."""
    retriever = RegulatoryDocumentRetriever(chunks=ingest_corpus_documents(include_educational_summaries=True))
    orchestrator = AIOrchestrator(retriever=retriever)

    resp = await orchestrator.answer_query("What are the diversification rules and single-stock exposure limits under SEBI regulations?")
    assert resp.intent == AIIntent.FINANCIAL_EDUCATION
    content_lower = resp.content.lower()

    # 1. Broad claim elimination
    assert "statutory caps apply only to mutual funds" not in content_lower
    assert "no retail limits exist" not in content_lower

    # 2. Citations verification
    citations_by_doc = {c.document_id: c for c in resp.citations}

    if "SEBI-CIRC-MF-2026" in citations_by_doc:
        mf_cit = citations_by_doc["SEBI-CIRC-MF-2026"]
        assert mf_cit.publisher == "Securities and Exchange Board of India (SEBI)"
        assert mf_cit.source_url == "https://www.sebi.gov.in/sebi_data/attachdocs/mar-2026/1774024028162.pdf"

    if "SEBI-INVESTOR-ED-RISK" in citations_by_doc:
        risk_cit = citations_by_doc["SEBI-INVESTOR-ED-RISK"]
        assert risk_cit.publisher == "Securities and Exchange Board of India (SEBI)"
        assert risk_cit.source_url == "https://investor.sebi.gov.in/investment_risk_managment.html"

    if "FINEX-ED-DIVERSIFICATION-2026" in citations_by_doc:
        finex_cit = citations_by_doc["FINEX-ED-DIVERSIFICATION-2026"]
        assert finex_cit.publisher == "FinEx Educational Summary"

    # 3. Prudent risk characterization
    assert "does not guarantee" in content_lower or "not eliminate market risk" in content_lower
    assert "unaffected or will offset losses" not in content_lower or "does not guarantee that other investments will be unaffected" in content_lower



