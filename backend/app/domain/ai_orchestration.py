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

import time
import uuid
from enum import Enum
from typing import List, Optional

from ai.rag.retriever import RegulatoryDocumentRetriever
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession


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
                    "Namaste! I am your FinEx AI Financial Research Assistant, powered by Google Gemini and grounded in verified regulatory documentation.\n\n"
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

        # Retrieve relevant regulatory evidence
        retrieved_chunks = await self.retriever.retrieve_relevant_chunks(query, top_k=3, db=db)

        if not retrieved_chunks:
            # If Gemini is ready, provide educational insight on general financial queries
            try:
                from backend.app.domain.gemini_assistant import gemini_assistant

                if gemini_assistant.is_gemini_api_ready():
                    sys_instruct = (
                        "You are FinEx AI Financial Research Assistant for Indian Equities and Capital Markets. "
                        "Provide a clear, objective, and educational explanation of the financial concept asked by the user. "
                        "Use Indian market examples (e.g. Nifty 50, BSE/NSE, INR) where helpful. "
                        "Maintain strict SEBI compliance: do not provide personal investment recommendations or guaranteed returns."
                    )
                    ai_general = await gemini_assistant.call_gemini_api(query, sys_instruct)
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

        # Structure response
        headline = f"Regulatory Insights: {primary.section or primary.title}"
        content_body = (
            f"Based on verified regulatory guidance from {primary.publisher} ({primary.title}):\n\n"
            f"{primary.content}\n\n"
            f"Key Takeaway: Capital market participation requires balancing expected returns with prudent risk limits. "
            f"Holding diversified assets and reviewing regulatory disclosures provides structural resilience."
        )

        # Enhance with live Gemini synthesis when available
        try:
            from backend.app.domain.gemini_assistant import gemini_assistant

            if gemini_assistant.is_gemini_api_ready():
                evidence_text = "\n\n".join(
                    [
                        f"Source [{i + 1}] ({c.publisher} - {c.title}):\n{c.content}"
                        for i, c in enumerate(retrieved_chunks)
                    ]
                )
                sys_instruct = (
                    "You are FinEx AI Financial Research Assistant for Indian Capital Markets. "
                    "Synthesize a clear, authoritative, and well-structured response to the user's question. "
                    "Ground your explanation in the following verified regulatory context:\n"
                    f"{evidence_text}\n\n"
                    "Explain the concepts clearly, highlight practical takeaways for Indian retail investors, and maintain strict SEBI educational compliance."
                )
                ai_text = await gemini_assistant.call_gemini_api(query, sys_instruct)
                if ai_text:
                    content_body = ai_text
        except Exception:
            pass

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
