"""Portfolio Concentration and Diversification Explainer Engine.

Task ID: S3-AI-02
Author: Shivraj Dhote
Date: 16 October 2026

Deterministic portfolio explanation tool that:
1. Ingests frozen deterministic portfolio valuation metrics (PortfolioValuationSummary).
2. Performs all concentration calculations (HHI, top sector weight, position weight) in Python.
3. Produces educational, beginner-friendly diversification narratives with ZERO LLM arithmetic.
4. Binds narratives permanently to the snapshot version/timestamp so future price changes never distort meaning.
5. Issues explicit partial valuation disclosures when quotes are missing.
6. Strictly avoids personalized trade advice or price predictions.
"""

from decimal import Decimal
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from backend.app.domain.portfolio import PortfolioSummary


class ConcentrationMetrics(BaseModel):
    hhi_score: float = Field(..., description="Herfindahl-Hirschman Index for sector concentration (0 to 10000)")
    concentration_level: str = Field(..., description="'Well Diversified', 'Moderately Concentrated', or 'Highly Concentrated'")
    top_sector_name: str
    top_sector_pct: float
    total_sectors_count: int


class PortfolioExplanation(BaseModel):
    portfolio_id: str
    snapshot_version: str
    is_fully_valued: bool
    missing_quote_symbols: List[str]
    formatted_total_value: str
    formatted_cost_basis: str
    formatted_unrealized_pnl: str
    formatted_unrealized_pnl_pct: str
    concentration_metrics: ConcentrationMetrics
    sector_breakdown: List[Dict[str, Any]]
    educational_narrative: str
    key_observations: List[str]
    risk_education_notes: List[str]
    disclaimer: str


def compute_concentration_metrics(sector_alloc: Dict[str, Decimal]) -> ConcentrationMetrics:
    """Calculates deterministic Herfindahl-Hirschman Index (HHI) and sector exposure."""
    if not sector_alloc:
        return ConcentrationMetrics(
            hhi_score=0.0,
            concentration_level="Empty Portfolio",
            top_sector_name="None",
            top_sector_pct=0.0,
            total_sectors_count=0,
        )

    # Sort allocations descending by percentage value
    sorted_alloc = sorted(sector_alloc.items(), key=lambda x: x[1], reverse=True)
    top_sector, top_pct = sorted_alloc[0]

    # HHI calculation: sum of (percentage points)^2 (e.g. 50^2 + 50^2 = 5000)
    hhi = sum((float(pct)) ** 2 for _, pct in sorted_alloc)

    # Standard portfolio concentration thresholds:
    # 4 balanced sectors (~25% each) -> HHI ~ 2500 -> Well Diversified
    # Moderately concentrated (e.g. 50% top sector) -> HHI ~ 3750 -> Moderately Concentrated
    # Highly concentrated (> 70% in one sector or single/duo sector) -> HHI > 5000 -> Highly Concentrated
    if hhi <= 2550:
        level = "Well Diversified"
    elif hhi <= 5000:
        level = "Moderately Concentrated"
    else:
        level = "Highly Concentrated"

    return ConcentrationMetrics(
        hhi_score=round(hhi, 2),
        concentration_level=level,
        top_sector_name=top_sector,
        top_sector_pct=round(float(top_pct), 2),
        total_sectors_count=len(sorted_alloc),
    )


def generate_portfolio_explanation(
    summary: PortfolioSummary,
    snapshot_version: Optional[str] = None,
) -> PortfolioExplanation:
    """Generates an educational diversification narrative strictly from deterministic metrics.
    
    CRITICAL RULE: No arithmetic is delegated to an external model. All numbers, percentages,
    and thresholds are calculated deterministically by Python logic.
    """
    now_iso = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    version_tag = snapshot_version or f"snap-{summary.portfolio_id}-{now_iso}"
    conc = compute_concentration_metrics(summary.sector_allocation)

    # Format numbers
    sign = "+" if summary.total_unrealized_pnl > 0 else ""
    fmt_val = f"₹{summary.total_market_value:,.2f}"
    fmt_cost = f"₹{summary.total_cost_basis:,.2f}"
    fmt_pnl = f"{sign}₹{summary.total_unrealized_pnl:,.2f}"
    fmt_pnl_pct = f"{sign}{summary.total_return_pct:.2f}%"

    # Sector breakdown table
    breakdown = [
        {
            "sector": sec,
            "weight_pct": f"{pct:.2f}%",
        }
        for sec, pct in sorted(summary.sector_allocation.items(), key=lambda x: x[1], reverse=True)
    ]

    # Deterministic Narrative Construction
    narrative_paragraphs = []

    # 1. Valuation & Performance Summary
    if summary.is_fully_valued:
        narrative_paragraphs.append(
            f"As of snapshot {version_tag}, your portfolio holds a total market valuation of {fmt_val} against an aggregate acquisition cost basis of {fmt_cost}. "
            f"This represents an unrealized net gain/loss of {fmt_pnl} ({fmt_pnl_pct}). All {len(summary.sector_allocation)} sectors are valued using verified live exchange quotes."
        )
    else:
        missing_str = ", ".join(summary.missing_quote_symbols)
        narrative_paragraphs.append(
            f"PARTIAL VALUATION NOTICE: Live market quotes for {missing_str} are currently unavailable. "
            f"The current recorded valuation is {fmt_val} based strictly on verified active quotes, representing an unrealized P&L of {fmt_pnl}. "
            f"Missing instruments are not converted to zero price and are excluded from sector percentage weights to prevent misleading ratios."
        )

    # 2. Diversification & Concentration Analysis
    if conc.total_sectors_count > 0:
        narrative_paragraphs.append(
            f"Diversification Profile: Your holdings are distributed across {conc.total_sectors_count} sectors with an overall assessment of '{conc.concentration_level}' (HHI: {conc.hhi_score:.1f}). "
            f"Your single largest sector exposure is {conc.top_sector_name}, accounting for {conc.top_sector_pct:.2f}% of your valued portfolio."
        )

    educational_narrative = "\n\n".join(narrative_paragraphs)

    # Key Observations
    observations = [
        f"Top sector exposure: {conc.top_sector_name} at {conc.top_sector_pct:.2f}%.",
        f"Total distinct sectors represented: {conc.total_sectors_count}.",
        f"Overall concentration status: {conc.concentration_level}.",
    ]
    if not summary.is_fully_valued:
        observations.append(f"Incomplete pricing: {len(summary.missing_quote_symbols)} holding(s) awaiting verified quote.")

    # Educational notes on risk
    risk_notes = [
        "Sector Concentration Risk: When more than 30-40% of a portfolio is concentrated in a single industry, overall returns are heavily influenced by sector-specific regulatory or economic events.",
        "Cost Basis Importance: Knowing your acquisition cost basis helps you accurately gauge real purchasing power growth after inflation and taxes.",
        "Unrealized vs Realized: Gains and losses shown here are unrealized paper valuations and fluctuate continuously with official market trading sessions.",
    ]

    disclaimer = (
        "EDUCATIONAL DISCLAIMER: This portfolio explanation is generated deterministically for financial literacy "
        "and analytical review. It does not constitute investment advice, asset management, or a recommendation to buy, sell, or rebalance any holding. "
        "FinEx never provides guaranteed return projections."
    )

    return PortfolioExplanation(
        portfolio_id=summary.portfolio_id,
        snapshot_version=version_tag,
        is_fully_valued=summary.is_fully_valued,
        missing_quote_symbols=summary.missing_quote_symbols,
        formatted_total_value=fmt_val,
        formatted_cost_basis=fmt_cost,
        formatted_unrealized_pnl=fmt_pnl,
        formatted_unrealized_pnl_pct=fmt_pnl_pct,
        concentration_metrics=conc,
        sector_breakdown=breakdown,
        educational_narrative=educational_narrative,
        key_observations=observations,
        risk_education_notes=risk_notes,
        disclaimer=disclaimer,
    )
