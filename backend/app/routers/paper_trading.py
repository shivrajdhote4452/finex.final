"""Paper Trading API Router.

Task ID: S5-API-01, S5-API-02
Exposes:
- GET /paper-trading/account: Virtual balance, equity, positions
- POST /paper-trading/orders: Submit simulated buy/sell order with idempotency
- GET /paper-trading/orders: Historical orders
- GET /paper-trading/positions: Active holdings
- GET /paper-trading/ledger: Cash ledger audit records
- POST /paper-trading/reset: Reset virtual cash with audit entry
"""

from decimal import Decimal
from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field

from backend.app.core.envelope import create_response_envelope
from backend.app.domain.paper_trading_service import (
    OrderSubmitRequest,
    PaperTradingEngine,
    _LEDGER_STORE,
    _ORDERS_STORE,
    _POSITIONS_STORE,
)
from backend.app.routers.auth import get_current_user_id

router = APIRouter(prefix="/paper-trading", tags=["Paper Trading (Simulated)"])
engine = PaperTradingEngine()


class ResetAccountRequest(BaseModel):
    confirm_reset: bool = Field(..., description="Must be true to authorize account reset")


@router.get("/account")
async def get_paper_account(
    request: Request,
    current_user: dict = Depends(get_current_user_id),
):
    """Fetch virtual account overview with equity, cash, and positions summary."""
    cid = getattr(request.state, "correlation_id", None)
    user_id = str(current_user.get("sub", current_user.get("user_id", "usr-shivraj-001")))

    summary = engine.get_portfolio_summary(user_id)
    return create_response_envelope(data=summary, correlation_id=cid)


@router.post("/orders")
async def submit_paper_order(
    request: Request,
    payload: OrderSubmitRequest,
    current_user: dict = Depends(get_current_user_id),
):
    """Execute simulated market order atomically with idempotency protection."""
    cid = getattr(request.state, "correlation_id", None)
    user_id = str(current_user.get("sub", current_user.get("user_id", "usr-shivraj-001")))

    result = engine.execute_order(user_id, payload)
    return create_response_envelope(data=result.model_dump(mode="json"), correlation_id=cid)


@router.get("/orders")
async def list_paper_orders(
    request: Request,
    limit: int = Query(50, ge=1, le=100),
    current_user: dict = Depends(get_current_user_id),
):
    """Fetch order history for authenticated caller."""
    cid = getattr(request.state, "correlation_id", None)
    user_id = str(current_user.get("sub", current_user.get("user_id", "usr-shivraj-001")))

    acct = engine.get_or_create_account(user_id)
    acct_id = acct["id"]

    orders = [o for o in _ORDERS_STORE.values() if o["account_id"] == acct_id]
    orders.sort(key=lambda x: x["created_at"], reverse=True)

    # Convert Decimals to float for clean JSON serialization
    serialized = []
    for o in orders[:limit]:
        item = dict(o)
        for k in ["quantity", "fill_price", "gross_value", "fee", "net_value", "realized_pnl"]:
            if item.get(k) is not None:
                item[k] = float(item[k])
        serialized.append(item)

    return create_response_envelope(
        data={"orders": serialized, "total": len(orders)},
        correlation_id=cid,
    )


@router.get("/positions")
async def list_paper_positions(
    request: Request,
    current_user: dict = Depends(get_current_user_id),
):
    """Fetch all open simulated positions for authenticated caller."""
    cid = getattr(request.state, "correlation_id", None)
    user_id = str(current_user.get("sub", current_user.get("user_id", "usr-shivraj-001")))

    summary = engine.get_portfolio_summary(user_id)
    return create_response_envelope(
        data={"positions": summary["positions"], "total": len(summary["positions"])},
        correlation_id=cid,
    )


@router.get("/ledger")
async def get_cash_ledger(
    request: Request,
    current_user: dict = Depends(get_current_user_id),
):
    """Fetch append-only cash ledger audit trail."""
    cid = getattr(request.state, "correlation_id", None)
    user_id = str(current_user.get("sub", current_user.get("user_id", "usr-shivraj-001")))

    acct = engine.get_or_create_account(user_id)
    acct_id = acct["id"]

    ledger = _LEDGER_STORE.get(acct_id, [])

    # Format numbers
    serialized = []
    for entry in ledger:
        item = dict(entry)
        item["amount"] = float(item["amount"])
        item["balance_after"] = float(item["balance_after"])
        serialized.append(item)

    return create_response_envelope(
        data={"ledger": serialized, "total": len(serialized)},
        correlation_id=cid,
    )


@router.post("/reset")
async def reset_paper_account(
    request: Request,
    payload: ResetAccountRequest,
    current_user: dict = Depends(get_current_user_id),
):
    """Reset virtual cash balance back to ₹1,00,000 and clear simulated positions."""
    cid = getattr(request.state, "correlation_id", None)
    user_id = str(current_user.get("sub", current_user.get("user_id", "usr-shivraj-001")))

    if not payload.confirm_reset:
        return create_response_envelope(
            data={"reset": False, "message": "Reset was not confirmed."},
            correlation_id=cid,
        )

    acct = engine.reset_account(user_id)
    summary = engine.get_portfolio_summary(user_id)

    return create_response_envelope(
        data={"reset": True, "reset_count": acct["reset_count"], "summary": summary},
        correlation_id=cid,
    )
