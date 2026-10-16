"""Portfolio Intent Router and Query Classifier.

Task ID: S6-AI-01
Author: Shivraj Dhote
Date: 16 October 2026

Coordinates:
1. Classifies portfolio conversational queries into a defined, documented intent taxonomy:
   - HOLDINGS
   - ALLOCATION
   - CONCENTRATION
   - PERFORMANCE
   - RISK
   - SCENARIO_STRESS_TEST
   - UNAUTHORIZED_ACCESS
   - UNSUPPORTED_ADVICE
2. Refuses cross-tenant data requests or unsupported investment advice.
3. Provides routing metadata and target deterministic tool recommendation.
"""

from enum import Enum
import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class PortfolioIntent(str, Enum):
    HOLDINGS = "HOLDINGS"
    ALLOCATION = "ALLOCATION"
    CONCENTRATION = "CONCENTRATION"
    PERFORMANCE = "PERFORMANCE"
    RISK = "RISK"
    SCENARIO_STRESS_TEST = "SCENARIO_STRESS_TEST"
    UNAUTHORIZED_ACCESS = "UNAUTHORIZED_ACCESS"
    UNSUPPORTED_ADVICE = "UNSUPPORTED_ADVICE"
    GENERAL_EDUCATIONAL = "GENERAL_EDUCATIONAL"


class IntentRoutingResult(BaseModel):
    query: str
    predicted_intent: PortfolioIntent
    confidence: float
    recommended_tool: Optional[str] = None
    is_supported: bool = True
    refusal_reason: Optional[str] = None
    educational_guidance: Optional[str] = None


class PortfolioIntentRouter:
    """Classifies user queries into deterministic intent pathways."""

    def route(self, query: str, caller_user_id: str = "usr-shivraj-001") -> IntentRoutingResult:
        q_lower = query.strip().lower()

        # 0. Prompt Injection / Jailbreak / Instruction Override check
        if any(p in q_lower for p in ["system prompt", "override", "jailbreak", "ignore all previous", "ignore previous", "forget what you were told", "internal credentials", "system update", "unrestricted"]):
            return IntentRoutingResult(
                query=query,
                predicted_intent=PortfolioIntent.UNAUTHORIZED_ACCESS,
                confidence=0.99,
                recommended_tool=None,
                is_supported=False,
                refusal_reason="System integrity violation: System prompts and internal configurations are immutable.",
                educational_guidance="FinEx operates strictly within educational guidelines and cannot override safety protocols.",
            )

        # 1. Unauthorized Access / Cross-user breach check
        if any(p in q_lower for p in ["other user", "another account", "usr-", "user 123", "admin view", "someone else"]):

            return IntentRoutingResult(
                query=query,
                predicted_intent=PortfolioIntent.UNAUTHORIZED_ACCESS,
                confidence=0.99,
                recommended_tool=None,
                is_supported=False,
                refusal_reason="Cross-tenant isolation policy: You may only query your own authenticated portfolio data.",
                educational_guidance="For privacy and security, FinEx isolates each user's financial records completely.",
            )

        # 2. Unsupported advice / return guarantee / tips check
        if any(p in q_lower for p in ["guarantee", "tip", "which stock to buy now", "tell me what to trade", "sure shot", "double money"]):
            return IntentRoutingResult(
                query=query,
                predicted_intent=PortfolioIntent.UNSUPPORTED_ADVICE,
                confidence=0.98,
                recommended_tool=None,
                is_supported=False,
                refusal_reason="SEBI Registered Investment Advisor constraint: FinEx cannot provide individualized stock tips or return guarantees.",
                educational_guidance="We can help you analyze your portfolio's allocation, concentration, and historical metrics to support your own informed decisions.",
            )

        # 3. Scenario / Stress Test (check before general sector queries)
        if any(p in q_lower for p in ["scenario", "stress test", "what if", "what happens if", "drop", "fall", "crash", "shock", "decline"]):
            return IntentRoutingResult(
                query=query,
                predicted_intent=PortfolioIntent.SCENARIO_STRESS_TEST,
                confidence=0.95,
                recommended_tool="portfolio_intelligence_service.run_scenario_stress_test",
                is_supported=True,
            )

        # 4. Concentration & HHI
        if any(p in q_lower for p in ["concentrat", "hhi", "top stock", "single stock risk", "overweight", "heavy in"]):
            return IntentRoutingResult(
                query=query,
                predicted_intent=PortfolioIntent.CONCENTRATION,
                confidence=0.94,
                recommended_tool="portfolio_intelligence_service.compute_intelligence",
                is_supported=True,
            )

        # 5. Asset Allocation & Sector Exposure
        if any(p in q_lower for p in ["allocation", "sector", "cash vs equity", "asset class", "exposure", "breakdown"]):
            return IntentRoutingResult(
                query=query,
                predicted_intent=PortfolioIntent.ALLOCATION,
                confidence=0.95,
                recommended_tool="portfolio_intelligence_service.compute_intelligence",
                is_supported=True,
            )

        # 6. Performance (gainers, losers, P&L, returns)
        if any(p in q_lower for p in ["performance", "gainers", "losers", "contributors", "detractors", "pnl", "profit", "loss", "return"]):
            return IntentRoutingResult(
                query=query,
                predicted_intent=PortfolioIntent.PERFORMANCE,
                confidence=0.92,
                recommended_tool="portfolio_intelligence_service.compute_intelligence",
                is_supported=True,
            )

        # 7. Risk & Diversification
        if any(p in q_lower for p in ["risk", "diversif", "volatility", "safe"]):
            return IntentRoutingResult(
                query=query,
                predicted_intent=PortfolioIntent.RISK,
                confidence=0.90,
                recommended_tool="portfolio_intelligence_service.compute_intelligence",
                is_supported=True,
            )

        # 8. Holdings (shares, positions, stock list)
        if any(p in q_lower for p in ["holding", "position", "stock", "what do i own", "share", "portfolio list"]):
            return IntentRoutingResult(
                query=query,
                predicted_intent=PortfolioIntent.HOLDINGS,
                confidence=0.93,
                recommended_tool="portfolio_service.get_portfolio_valuation",
                is_supported=True,
            )

        # Fallback to general educational financial exploration
        return IntentRoutingResult(
            query=query,
            predicted_intent=PortfolioIntent.GENERAL_EDUCATIONAL,
            confidence=0.80,
            recommended_tool="ai_orchestrator.answer_educational_query",
            is_supported=True,
            educational_guidance="You can ask about your holdings, asset allocation, sector exposure, top contributors, or run a 15% sector shock scenario.",
        )
