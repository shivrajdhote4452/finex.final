"""Portfolio Intelligence API Router.

Task ID: S6-API-02
Author: Shivraj Dhote
Date: 16 October 2026

Exposes:
- GET /portfolio-intelligence: Return deterministic allocation, sector exposure, HHI, and 15% sector shock
- POST /portfolio-intelligence/scenario: Run customized hypothetical sector drawdown stress test
"""

from decimal import Decimal

from backend.app.adapters.market_data_provider import (
    INSTRUMENT_REGISTRY,
    VERIFIED_OBSERVATIONS,
    RealMarketDataProvider,
)
from backend.app.core.envelope import create_response_envelope
from backend.app.database import get_db
from backend.app.domain.paper_trading_service import PaperTradingEngine
from backend.app.domain.portfolio_intelligence_service import (
    PortfolioIntelligenceService,
)
from backend.app.routers.auth import get_current_user_id
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/portfolio-intelligence", tags=["Portfolio Intelligence & Scenarios"])
intelligence_service = PortfolioIntelligenceService()
market_provider = RealMarketDataProvider(force_cache=True, allow_fixture_fallback=True)
paper_engine = PaperTradingEngine()


class ScenarioRequest(BaseModel):
    target_sector: str = Field(
        ..., description="Target sector (e.g. 'Information Technology', 'Energy & Petrochemicals')"
    )
    shock_percentage: float = Field(-15.0, description="Hypothetical percentage shock (e.g. -15.0)")


@router.get("")
async def get_portfolio_intelligence(
    request: Request,
    current_user: dict = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve full deterministic intelligence report on current holdings."""
    cid = getattr(request.state, "correlation_id", None)
    user_id = str(current_user.get("sub", current_user.get("user_id", "usr-shivraj-001")))

    # Get active holdings from paper trading engine or default baseline
    summary = await paper_engine.get_portfolio_summary_db(user_id, db=db)
    holdings = summary.get("positions", [])
    cash = float(summary.get("cash_balance", 100000.00))

    # If no positions yet, provide standard benchmark holdings for preview
    if not holdings:
        holdings = [
            {"symbol": "RELIANCE", "quantity": 10.0, "avg_price": 2450.00},
            {"symbol": "TCS", "quantity": 5.0, "avg_price": 3400.00},
            {"symbol": "INFY", "quantity": 15.0, "avg_price": 1550.00},
            {"symbol": "HDFCBANK", "quantity": 20.0, "avg_price": 1420.00},
        ]
        cash = 45000.00

    # Fetch live quotes
    quotes = {}
    for item in INSTRUMENT_REGISTRY:
        sym = item["symbol"]
        q = await market_provider.get_latest_quote(sym)
        obs = VERIFIED_OBSERVATIONS.get(sym, {})
        if q:
            quotes[sym] = {
                "price": float(q.price),
                "change_percent": float(obs.get("change_pct", Decimal("0.0"))),
                "observation_date": q.observed_at.isoformat() if q.observed_at else "2026-10-16",
            }

    report = intelligence_service.compute_intelligence(
        holdings=holdings,
        cash_balance=cash,
        current_quotes=quotes,
        simulated_sector_shock="Information Technology",
    )

    return create_response_envelope(data=report.model_dump(mode="json"), correlation_id=cid)


@router.post("/scenario")
async def run_scenario_stress_test(
    request: Request,
    payload: ScenarioRequest,
    current_user: dict = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Run a custom hypothetical sector stress test."""
    cid = getattr(request.state, "correlation_id", None)
    user_id = str(current_user.get("sub", current_user.get("user_id", "usr-shivraj-001")))

    summary = await paper_engine.get_portfolio_summary_db(user_id, db=db)
    holdings = summary.get("positions", [])
    cash = float(summary.get("cash_balance", 100000.00))
    if not holdings:
        holdings = [
            {"symbol": "RELIANCE", "quantity": 10.0, "avg_price": 2450.00},
            {"symbol": "TCS", "quantity": 5.0, "avg_price": 3400.00},
            {"symbol": "INFY", "quantity": 15.0, "avg_price": 1550.00},
            {"symbol": "HDFCBANK", "quantity": 20.0, "avg_price": 1420.00},
        ]
        cash = 45000.00

    quotes = {}
    for item in INSTRUMENT_REGISTRY:
        sym = item["symbol"]
        q = await market_provider.get_latest_quote(sym)
        if q:
            quotes[sym] = {"price": float(q.price)}

    report = intelligence_service.compute_intelligence(
        holdings=holdings,
        cash_balance=cash,
        current_quotes=quotes,
        simulated_sector_shock=payload.target_sector,
    )

    return create_response_envelope(
        data={
            "scenario": report.scenario_shock_15pct_it.model_dump(mode="json")
            if report.scenario_shock_15pct_it
            else None,
            "baseline_portfolio_value": report.total_portfolio_value,
            "statutory_disclaimer": report.statutory_disclaimer,
        },
        correlation_id=cid,
    )
