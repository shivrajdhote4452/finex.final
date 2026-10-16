"""Portfolio Management Router.

Task ID: S3-API-02
Exposes portfolio CRUD, positions management, and deterministic summary calculations.
Enforces caller ownership and prevents unauthorized access across users.
"""

import uuid
from decimal import Decimal
from typing import Dict

from backend.app.adapters.market_data_provider import VERIFIED_OBSERVATIONS
from backend.app.core.envelope import create_response_envelope
from backend.app.core.errors import ForbiddenException, NotFoundException
from backend.app.domain.portfolio import calculate_portfolio_valuation
from backend.app.routers.auth import get_current_user_id
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix="/portfolios", tags=["Portfolio"])

# In-memory store for isolated demonstration and test runs
_PORTFOLIO_STORE: Dict[str, Dict] = {}


class AddHoldingRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=20)
    quantity: Decimal = Field(..., gt=0, description="Positive quantity of shares")
    cost_basis_per_share: Decimal = Field(..., ge=0, description="Acquisition cost per share")
    asset_class: str = Field("EQUITY", description="Asset class")


@router.get("/me")
async def get_my_portfolio(request: Request, current_user: dict = Depends(get_current_user_id)):
    """Fetch or bootstrap the default portfolio for the authenticated caller."""
    cid = getattr(request.state, "correlation_id", None)
    user_id = str(current_user.get("sub", current_user.get("user_id", "usr-shivraj-001")))

    # Find or bootstrap portfolio
    p = next((x for x in _PORTFOLIO_STORE.values() if x["user_id"] == user_id), None)
    if not p:
        p_id = str(uuid.uuid4())
        p = {
            "id": p_id,
            "user_id": user_id,
            "name": "My Primary Portfolio",
            "currency": "INR",
            "holdings": [
                {
                    "id": str(uuid.uuid4()),
                    "symbol": "RELIANCE",
                    "quantity": Decimal("10.0"),
                    "cost_basis_per_share": Decimal("2300.00"),
                    "asset_class": "EQUITY",
                },
                {
                    "id": str(uuid.uuid4()),
                    "symbol": "TCS",
                    "quantity": Decimal("10.0"),
                    "cost_basis_per_share": Decimal("3450.00"),
                    "asset_class": "EQUITY",
                },
                {
                    "id": str(uuid.uuid4()),
                    "symbol": "INFY",
                    "quantity": Decimal("10.0"),
                    "cost_basis_per_share": Decimal("1350.00"),
                    "asset_class": "EQUITY",
                },
                {
                    "id": str(uuid.uuid4()),
                    "symbol": "HDFCBANK",
                    "quantity": Decimal("15.0"),
                    "cost_basis_per_share": Decimal("1533.00"),
                    "asset_class": "EQUITY",
                },
            ],
        }
        _PORTFOLIO_STORE[p_id] = p

    return create_response_envelope(data=p, correlation_id=cid)


@router.get("/{portfolio_id}/summary")
async def get_portfolio_summary(
    request: Request,
    portfolio_id: str,
    current_user: dict = Depends(get_current_user_id),
):
    """Calculate deterministic portfolio valuation, P&L and asset allocation."""
    cid = getattr(request.state, "correlation_id", None)
    user_id = str(current_user.get("sub", current_user.get("user_id", "usr-shivraj-001")))

    p = _PORTFOLIO_STORE.get(portfolio_id)
    if not p:
        raise NotFoundException(message="Portfolio not found.")
    if p["user_id"] != user_id:
        raise ForbiddenException(message="Forbidden: You do not own this portfolio.")

    # Gather prices from verified observations
    quotes = {sym: obs["price"] for sym, obs in VERIFIED_OBSERVATIONS.items()}
    sectors = {
        "RELIANCE": "Energy & Retail",
        "TCS": "Technology",
        "INFY": "Technology",
        "HDFCBANK": "Banking & Financial Services",
        "ICICIBANK": "Banking & Financial Services",
        "TATAMOTORS": "Automobile",
        "SBIN": "Banking & Financial Services",
        "ITC": "Consumer Goods & FMCG",
    }

    summary = calculate_portfolio_valuation(
        portfolio_id=portfolio_id,
        holdings=p["holdings"],
        quotes=quotes,
        sectors=sectors,
        currency=p.get("currency", "INR"),
    )

    return create_response_envelope(data=summary.model_dump(mode="json"), correlation_id=cid)


@router.post("/{portfolio_id}/holdings")
async def add_portfolio_holding(
    request: Request,
    portfolio_id: str,
    payload: AddHoldingRequest,
    current_user: dict = Depends(get_current_user_id),
):
    """Add or increase a holding position in caller's portfolio."""
    cid = getattr(request.state, "correlation_id", None)
    user_id = str(current_user.get("sub", current_user.get("user_id", "usr-shivraj-001")))

    p = _PORTFOLIO_STORE.get(portfolio_id)
    if not p:
        raise NotFoundException(message="Portfolio not found.")
    if p["user_id"] != user_id:
        raise ForbiddenException(message="Forbidden: You do not own this portfolio.")

    sym = payload.symbol.upper().strip()
    existing = next((h for h in p["holdings"] if h["symbol"] == sym), None)

    if existing:
        # Weighted average cost basis calculation
        current_qty = existing["quantity"]
        current_cost = existing["cost_basis_per_share"]
        added_qty = payload.quantity
        added_cost = payload.cost_basis_per_share

        total_qty = current_qty + added_qty
        new_avg_cost = ((current_qty * current_cost) + (added_qty * added_cost)) / total_qty

        existing["quantity"] = total_qty
        existing["cost_basis_per_share"] = new_avg_cost.quantize(Decimal("0.01"))
        holding_record = existing
    else:
        holding_record = {
            "id": str(uuid.uuid4()),
            "symbol": sym,
            "quantity": payload.quantity,
            "cost_basis_per_share": payload.cost_basis_per_share,
            "asset_class": payload.asset_class,
        }
        p["holdings"].append(holding_record)

    return create_response_envelope(
        data={"portfolio_id": portfolio_id, "holding": holding_record},
        correlation_id=cid,
    )


@router.delete("/{portfolio_id}/holdings/{holding_id}")
async def remove_portfolio_holding(
    request: Request,
    portfolio_id: str,
    holding_id: str,
    current_user: dict = Depends(get_current_user_id),
):
    """Remove a holding from caller's portfolio."""
    cid = getattr(request.state, "correlation_id", None)
    user_id = str(current_user.get("sub", current_user.get("user_id", "usr-shivraj-001")))

    p = _PORTFOLIO_STORE.get(portfolio_id)
    if not p:
        raise NotFoundException(message="Portfolio not found.")
    if p["user_id"] != user_id:
        raise ForbiddenException(message="Forbidden: You do not own this portfolio.")

    initial_len = len(p["holdings"])
    p["holdings"] = [h for h in p["holdings"] if str(h["id"]) != str(holding_id)]

    if len(p["holdings"]) == initial_len:
        raise NotFoundException(message="Holding not found in this portfolio.")

    return create_response_envelope(
        data={"portfolio_id": portfolio_id, "deleted_holding_id": holding_id},
        correlation_id=cid,
    )
