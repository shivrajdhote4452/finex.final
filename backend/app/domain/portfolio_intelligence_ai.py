"""Conversational Portfolio Explanation & Intelligence AI Pipeline.

Task ID: S6-AI-02
Author: Shivraj Dhote
Date: 16 October 2026

Coordinates:
1. Explains deterministic metrics (allocation, concentration, scenario stress test).
2. Incorporates user risk profile (Conservative, Moderate, Aggressive) to explain structural balance.
3. Educational rebalancing considerations without automatic order execution.
4. Strict statutory disclosures and preservation of all input values.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel

from backend.app.domain.portfolio_intelligence_service import PortfolioIntelligenceReport


class PortfolioExplanationResponse(BaseModel):
    headline: str
    narrative: str
    risk_profile_alignment: str
    scenario_interpretation: Optional[str] = None
    educational_considerations: List[str]
    disclaimer: str


AI_PORTFOLIO_CONVERSATION_DISCLAIMER = (
    "DISCLAIMER: This commentary is provided solely for financial literacy and educational self-evaluation. "
    "All figures are deterministically calculated from verified exchange and portfolio records. "
    "FinEx does not execute automatic rebalancing or issue registered investment recommendations."
)


def explain_portfolio_intelligence(
    report: PortfolioIntelligenceReport,
    risk_category: str = "MODERATE",
) -> PortfolioExplanationResponse:
    """Generates educational explanation grounded 100% in deterministic intelligence metrics."""
    tot = report.total_portfolio_value
    eq_pct = report.equity_weight_pct
    cash_pct = report.cash_weight_pct
    hhi = report.hhi_concentration_score
    top_sym = report.top_holding_symbol
    top_pct = report.top_holding_pct
    div_score = report.diversification_score

    headline = (
        f"Portfolio Intelligence Snapshot: ₹{tot:,.2f} | "
        f"Equity {eq_pct:.1f}% / Cash {cash_pct:.1f}% | "
        f"Diversification Score {div_score}/10"
    )

    # Risk alignment explanation
    risk_cat = risk_category.upper()
    if risk_cat == "CONSERVATIVE":
        if eq_pct > 60.0:
            risk_align = (
                f"Your equity allocation is {eq_pct:.1f}%, which is elevated compared to a conventional "
                "conservative benchmark (typically 20-40% equity, 60-80% debt/cash). "
                "Consider whether your cash buffer of ₹{report.cash_balance:,.2f} ({cash_pct:.1f}%) matches your planned emergency horizon."
            )
        else:
            risk_align = (
                f"Your equity allocation of {eq_pct:.1f}% aligns well with a conservative wealth preservation profile, "
                f"maintaining ₹{report.cash_balance:,.2f} ({cash_pct:.1f}%) in liquid virtual reserves."
            )
    elif risk_cat == "AGGRESSIVE":
        risk_align = (
            f"Your portfolio is positioned for capital growth with {eq_pct:.1f}% equity allocation. "
            f"With top holding {top_sym} representing {top_pct:.1f}% of total value, "
            "growth is concentrated in leading sector champions."
        )
    else:  # MODERATE
        risk_align = (
            f"Your current asset mix holds {eq_pct:.1f}% equity and {cash_pct:.1f}% virtual cash, "
            "providing balanced equity participation while retaining liquidity for potential market corrections."
        )

    # Narrative
    sec_str = ", ".join(f"{s.sector} ({s.weight_pct:.1f}%)" for s in report.sector_exposures[:3])
    narrative = (
        f"Your total portfolio stands at ₹{tot:,.2f}. Primary sector allocations are {sec_str}. "
        f"Single-stock concentration in {top_sym} is {top_pct:.1f}%, resulting in an HHI score of {hhi:.0f}."
    )

    # Scenario interpretation
    scenario_text = None
    if report.scenario_shock_15pct_it:
        sc = report.scenario_shock_15pct_it
        scenario_text = (
            f"Stress Test: Under a hypothetical 15% shock in {sc.target_sector}, "
            f"your portfolio would absorb an estimated impact of ₹{abs(sc.estimated_rupee_impact):,.2f}, "
            f"bringing simulated value to ₹{sc.post_shock_portfolio_value:,.2f}. "
            "This highlights the importance of sector diversification beyond a single industry."
        )

    considerations = [
        f"Asset Class Balance: Ensure the {cash_pct:.1f}% cash allocation matches short-term liquidity needs.",
        f"Concentration Guardrail: Top holding {top_sym} at {top_pct:.1f}% - prudential financial planning recommends limiting any single stock to under 20-25% of total net worth.",
        "Systematic Review: Conduct regular quarterly reviews of sector exposures rather than reacting to short-term daily volatility.",
    ]

    return PortfolioExplanationResponse(
        headline=headline,
        narrative=narrative,
        risk_profile_alignment=risk_align,
        scenario_interpretation=scenario_text,
        educational_considerations=considerations,
        disclaimer=AI_PORTFOLIO_CONVERSATION_DISCLAIMER,
    )
