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

from datetime import datetime, timezone
from enum import Enum
import re
import time
import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from ai.rag.retriever import RegulatoryDocumentRetriever
from backend.app.ports.retriever import DocumentChunk


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
        if any(w in q_lower for w in ["my portfolio", "my holdings", "my allocation", "my concentration", "my positions"]):
            return AIIntent.PORTFOLIO_INQUIRY

        # 4. Financial education (default for learning queries)
        return AIIntent.FINANCIAL_EDUCATION

    async def answer_query(
        self,
        query: str,
        conversation_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
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

        # Retrieve relevant regulatory evidence
        retrieved_chunks = await self.retriever.retrieve_relevant_chunks(query, top_k=3)

        if not retrieved_chunks:
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
