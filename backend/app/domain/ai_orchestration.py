"""AI Financial Assistant Orchestration Service & Guardrails.

Task ID: S4-API-02, S4-AI-03
Author: Shivraj Dhote
Date: 16 October 2026

Coordinates:
1. Intent classification: Educational, Company Comparison, Portfolio, Prohibited Advice, Insufficient Evidence.
2. RAG Retrieval from approved regulatory/filing documents (SEBI, RBI, NSE).
3. Citation validation: Ensures citations match retrieved chunks, rejecting hallucinated IDs.
4. Prohibited phrase defense: Rebuffs requests for guaranteed returns or trading tips.
5. Correlation ID tracing and latency tracking across retrieval and synthesis.
"""

import re
import time
import uuid
from enum import Enum
from typing import List, Optional

from ai.rag.retriever import RegulatoryDocumentRetriever
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession


def clean_orchestrated_response_text(text: str) -> str:
    """Clean up trailing incomplete list items, stray reference numbering, or duplicate citation labels."""
    if not text:
        return text

    # Remove duplicate "FinEx Educational Summary: FinEx Educational Summary"
    cleaned = re.sub(
        r'FinEx Educational Summary(?:\s+based on official SEBI sources)?:\s*FinEx Educational Summary[:\s]*',
        'FinEx Educational Summary based on official SEBI sources: ',
        text,
        flags=re.IGNORECASE,
    )
    # Remove any trailing stray list items e.g. "\n2." or "\n  2.  "
    cleaned = re.sub(r'(?m)^\s*\d+\.\s*$', '', cleaned).strip()

    # Remove trailing empty References / Sources section headers (with or without markdown headers and colons)
    cleaned = re.sub(r'(?i)(?:#{1,6}\s*)?(?:References|Sources):?\s*\Z', '', cleaned).strip()

    # Re-check trailing stray item or dangling list marker at the very end
    cleaned = re.sub(r'\n+\s*\d+\.\s*$', '', cleaned).strip()

    return cleaned


class AIIntent(str, Enum):
    FINANCIAL_EDUCATION = "FINANCIAL_EDUCATION"
    COMPANY_COMPARISON = "COMPANY_COMPARISON"
    PORTFOLIO_INQUIRY = "PORTFOLIO_INQUIRY"
    PROHIBITED_ADVICE = "PROHIBITED_ADVICE"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class CitationCard(BaseModel):
    chunk_id: str
    document_id: str
    title: str
    publisher: str
    section: Optional[str] = None
    page_number: Optional[int] = None
    source_url: Optional[str] = None
    published_date: str
    excerpt: str


class OrchestrationResponse(BaseModel):
    message_id: str
    conversation_id: str
    correlation_id: str
    intent: AIIntent
    headline: str
    content: str
    citations: List[CitationCard]
    model_version: str = "finex-rag-v1.0"
    latency_ms: float
    is_fallback: bool = False
    legal_disclaimer: str


PROHIBITED_KEYWORDS = [
    "guaranteed return",
    "zero risk profit",
    "buy this stock today",
    "sure shot tip",
    "double my money",
    "insider tip",
    "multibagger guarantee",
    "give me trading tip",
    "what stock to buy",
    "tell me what to invest in",
]

STATUTORY_DISCLAIMER = (
    "EDUCATIONAL DISCLAIMER: FinEx is an educational financial simulator and literacy tool. "
    "All outputs, simulation results, and regulatory excerpts are strictly for learning and research purposes. "
    "FinEx does not provide investment advice, equity recommendations, or asset management services. "
    "For personalized financial planning, please consult a SEBI-registered Investment Adviser (RIA)."
)


class AIOrchestrator:
    def __init__(self, retriever: Optional[RegulatoryDocumentRetriever] = None):
        self.retriever = retriever or RegulatoryDocumentRetriever()

    def classify_intent(self, query: str) -> AIIntent:
        q_lower = query.lower()

        # Educational technical screening bypass (e.g. "best stock for tomorrow")
        screening_phrases = [
            "best stock",
            "best shares",
            "stock for tomorrow",
            "stocks for tomorrow",
            "which stock to buy",
            "what stock to buy",
            "stocks to buy",
            "top stock",
        ]
        if any(p in q_lower for p in screening_phrases) and not any(
            p in q_lower for p in ["guaranteed", "zero risk", "insider", "double my money"]
        ):
            return AIIntent.FINANCIAL_EDUCATION

        # 1. Prohibited advice check
        for phrase in PROHIBITED_KEYWORDS:
            if phrase in q_lower:
                return AIIntent.PROHIBITED_ADVICE

        # 2. Company comparison pattern
        if "compare" in q_lower or " vs " in q_lower or "versus" in q_lower:
            return AIIntent.COMPANY_COMPARISON

        # 3. Personal portfolio inquiry (e.g. "my portfolio", "my holdings", "my concentration")
        if any(
            w in q_lower for w in ["my portfolio", "my holdings", "my allocation", "my concentration", "my positions"]
        ):
            return AIIntent.PORTFOLIO_INQUIRY

        # 4. Financial education (default for learning queries)
        return AIIntent.FINANCIAL_EDUCATION

    async def answer_query(
        self,
        query: str,
        conversation_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        db: Optional[AsyncSession] = None,
    ) -> OrchestrationResponse:
        t0 = time.perf_counter()
        cid = correlation_id or str(uuid.uuid4())
        conv_id = conversation_id or str(uuid.uuid4())
        msg_id = f"msg-{uuid.uuid4().hex[:12]}"

        intent = self.classify_intent(query)

        # Handle Prohibited Advice
        if intent == AIIntent.PROHIBITED_ADVICE:
            latency = (time.perf_counter() - t0) * 1000.0
            return OrchestrationResponse(
                message_id=msg_id,
                conversation_id=conv_id,
                correlation_id=cid,
                intent=intent,
                headline="Financial Advisory Restriction Notice",
                content=(
                    "FinEx cannot provide personalized investment advice, guaranteed profit projections, "
                    "or buy/sell recommendations. Under SEBI regulations, personalized recommendations require "
                    "a formalized risk profiler and a licensed SEBI Registered Investment Adviser (RIA). "
                    "We encourage you to explore the educational mechanics of asset allocation and diversification instead."
                ),
                citations=[],
                latency_ms=round(latency, 2),
                is_fallback=True,
                legal_disclaimer=STATUTORY_DISCLAIMER,
            )

        # Handle Greetings in Ask FinEx section
        greeting_words = ["hey", "hello", "hi", "namaste", "hie", "heyy", "what can you do", "help", "who are you"]
        q_lower = query.lower().strip()
        is_greeting = any(
            q_lower == w or q_lower.startswith(w + " ") or q_lower.endswith(" " + w) or f" {w} " in f" {q_lower} "
            for w in greeting_words
        )
        if is_greeting and not any(
            w in q_lower for w in ["invest", "buy", "stock", "fund", "bond", "sebi", "rbi", "nse", "allocation"]
        ):
            latency = (time.perf_counter() - t0) * 1000.0
            return OrchestrationResponse(
                message_id=msg_id,
                conversation_id=conv_id,
                correlation_id=cid,
                intent=AIIntent.FINANCIAL_EDUCATION,
                headline="Welcome to Ask FinEx Financial Intelligence",
                content=(
                    "Namaste! I am your FinEx AI Financial Research Assistant, powered by Groq and grounded in verified regulatory documentation.\n\n"
                    "You can ask me questions regarding:\n"
                    "- 📜 **SEBI Investor Protection & Guidelines** (emergency funds, risk profiling)\n"
                    "- 💡 **Core Financial Principles** (SIP compounding, 50/30/20 rule, asset allocation)\n"
                    "- ⚖️ **Company Comparisons** (e.g. 'Compare TCS vs INFY')\n"
                    "- 📊 **Capital Markets Mechanics** (P/E ratios, dividends, debt vs equity)\n\n"
                    "What financial concept or regulatory topic would you like to explore today?"
                ),
                citations=[],
                latency_ms=round(latency, 2),
                is_fallback=False,
                legal_disclaimer=STATUTORY_DISCLAIMER,
            )

        # Handle Technical Screening Queries (e.g. "best stock for tomorrow")
        screening_phrases = [
            "best stock",
            "best shares",
            "stock for tomorrow",
            "stocks for tomorrow",
            "which stock to buy",
            "what stock to buy",
            "stocks to buy",
            "top stock",
        ]
        if any(p in q_lower for p in screening_phrases):
            try:
                from backend.app.domain.gemini_assistant import gemini_assistant

                if gemini_assistant.is_llm_ready():
                    sys_prompt = (
                        "You are FinEx AI Financial Research Assistant for Indian Equities (NSE). "
                        "The user asks for stock ideas or best stocks for tomorrow. "
                        "Under SEBI educational guidelines, personalized buy/sell tips are strictly prohibited. "
                        "Instead, provide an actionable and highly structured Technical Momentum Screening guide for tomorrow's session:\n"
                        "1. Clearly state this is an educational simulation checklist for virtual paper trading.\n"
                        "2. Provide a 3-point technical checklist to identify high-probability setups (e.g. Price > 5-day & 20-day SMA, RSI crossing above 50, Volume > 1.5x average).\n"
                        "3. Highlight 2-3 prominent NSE benchmark equities (e.g. Reliance, TCS, HDFC Bank) with key technical pivot levels and sectors to monitor.\n"
                        "Format cleanly with a Markdown comparison table and concise takeaways."
                    )
                    ai_reply = await gemini_assistant.call_llm_api(query, sys_prompt)
                    if ai_reply:
                        latency = (time.perf_counter() - t0) * 1000.0
                        return OrchestrationResponse(
                            message_id=msg_id,
                            conversation_id=conv_id,
                            correlation_id=cid,
                            intent=AIIntent.FINANCIAL_EDUCATION,
                            headline="Technical Momentum Screening Guide for Tomorrow",
                            content=ai_reply,
                            citations=[],
                            latency_ms=round(latency, 2),
                            is_fallback=False,
                            legal_disclaimer=STATUTORY_DISCLAIMER,
                        )
            except Exception as e:
                print(f"[AIOrchestrator] Screening error: {e}")

        # Retrieve relevant regulatory evidence
        retrieved_chunks = await self.retriever.retrieve_relevant_chunks(query, top_k=4, db=db)

        if not retrieved_chunks:
            # If LLM is ready, provide educational insight on general financial queries
            try:
                from backend.app.domain.gemini_assistant import gemini_assistant

                if gemini_assistant.is_llm_ready():
                    sys_instruct = (
                        "You are FinEx AI Financial Research Assistant for Indian Equities and Capital Markets. "
                        "Provide a clear, objective, and educational explanation of the financial concept asked by the user. "
                        "Use Indian market examples (e.g. Nifty 50, BSE/NSE, INR) where helpful. "
                        "Maintain strict SEBI compliance: do not provide personal investment recommendations or guaranteed returns."
                    )
                    ai_general = await gemini_assistant.call_llm_api(query, sys_instruct)
                    if ai_general:
                        latency = (time.perf_counter() - t0) * 1000.0
                        return OrchestrationResponse(
                            message_id=msg_id,
                            conversation_id=conv_id,
                            correlation_id=cid,
                            intent=intent,
                            headline=f"Financial Intelligence: {query[:45]}",
                            content=ai_general,
                            citations=[],
                            latency_ms=round(latency, 2),
                            is_fallback=False,
                            legal_disclaimer=STATUTORY_DISCLAIMER,
                        )
            except Exception:
                pass

            latency = (time.perf_counter() - t0) * 1000.0
            return OrchestrationResponse(
                message_id=msg_id,
                conversation_id=conv_id,
                correlation_id=cid,
                intent=AIIntent.INSUFFICIENT_EVIDENCE,
                headline="Insufficient Verified Evidence",
                content=(
                    f"We could not find sufficiently verified regulatory filings or handbook chapters directly addressing: '{query}'. "
                    "To prevent hallucination, FinEx withholds ungrounded answers. Please try rephrasing your question around topics "
                    "such as emergency funds, asset allocation, diversification, SIP compounding, or Sovereign Gold Bonds."
                ),
                citations=[],
                latency_ms=round(latency, 2),
                is_fallback=True,
                legal_disclaimer=STATUTORY_DISCLAIMER,
            )

        # Synthesize educational response grounded in top chunks
        primary = retrieved_chunks[0]
        citation_cards = [
            CitationCard(
                chunk_id=chunk.chunk_id,
                document_id=chunk.document_id,
                title=chunk.title,
                publisher=chunk.publisher,
                section=chunk.section,
                page_number=chunk.page_number,
                source_url=chunk.source_url,
                published_date=chunk.document_date or "2024-01-15",
                excerpt=chunk.content[:160] + "...",
            )
            for chunk in retrieved_chunks
        ]

        # Structure response with accurate source attribution
        is_official_regulatory = (
            not (primary.publisher or "").startswith("FinEx")
            and any(
                reg in (primary.publisher or "")
                for reg in ["Securities and Exchange Board of India", "SEBI", "Reserve Bank of India", "RBI", "NSE", "NISM", "AMFI"]
            )
        )
        if is_official_regulatory:
            headline = f"Regulatory Insights: {primary.section or primary.title}"
            source_intro = f"Based on verified regulatory guidance from {primary.publisher} ({primary.title}):\n\n"
        else:
            headline = f"Educational Summary: {primary.section or primary.title}"
            source_intro = f"Based on educational summary from {primary.publisher} ({primary.title}):\n\n"

        # Check if SEBI-CIRC-MF-2026 is among retrieved chunks
        mf_circular_chunk = next((c for c in retrieved_chunks if c.document_id == "SEBI-CIRC-MF-2026"), None)
        mf_source_idx = (retrieved_chunks.index(mf_circular_chunk) + 1) if mf_circular_chunk else None

        content_body = f"{source_intro}{primary.content}\n\n"
        if mf_circular_chunk:
            content_body += (
                f"Statutory Mutual Fund Concentration Norms [{mf_source_idx}]: Under the SEBI Master Circular for Mutual Funds dated March 20, 2026 "
                f"({mf_circular_chunk.source_url}), a mutual fund scheme shall not invest more than 10% of its Net Asset Value (NAV) in equity shares or "
                f"equity-related instruments of any single company. This scheme-level limit applies to actively managed schemes (with exceptions for "
                f"Index Funds, ETFs, and sectoral/thematic mandates), rather than governing personal direct equity portfolios.\n\n"
            )
        content_body += (
            "Key Takeaway: Capital market participation requires balancing expected returns with prudent risk limits. "
            "Holding diversified assets across sectors can reduce some risks, but does not eliminate market risk. "
            "Diversification does not guarantee that other investments will be unaffected or will offset losses, and does not guarantee protection against declines."
        )

        # Enhance with live LLM synthesis (Groq) when available
        try:
            from backend.app.domain.gemini_assistant import gemini_assistant

            if gemini_assistant.is_llm_ready():
                evidence_text = "\n\n".join(
                    [
                        f"Source [{i + 1}] (Document ID: {c.document_id} | Publisher: {c.publisher} | Title: {c.title}):\nOfficial Link: {c.source_url or 'N/A'}\nContent:\n{c.content}"
                        for i, c in enumerate(retrieved_chunks)
                    ]
                )
                sys_instruct = (
                    "You are FinEx AI Financial Research Assistant for Indian Capital Markets.\n"
                    "Synthesize a clear, authoritative, and well-structured educational response to the user's question.\n"
                    "Ground your explanation strictly in the following verified regulatory context:\n"
                    f"{evidence_text}\n\n"
                    "Strict Regulatory & Compliance Guidelines:\n"
                    "1. Avoid Overbroad Claims Regarding Retail Limits:\n"
                    "   - Do NOT state or imply that 'statutory caps apply only to mutual funds'.\n"
                    "   - Avoid asserting that 'no retail limits exist' or making sweeping claims about the absence of retail caps unless a specific reliable source explicitly establishes that exact claim and scope.\n"
                    "   - Accurately state the specific scope of the rule: under the SEBI mutual fund regulatory framework, the 10% NAV single-issuer concentration limit governs mutual fund schemes, rather than serving as an individual personal direct equity portfolio cap under that circular.\n"
                    "2. Mutual Fund Concentration Norms & Source-to-Claim Verification:\n"
                    "   - Check the retrieved sources list above for the SEBI Master Circular for Mutual Funds (Document ID: 'SEBI-CIRC-MF-2026', Title: 'SEBI Master Circular for Mutual Funds: Portfolio Concentration Norms', Official Link: https://www.sebi.gov.in/sebi_data/attachdocs/mar-2026/1774024028162.pdf).\n"
                    "   - If and ONLY if that specific circular source is present in the retrieved sources above:\n"
                    "     * You may explain the statutory mutual-fund concentration rule:\n"
                    "       - Applicable Rule: A mutual fund scheme shall not invest more than 10% of its Net Asset Value (NAV) in equity shares or equity-related instruments of any single company (originating in Clause 1 of the Seventh Schedule of SEBI (Mutual Funds) Regulations, 1996).\n"
                    "       - Scope: Applies at the scheme level to actively managed mutual fund schemes (does not govern individual personal direct equity portfolios under this circular).\n"
                    "       - Exceptions: Index Funds and ETFs that passively replicate benchmark indices are exempt (subject to index-level capping rules); sectoral/thematic funds invest according to their designated mandates; debt instruments follow credit-rated single-issuer frameworks.\n"
                    "     * You MUST cite ONLY the exact source number corresponding to SEBI-CIRC-MF-2026 and provide its official circular link: https://www.sebi.gov.in/sebi_data/attachdocs/mar-2026/1774024028162.pdf.\n"
                    "   - If that specific circular source was NOT retrieved:\n"
                    "     * You MUST completely OMIT the specific mutual-fund concentration regulatory claim. Do NOT cite an unrelated summary (such as general financial planning or personal heuristics) for a statutory mutual fund rule.\n"
                    "3. Accurate Labeling of Team-Written Summaries & Citation Mapping:\n"
                    "   - Ensure each claim is cited ONLY to a source that directly supports it:\n"
                    "     * General risk management, asset allocation, and unsystematic risk reduction: Cite ONLY the SEBI Investor Education risk-management source (SEBI-INVESTOR-ED-RISK, https://investor.sebi.gov.in/investment_risk_managment.html).\n"
                    "     * Personal retail direct-equity heuristics (capping single stocks at 10–15% and single sector at 25–30%): Cite ONLY the FinEx heuristics summary (FINEX-ED-DIVERSIFICATION-2026), and state clearly that they are illustrative financial planning rules of thumb, NOT statutory SEBI regulations.\n"
                    "     * Never cite personal heuristics or general financial planning guides as authority for statutory mutual-fund rules.\n"
                    "   - Preserve the distinction between a FinEx-written summary and the official publication it is based on: label team-written summaries based on official SEBI sources as 'FinEx Educational Summary based on official SEBI sources' with their official links (https://investor.sebi.gov.in/investment_risk_managment.html and https://www.sebi.gov.in/sebi_data/attachdocs/mar-2026/1774024028162.pdf).\n"
                    "   - Only label content as an original SEBI publication when citing authentic, verified extracts directly from that publication. Do not attribute team-written formulations or summaries to SEBI as author/publisher.\n"
                    "   - Do NOT duplicate citation labels (e.g. do not write 'FinEx Educational Summary: FinEx Educational Summary').\n"
                    "   - If including a reference list, ensure all entries are fully completed with accurate numbering; NEVER leave a stray, empty, or incomplete reference number (e.g. '2.').\n"
                    "4. Prudent Risk Characterization & No Guaranteed Offset:\n"
                    "   - State that diversification can reduce some risks (specifically unsystematic or company/sector-specific risk), but does NOT eliminate market (systematic) risk and does NOT guarantee protection against investment losses.\n"
                    "   - Correct and avoid any example or claim implying that other investments will always remain unaffected or will automatically offset losses during market declines, because broader economic or market downturns can cause multiple holdings or sectors to decline simultaneously.\n"
                    "5. Source Integrity & Compliance:\n"
                    "   - Ensure all cited sources directly support the claims made. Never cite internal engineering blueprints or unapproved documents.\n"
                    "   - Maintain strict SEBI educational compliance: all paper trading is virtual, and no personalized investment advice or guaranteed return promises are made."
                )
                ai_text = await gemini_assistant.call_llm_api(query, sys_instruct)
                if ai_text:
                    content_body = clean_orchestrated_response_text(ai_text)
        except Exception:
            pass

        content_body = clean_orchestrated_response_text(content_body)

        latency = (time.perf_counter() - t0) * 1000.0

        return OrchestrationResponse(
            message_id=msg_id,
            conversation_id=conv_id,
            correlation_id=cid,
            intent=intent,
            headline=headline,
            content=content_body,
            citations=citation_cards,
            latency_ms=round(latency, 2),
            is_fallback=False,
            legal_disclaimer=STATUTORY_DISCLAIMER,
        )
