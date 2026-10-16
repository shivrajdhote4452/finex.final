"""Deterministic Portfolio Valuation Engine.

Task ID: S3-API-02
Implements high-precision Decimal calculation for holdings valuation,
cost basis, unrealized P&L, percentage return, and asset allocation breakdown.
Never converts missing quotes to zero; reports partial valuation explicitly.
"""

from decimal import ROUND_HALF_UP, Decimal
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class HoldingValuation(BaseModel):
    symbol: str
    shares: Decimal
    cost_basis_per_share: Decimal
    total_cost: Decimal
    current_price: Optional[Decimal] = None
    market_value: Optional[Decimal] = None
    unrealized_pnl: Optional[Decimal] = None
    unrealized_pnl_pct: Optional[Decimal] = None
    allocation_pct: Optional[Decimal] = None
    is_quote_missing: bool = False


class PortfolioSummary(BaseModel):
    portfolio_id: str
    currency: str = "INR"
    total_cost_basis: Decimal
    total_market_value: Decimal
    total_unrealized_pnl: Decimal
    total_return_pct: Decimal
    is_fully_valued: bool
    missing_quote_symbols: List[str] = Field(default_factory=list)
    holdings: List[HoldingValuation]
    sector_allocation: Dict[str, Decimal] = Field(default_factory=dict)


def calculate_portfolio_valuation(
    portfolio_id: str,
    holdings: List[Dict],
    quotes: Dict[str, Decimal],
    sectors: Optional[Dict[str, str]] = None,
    currency: str = "INR",
) -> PortfolioSummary:
    """Calculate deterministic valuation across all positions.

    If any instrument quote is missing, it is reported under missing_quote_symbols
    and is_fully_valued is set to False.
    """
    sectors = sectors or {}
    total_cost = Decimal("0.00")
    total_market_val = Decimal("0.00")
    total_pnl = Decimal("0.00")
    is_full = True
    missing_symbols: List[str] = []
    holding_results: List[HoldingValuation] = []

    for h in holdings:
        sym = str(h["symbol"]).upper().strip()
        shares = Decimal(str(h["quantity"]))
        cost_per_share = Decimal(str(h["cost_basis_per_share"]))
        pos_cost = (shares * cost_per_share).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        total_cost += pos_cost

        cur_price = quotes.get(sym)
        if cur_price is not None:
            cur_price = Decimal(str(cur_price)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            pos_mkt_val = (shares * cur_price).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            pos_pnl = (pos_mkt_val - pos_cost).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            pos_pnl_pct = (
                (pos_pnl / pos_cost * Decimal("100.00")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                if pos_cost > Decimal("0")
                else Decimal("0.00")
            )
            total_market_val += pos_mkt_val
            total_pnl += pos_pnl

            holding_results.append(
                HoldingValuation(
                    symbol=sym,
                    shares=shares,
                    cost_basis_per_share=cost_per_share,
                    total_cost=pos_cost,
                    current_price=cur_price,
                    market_value=pos_mkt_val,
                    unrealized_pnl=pos_pnl,
                    unrealized_pnl_pct=pos_pnl_pct,
                    is_quote_missing=False,
                )
            )
        else:
            is_full = False
            missing_symbols.append(sym)
            holding_results.append(
                HoldingValuation(
                    symbol=sym,
                    shares=shares,
                    cost_basis_per_share=cost_per_share,
                    total_cost=pos_cost,
                    current_price=None,
                    market_value=None,
                    unrealized_pnl=None,
                    unrealized_pnl_pct=None,
                    is_quote_missing=True,
                )
            )

    # Compute asset & sector allocations
    sector_alloc: Dict[str, Decimal] = {}
    if total_market_val > Decimal("0"):
        for res in holding_results:
            if res.market_value is not None:
                alloc = (res.market_value / total_market_val * Decimal("100.00")).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
                res.allocation_pct = alloc
                sec = sectors.get(res.symbol, "General Equity")
                sector_alloc[sec] = (sector_alloc.get(sec, Decimal("0.00")) + alloc).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )

    total_return_pct = (
        (total_pnl / total_cost * Decimal("100.00")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if total_cost > Decimal("0")
        else Decimal("0.00")
    )

    return PortfolioSummary(
        portfolio_id=portfolio_id,
        currency=currency,
        total_cost_basis=total_cost,
        total_market_value=total_market_val,
        total_unrealized_pnl=total_pnl,
        total_return_pct=total_return_pct,
        is_fully_valued=is_full,
        missing_quote_symbols=missing_symbols,
        holdings=holding_results,
        sector_allocation=sector_alloc,
    )
