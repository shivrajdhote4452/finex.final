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
from typing import Optional

from backend.app.core.envelope import create_response_envelope
from backend.app.database import get_db
from backend.app.domain.paper_trading_service import (
    OptionOrderSubmitRequest,
    OrderSubmitRequest,
    PaperTradingEngine,
)
from backend.app.routers.auth import get_current_user_id, is_owner
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/paper-trading", tags=["Paper Trading (Simulated)"])
engine = PaperTradingEngine()


class ResetAccountRequest(BaseModel):
    confirm_reset: bool = Field(..., description="Must be true to authorize account reset")


class DepositFundsRequest(BaseModel):
    amount: Decimal = Field(
        ...,
        gt=Decimal("0.00"),
        le=Decimal("10000000.00"),
        description="Deposit amount between 1 and 1 Crore virtual INR",
    )


@router.get("/account")
async def get_paper_account(
    request: Request,
    current_user: dict = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Fetch virtual account overview with equity, cash, and positions summary from PostgreSQL."""
    cid = getattr(request.state, "correlation_id", None)
    user_id = str(current_user.get("sub", current_user.get("user_id", "usr-shivraj-001")))

    summary = await engine.get_portfolio_summary_db(user_id, db=db)
    return create_response_envelope(data=summary, correlation_id=cid)


@router.post("/orders")
async def submit_paper_order(
    request: Request,
    payload: OrderSubmitRequest,
    x_idempotency_key: Optional[str] = Header(None, alias="X-Idempotency-Key"),
    current_user: dict = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Execute simulated market order atomically with idempotency protection in PostgreSQL."""
    cid = getattr(request.state, "correlation_id", None)
    user_id = str(current_user.get("sub", current_user.get("user_id", "usr-shivraj-001")))

    key = payload.idempotency_key or x_idempotency_key
    if not key:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Idempotency key required via body or X-Idempotency-Key header",
        )
    payload.idempotency_key = key

    result = await engine.execute_order_db(user_id, payload, db=db)
    return create_response_envelope(data=result.model_dump(mode="json"), correlation_id=cid)


@router.get("/orders")
async def list_paper_orders(
    request: Request,
    limit: int = Query(50, ge=1, le=100),
    current_user: dict = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Fetch order history for authenticated caller from PostgreSQL."""
    cid = getattr(request.state, "correlation_id", None)
    user_id = str(current_user.get("sub", current_user.get("user_id", "usr-shivraj-001")))

    orders = await engine.get_orders_db(user_id, limit=limit, db=db)
    return create_response_envelope(
        data={"orders": orders, "total": len(orders)},
        correlation_id=cid,
    )


@router.get("/positions")
async def list_paper_positions(
    request: Request,
    current_user: dict = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Fetch all open simulated positions for authenticated caller from PostgreSQL."""
    cid = getattr(request.state, "correlation_id", None)
    user_id = str(current_user.get("sub", current_user.get("user_id", "usr-shivraj-001")))

    positions = await engine.get_positions_db(user_id, db=db)
    return create_response_envelope(
        data={"positions": positions, "total": len(positions)},
        correlation_id=cid,
    )


@router.get("/ledger")
async def get_cash_ledger(
    request: Request,
    current_user: dict = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Fetch append-only cash ledger audit trail from PostgreSQL."""
    cid = getattr(request.state, "correlation_id", None)
    user_id = str(current_user.get("sub", current_user.get("user_id", "usr-shivraj-001")))

    ledger = await engine.get_ledger_db(user_id, db=db)
    return create_response_envelope(
        data={"ledger": ledger, "total": len(ledger)},
        correlation_id=cid,
    )


@router.post("/reset")
async def reset_paper_account(
    request: Request,
    payload: ResetAccountRequest,
    current_user: dict = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Reset virtual cash balance back to ₹1,00,000 and clear simulated positions in PostgreSQL."""
    if not is_owner(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Sandbox controls and accounts are restricted to the platform owner.",
        )

    cid = getattr(request.state, "correlation_id", None)
    user_id = str(current_user.get("sub", current_user.get("user_id", "usr-shivraj-001")))

    if not payload.confirm_reset:
        return create_response_envelope(
            data={"reset": False, "message": "Reset was not confirmed."},
            correlation_id=cid,
        )

    acct = await engine.reset_account_db(user_id, db=db)
    summary = await engine.get_portfolio_summary_db(user_id, db=db)

    return create_response_envelope(
        data={"reset": True, "reset_count": acct["reset_count"], "summary": summary},
        correlation_id=cid,
    )


@router.post("/deposit")
async def deposit_virtual_cash(
    request: Request,
    payload: DepositFundsRequest,
    current_user: dict = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Credit authorized virtual paper cash to account with immutable ledger audit record in PostgreSQL."""
    if not is_owner(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Sandbox controls and accounts are restricted to the platform owner.",
        )

    cid = getattr(request.state, "correlation_id", None)
    user_id = str(current_user.get("sub", current_user.get("user_id", "usr-shivraj-001")))

    result = await engine.deposit_funds_db(user_id, payload.amount, db=db)
    return create_response_envelope(data=result, correlation_id=cid)


# =============================================================================
# Options Paper Trading Endpoints (Phase 2 Long-Only)
# =============================================================================
@router.post("/options/orders")
async def submit_paper_option_order(
    request: Request,
    payload: OptionOrderSubmitRequest,
    x_idempotency_key: Optional[str] = Header(None, alias="X-Idempotency-Key"),
    current_user: dict = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Execute simulated long-only options buy order with deterministic cost & risk math."""
    cid = getattr(request.state, "correlation_id", None)
    user_id = str(current_user.get("sub", current_user.get("user_id", "usr-shivraj-001")))

    key = payload.idempotency_key or x_idempotency_key
    if not key:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Idempotency key required via body or X-Idempotency-Key header",
        )
    payload.idempotency_key = key

    result = await engine.execute_option_order_db(user_id, payload, db=db)
    return create_response_envelope(data=result.model_dump(mode="json"), correlation_id=cid)


@router.get("/options/positions")
async def list_paper_option_positions(
    request: Request,
    current_user: dict = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Fetch all open simulated options positions with mark-to-market valuation, P&L, and ITM/OTM status."""
    cid = getattr(request.state, "correlation_id", None)
    user_id = str(current_user.get("sub", current_user.get("user_id", "usr-shivraj-001")))

    positions = await engine.get_options_positions_db(user_id, db=db)
    return create_response_envelope(
        data={"positions": [p.model_dump(mode="json") for p in positions], "total": len(positions)},
        correlation_id=cid,
    )


class SettleOptionsRequest(BaseModel):
    spot_prices: Optional[dict] = Field(
        None, description="Optional map of underlying symbol to final expiry spot price"
    )


@router.post("/options/settle")
async def settle_expired_options_endpoint(
    request: Request,
    payload: Optional[SettleOptionsRequest] = None,
    current_user: dict = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Trigger deterministic settlement of expired option contracts.
    - ITM options settle at intrinsic value with virtual cash credit.
    - OTM options expire worthless with 100% loss of virtual premium paid.
    """
    cid = getattr(request.state, "correlation_id", None)
    user_id = str(current_user.get("sub", current_user.get("user_id", "usr-shivraj-001")))

    spot_prices = payload.spot_prices if payload else None
    settlement_results = await engine.settle_expired_options_db(user_id, spot_prices=spot_prices, db=db)
    return create_response_envelope(
        data={"settlements": settlement_results, "count": len(settlement_results)},
        correlation_id=cid,
    )
