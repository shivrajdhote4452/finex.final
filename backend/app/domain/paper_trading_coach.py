"""Paper Trading Coach and Performance Narrative Domain Module.

Task ID: S5-AI-01, S5-AI-02
Author: Shivraj Dhote
Date: 16 October 2026

Coordinates:
1. Trade execution coaching: Explains simulated order outcome, portfolio impact, and risk lessons.
2. Performance narrative pipeline: Summarizes contributors, concentration, and trading discipline.
3. Zero-hallucination arithmetic: All values map strictly from input metrics.
4. Mandatory educational simulation disclaimers: Strictly avoids encouraging real-money trading.
"""

from decimal import Decimal
from typing import Any, Dict, List

from backend.app.domain.paper_trading_service import ExecutionResult
from pydantic import BaseModel


class TradeCoachingInsight(BaseModel):
    order_id: str
    symbol: str
    side: str
    quantity: float
    fill_price: float
    order_status: str
    headline: str
    explanation: str
    portfolio_impact: str
    learning_points: List[str]
    disclaimer: str


class PaperPerformanceNarrative(BaseModel):
    account_id: str
    total_equity: float
    cash_balance: float
    positions_market_value: float
    unrealized_pnl: float
    cash_ratio_pct: float
    summary_narrative: str
    top_contributors: List[str]
    coaching_recommendations: List[str]
    disclaimer: str


SIMULATION_NOTICE = (
    "SIMULATION NOTICE: This coaching commentary evaluates a simulated paper trade within FinEx. "
    "Simulated execution does not account for real liquidity slippage, exchange fees, or execution queues. "
    "Past paper trading success does not guarantee real-market profitability. Never trade real capital without licensed advice."
)


def generate_trade_coaching(execution: ExecutionResult) -> TradeCoachingInsight:
    """Generates an educational breakdown of a confirmed paper trading execution."""
    sym = execution.symbol
    side = execution.side
    qty = float(execution.quantity)
    fill = float(execution.fill_price)
    gross = float(execution.gross_value)

    if execution.status == "REJECTED":
        headline = f"Order Rejected: {side} {qty} {sym}"
        explanation = f"Your order was not filled because: {execution.rejection_reason}"
        impact = "No virtual cash was deducted and no positions were opened."
        learnings = [
            "Capital Discipline: Always verify cash balance and available margin before submitting buy orders.",
            "Position Limits: Short selling is restricted in spot equity trading; you can only sell shares you currently hold.",
        ]
    elif side == "BUY":
        headline = f"Buy Order Filled: {qty} shares of {sym} @ ₹{fill:,.2f}"
        explanation = (
            f"You deployed ₹{gross:,.2f} of virtual cash to acquire {qty} shares of {sym}. "
            f"Your remaining available virtual cash is ₹{float(execution.cash_balance_after):,.2f}."
        )
        impact = f"Your portfolio equity is now backed by a new or enlarged equity position in {sym}."
        learnings = [
            "Opportunity Cost: Deploying cash into equity trades liquidity for expected capital growth.",
            "Volatility Management: Market orders execute at the prevailing market price; limit orders can be used to control acquisition cost.",
        ]
    else:  # SELL
        realized = float(execution.realized_pnl or Decimal("0.00"))
        sign = "+" if realized >= 0 else ""
        headline = f"Sell Order Filled: {qty} shares of {sym} @ ₹{fill:,.2f}"
        explanation = (
            f"You liquidated {qty} shares of {sym}, receiving net proceeds of ₹{gross:,.2f}. "
            f"The trade resulted in a realized profit/loss of {sign}₹{realized:,.2f}."
        )
        impact = f"Your virtual cash balance increased to ₹{float(execution.cash_balance_after):,.2f}."
        learnings = [
            "Realizing Gains/Losses: Selling converts unrealized paper fluctuations into permanent cash outcomes.",
            "Tax Awareness: In live trading, realized capital gains trigger taxation under Section 111A / 112A of the Income Tax Act.",
        ]

    return TradeCoachingInsight(
        order_id=execution.order_id,
        symbol=sym,
        side=side,
        quantity=qty,
        fill_price=fill,
        order_status=execution.status,
        headline=headline,
        explanation=explanation,
        portfolio_impact=impact,
        learning_points=learnings,
        disclaimer=SIMULATION_NOTICE,
    )


def generate_performance_narrative(summary: Dict[str, Any]) -> PaperPerformanceNarrative:
    """Generates educational portfolio review strictly from deterministic summary metrics."""
    acct_id = summary["account_id"]
    equity = summary["total_equity"]
    cash = summary["cash_balance"]
    market_val = summary["positions_market_value"]
    unrealized = summary["unrealized_pnl"]
    positions = summary.get("positions", [])

    cash_ratio = round((cash / equity * 100.0), 2) if equity > 0 else 100.0

    sign = "+" if unrealized >= 0 else ""
    narrative = (
        f"Your paper trading portfolio holds a total simulated equity of ₹{equity:,.2f}. "
        f"You have ₹{cash:,.2f} ({cash_ratio}%) in available virtual cash and ₹{market_val:,.2f} allocated across {len(positions)} equity positions. "
        f"Overall unrealized position return stands at {sign}₹{unrealized:,.2f} based on verified market observations."
    )

    contributors = []
    for p in positions:
        sym = p["symbol"]
        pnl = p["unrealized_pnl"]
        pnl_pct = p["unrealized_pnl_pct"]
        s = "+" if pnl >= 0 else ""
        contributors.append(f"{sym}: {s}₹{pnl:,.2f} ({s}{pnl_pct:.2f}%) on {p['quantity']} shares")

    if not contributors:
        contributors = ["No open positions; 100% virtual cash reserve."]

    coaching = [
        f"Cash Buffer: Maintaining {cash_ratio}% in virtual cash provides ample dry powder to practice dollar-cost averaging during market dips.",
        "Position Sizing: Avoid putting more than 20% of your virtual account into any single company to prevent outsized losses.",
    ]

    return PaperPerformanceNarrative(
        account_id=acct_id,
        total_equity=equity,
        cash_balance=cash,
        positions_market_value=market_val,
        unrealized_pnl=unrealized,
        cash_ratio_pct=cash_ratio,
        summary_narrative=narrative,
        top_contributors=contributors,
        coaching_recommendations=coaching,
        disclaimer=SIMULATION_NOTICE,
    )
