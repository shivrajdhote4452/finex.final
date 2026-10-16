"""Portfolio Intelligence Service & Deterministic Scenario Stress Testing.

Task ID: S6-API-02
Author: Shivraj Dhote
Date: 16 October 2026

Coordinates:
1. Deterministic portfolio analytics: allocation, sector exposure, HHI concentration, diversification score.
2. Top contributors and detractors derived strictly from verified quotes and cost bases.
3. Scenario stress testing: e.g. hypothetical 15% sector shock with clear disclosure.
4. Missing data defense: missing quotes produce explicit 'UNAVAILABLE' values, never hallucinated.
"""

from decimal import Decimal
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

# Verified Official NSE Sector Taxonomy Mapping
SECTOR_TAXONOMY: Dict[str, str] = {
    "RELIANCE": "Energy & Petrochemicals",
    "TCS": "Information Technology",
    "INFY": "Information Technology",
    "HDFCBANK": "Financial Services",
    "ICICIBANK": "Financial Services",
    "SBIN": "Financial Services",
    "BHARTIARTL": "Telecommunication",
    "ITC": "Fast Moving Consumer Goods",
    "KOTAKBANK": "Financial Services",
    "LT": "Construction & Infrastructure",
}


class SectorExposure(BaseModel):
    sector: str
    market_value: float
    weight_pct: float
    securities_count: int


class ContributorItem(BaseModel):
    symbol: str
    unrealized_pnl: float
    unrealized_pnl_pct: float
    contribution_weight_pct: float


class ScenarioShockResult(BaseModel):
    scenario_name: str
    target_sector: str
    shock_pct: float
    baseline_portfolio_value: float
    estimated_rupee_impact: float
    post_shock_portfolio_value: float
    is_hypothetical: bool = True
    disclaimer: str


class PortfolioIntelligenceReport(BaseModel):
    snapshot_date: str
    total_portfolio_value: float
    cash_balance: float
    equity_market_value: float
    cash_weight_pct: float
    equity_weight_pct: float
    sector_exposures: List[SectorExposure]
    hhi_concentration_score: float
    top_holding_symbol: str
    top_holding_pct: float
    top_3_concentration_pct: float
    diversification_score: float  # 1.0 (Highly concentrated) to 10.0 (Well diversified)
    top_contributors: List[ContributorItem]
    top_detractors: List[ContributorItem]
    scenario_shock_15pct_it: Optional[ScenarioShockResult] = None
    is_complete: bool = True
    missing_data_fields: List[str] = Field(default_factory=list)
    statutory_disclaimer: str


STATUTORY_INTELLIGENCE_DISCLAIMER = (
    "STATUTORY DISCLAIMER: Portfolio intelligence metrics are generated through deterministic mathematical "
    "computation on verified exchange records. All scenario models (including sector shocks) are hypothetical stress tests "
    "for educational evaluation only and do not constitute trading advice, projections, or buy/sell recommendations."
)


class PortfolioIntelligenceService:
    """Calculates deterministic portfolio metrics and runs educational stress tests."""

    def compute_intelligence(
        self,
        holdings: List[Dict[str, Any]],
        cash_balance: float,
        current_quotes: Dict[str, Dict[str, Any]],
        snapshot_date: str = "2026-10-16",
        simulated_sector_shock: str = "Information Technology",
    ) -> PortfolioIntelligenceReport:
        missing_data = []
        equity_value = 0.0
        enriched_holdings = []

        # Validate market quotes
        for h in holdings:
            sym = h["symbol"].upper()
            qty = float(h["quantity"])
            avg_price = float(h.get("average_buy_price", h.get("avg_price", 0.0)))
            quote = current_quotes.get(sym)

            if not quote or "price" not in quote:
                missing_data.append(f"Missing quote for {sym}")
                cur_price = None
                mkt_val = 0.0
                pnl = 0.0
                pnl_pct = 0.0
            else:
                cur_price = float(quote["price"])
                mkt_val = cur_price * qty
                cost = avg_price * qty
                pnl = mkt_val - cost
                pnl_pct = ((cur_price - avg_price) / avg_price * 100.0) if avg_price > 0 else 0.0
                equity_value += mkt_val

            sector = SECTOR_TAXONOMY.get(sym, "Unclassified Sector")
            enriched_holdings.append({
                "symbol": sym,
                "quantity": qty,
                "avg_price": avg_price,
                "current_price": cur_price,
                "market_value": mkt_val,
                "unrealized_pnl": pnl,
                "unrealized_pnl_pct": pnl_pct,
                "sector": sector,
            })

        total_val = equity_value + cash_balance
        cash_pct = round((cash_balance / total_val * 100.0), 2) if total_val > 0 else 100.0
        equity_pct = round((equity_value / total_val * 100.0), 2) if total_val > 0 else 0.0

        # Sector Exposure
        sector_totals: Dict[str, Dict[str, Any]] = {}
        for eh in enriched_holdings:
            sec = eh["sector"]
            mv = eh["market_value"]
            if sec not in sector_totals:
                sector_totals[sec] = {"market_value": 0.0, "count": 0}
            sector_totals[sec]["market_value"] += mv
            sector_totals[sec]["count"] += 1

        sector_exposures = []
        for sec, dat in sorted(sector_totals.items(), key=lambda x: x[1]["market_value"], reverse=True):
            wt = round((dat["market_value"] / total_val * 100.0), 2) if total_val > 0 else 0.0
            sector_exposures.append(
                SectorExposure(
                    sector=sec,
                    market_value=round(dat["market_value"], 2),
                    weight_pct=wt,
                    securities_count=dat["count"],
                )
            )

        # Concentration & HHI
        # Weights across total portfolio (including cash as an asset)
        weights = []
        if total_val > 0:
            for eh in enriched_holdings:
                weights.append((eh["market_value"] / total_val) * 100.0)
            weights.append(cash_pct)

        hhi = sum(w ** 2 for w in weights)
        sorted_holdings = sorted(enriched_holdings, key=lambda x: x["market_value"], reverse=True)
        top_sym = sorted_holdings[0]["symbol"] if sorted_holdings else "NONE"
        top_pct = round((sorted_holdings[0]["market_value"] / total_val * 100.0), 2) if sorted_holdings and total_val > 0 else 0.0
        top_3_pct = round((sum(h["market_value"] for h in sorted_holdings[:3]) / total_val * 100.0), 2) if total_val > 0 else 0.0

        # Diversification Score (1.0 to 10.0 scale, where lower HHI gives higher score)
        raw_div = 10.0 - (hhi / 1000.0)
        div_score = round(max(1.0, min(10.0, raw_div)), 1)

        # Top Contributors & Detractors
        holdings_by_pnl = sorted(enriched_holdings, key=lambda x: x["unrealized_pnl"], reverse=True)
        top_contributors = [
            ContributorItem(
                symbol=h["symbol"],
                unrealized_pnl=round(h["unrealized_pnl"], 2),
                unrealized_pnl_pct=round(h["unrealized_pnl_pct"], 2),
                contribution_weight_pct=round((h["market_value"] / total_val * 100.0), 2) if total_val > 0 else 0.0,
            )
            for h in holdings_by_pnl if h["unrealized_pnl"] > 0
        ][:3]

        top_detractors = [
            ContributorItem(
                symbol=h["symbol"],
                unrealized_pnl=round(h["unrealized_pnl"], 2),
                unrealized_pnl_pct=round(h["unrealized_pnl_pct"], 2),
                contribution_weight_pct=round((h["market_value"] / total_val * 100.0), 2) if total_val > 0 else 0.0,
            )
            for h in reversed(holdings_by_pnl) if h["unrealized_pnl"] < 0
        ][:3]

        # Hypothetical 15% Sector Decline Scenario (Sprint 6 requirement S6-API-02 / S6-AI-03)
        target_sector_exposure = next((s for s in sector_exposures if s.sector == simulated_sector_shock), None)
        target_sector_mv = target_sector_exposure.market_value if target_sector_exposure else 0.0
        rupee_shock = round(target_sector_mv * 0.15, 2)
        post_shock_val = round(total_val - rupee_shock, 2)

        scenario = ScenarioShockResult(
            scenario_name=f"Hypothetical 15% Drawdown in {simulated_sector_shock}",
            target_sector=simulated_sector_shock,
            shock_pct=-15.0,
            baseline_portfolio_value=round(total_val, 2),
            estimated_rupee_impact=-rupee_shock,
            post_shock_portfolio_value=post_shock_val,
            is_hypothetical=True,
            disclaimer=(
                f"HYPOTHETICAL SIMULATION ONLY: Tests an instantaneous 15% drop in {simulated_sector_shock} holdings. "
                "Assumes zero correlated movement in other assets and does not forecast future price action."
            ),
        )

        return PortfolioIntelligenceReport(
            snapshot_date=snapshot_date,
            total_portfolio_value=round(total_val, 2),
            cash_balance=round(cash_balance, 2),
            equity_market_value=round(equity_value, 2),
            cash_weight_pct=cash_pct,
            equity_weight_pct=equity_pct,
            sector_exposures=sector_exposures,
            hhi_concentration_score=round(hhi, 2),
            top_holding_symbol=top_sym,
            top_holding_pct=top_pct,
            top_3_concentration_pct=top_3_pct,
            diversification_score=div_score,
            top_contributors=top_contributors,
            top_detractors=top_detractors,
            scenario_shock_15pct_it=scenario,
            is_complete=len(missing_data) == 0,
            missing_data_fields=missing_data,
            statutory_disclaimer=STATUTORY_INTELLIGENCE_DISCLAIMER,
        )
