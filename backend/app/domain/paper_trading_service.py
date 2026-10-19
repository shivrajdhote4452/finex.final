"""Deterministic Execution and Ledger Service for Paper Trading.

Task ID: S5-API-01, S5-API-02
Author: Shivraj Dhote
Date: 16 October 2026

Implements:
1. Atomic Buy/Sell execution with exact Decimal arithmetic.
2. Idempotency protection with payload deduplication.
3. Pre-trade cash verification (insufficient cash rejection).
4. Pre-trade quantity verification (short selling prevention).
5. Append-only cash ledger accounting.
6. Controlled virtual account reset with audit trail.
7. Separation from real-money brokerages.
"""

import hashlib
import uuid
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import Dict, List, Optional

from backend.app.adapters.market_data_provider import VERIFIED_OBSERVATIONS, RealMarketDataProvider
from backend.app.database import AsyncSessionLocal
from backend.app.models.core import User
from backend.app.models.paper_trading import (
    PaperAccount,
    PaperCashLedger,
    PaperOrder,
    PaperPosition,
    PaperTrade,
)
from backend.app.ports.market_data import Quote
from fastapi import HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession


class OrderSubmitRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=20)
    side: str = Field(..., description="'BUY' or 'SELL'")
    quantity: Decimal = Field(..., gt=0, description="Positive quantity of shares to trade")
    order_type: str = Field("MARKET", description="'MARKET' or 'LIMIT'")
    limit_price: Optional[Decimal] = None
    max_total_cost: Optional[Decimal] = Field(None, description="Maximum authorized total cost including fees")
    idempotency_key: Optional[str] = Field(None, min_length=8, max_length=128)


class ExecutionResult(BaseModel):
    order_id: str
    account_id: str
    symbol: str
    side: str
    quantity: Decimal
    fill_price: Decimal
    gross_value: Decimal
    fee: Decimal
    net_value: Decimal
    status: str  # 'FILLED' or 'REJECTED'
    rejection_reason: Optional[str] = None
    cash_balance_after: Decimal
    realized_pnl: Optional[Decimal] = None
    executed_at: str
    disclaimer: str
    replayed: bool = False


class PaperPositionSummaryResponse(BaseModel):
    symbol: str
    quantity: float
    average_buy_price: float
    avg_cost: float
    current_price: float
    market_value: float
    cost_basis: float
    unrealized_pnl: float
    unrealized_pnl_pct: float


class PaperAccountSummaryResponse(BaseModel):
    account_id: str
    currency: str
    cash_balance: float
    current_cash: float
    positions_market_value: float
    total_cost_basis: float
    total_equity: float
    total_portfolio_value: float
    unrealized_pnl: float
    positions: List[PaperPositionSummaryResponse]
    reset_count: int
    disclaimer: str


# In-memory storage for isolated operational baseline
_ACCOUNTS_STORE: Dict[str, Dict] = {}
_ORDERS_STORE: Dict[str, Dict] = {}
_POSITIONS_STORE: Dict[str, Dict[str, Dict]] = {}  # account_id -> {symbol: position_dict}
_LEDGER_STORE: Dict[str, List[Dict]] = {}  # account_id -> list of ledger entries


class PaperTradingEngine:
    SIMULATION_DISCLAIMER = (
        "VIRTUAL TRADING DISCLAIMER: This execution is strictly a simulated paper trade within FinEx. "
        "No real currency, shares, or exchange orders were routed to any exchange or broker. "
        "Virtual profits or losses do not represent actual investment performance."
    )

    def __init__(self, market_provider: Optional[RealMarketDataProvider] = None) -> None:
        from backend.app.config import get_settings

        settings = get_settings()
        self.market_provider = market_provider or RealMarketDataProvider(
            force_cache=True, allow_fixture_fallback=getattr(settings, "MARKET_ALLOW_FIXTURES", False)
        )

    def get_or_create_account(self, user_id: str) -> Dict:
        """Fetch or bootstrap the default paper trading account (₹1,00,000 initial virtual cash)."""
        acct = next((a for a in _ACCOUNTS_STORE.values() if a["user_id"] == user_id), None)
        if not acct:
            acct_id = f"acct-{uuid.uuid4().hex[:12]}"
            now_str = datetime.now(timezone.utc).isoformat()
            acct = {
                "id": acct_id,
                "user_id": user_id,
                "initial_balance": Decimal("100000.00"),
                "current_cash": Decimal("100000.00"),
                "currency": "INR",
                "status": "ACTIVE",
                "reset_count": 0,
                "created_at": now_str,
                "updated_at": now_str,
            }
            _ACCOUNTS_STORE[acct_id] = acct
            _POSITIONS_STORE[acct_id] = {}
            _LEDGER_STORE[acct_id] = [
                {
                    "id": f"led-{uuid.uuid4().hex[:12]}",
                    "account_id": acct_id,
                    "entry_type": "INITIAL_CREDIT",
                    "amount": Decimal("100000.00"),
                    "balance_after": Decimal("100000.00"),
                    "reference_id": "INIT",
                    "description": "Initial virtual paper cash deposit",
                    "created_at": now_str,
                }
            ]
        return acct

    def get_market_quote_sync(self, symbol: str) -> Optional[Quote]:
        """Fetch quote synchronously checking cache or verified observation fixtures ONLY when explicitly permitted."""
        norm = self.market_provider._normalize_symbol(symbol)
        if norm in self.market_provider._cache:
            cached = self.market_provider._cache[norm]
            is_delayed, is_stale, status = self.market_provider._evaluate_freshness(cached.observed_at)
            return cached.model_copy(
                update={
                    "served_from_cache": True,
                    "is_delayed": is_delayed,
                    "is_stale": is_stale,
                    "data_status": status,
                }
            )
        if getattr(self.market_provider, "allow_fixture_fallback", False):
            if norm in VERIFIED_OBSERVATIONS:
                obs = VERIFIED_OBSERVATIONS[norm]
                now = datetime.now(timezone.utc)
                obs_time = obs["observed_at"]
                is_delayed, is_stale, status = self.market_provider._evaluate_freshness(obs_time)
                evidence = hashlib.sha256(
                    f"{norm}:{obs_time.isoformat()}:{obs['price']}:INR".encode("utf-8")
                ).hexdigest()
                q = Quote(
                    canonical_id=f"NSE:{norm}",
                    symbol=f"{norm}.NS",
                    price=obs["price"],
                    currency="INR",
                    observed_at=obs_time,
                    ingested_at=now,
                    source="test_fixture_baseline_snapshot",
                    source_uri=f"urn:market-data:fixture:{norm}",
                    source_evidence=evidence,
                    served_from_cache=False,
                    is_delayed=is_delayed,
                    is_stale=is_stale,
                    data_status=status,
                )
                self.market_provider._cache[norm] = q
                return q
        return None

    def get_market_price(self, symbol: str) -> Optional[Decimal]:
        """Fetch verified observation price for symbol if fresh."""
        q = self.get_market_quote_sync(symbol)
        if q and not q.is_stale and q.data_status != "stale":
            return q.price
        return None

    def execute_order(self, user_id: str, payload: OrderSubmitRequest) -> ExecutionResult:
        """Atomic market order execution with idempotency, cash check, and ledger updates."""
        acct = self.get_or_create_account(user_id)
        acct_id = acct["id"]
        sym = payload.symbol.upper().strip()
        side = payload.side.upper().strip()
        qty = payload.quantity
        now_str = datetime.now(timezone.utc).isoformat()
        order_type = payload.order_type.upper().strip()

        # 0. Validate supported order types
        if order_type not in ["MARKET", "LIMIT"]:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unsupported order type '{payload.order_type}'. Supported types: 'MARKET', 'LIMIT'.",
            )

        if order_type == "LIMIT" and (payload.limit_price is None or payload.limit_price <= Decimal("0.00")):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="LIMIT orders require a strictly positive limit_price.",
            )

        # 1. Canonical Fingerprint & Idempotency Check
        idemp_key = payload.idempotency_key
        if not idemp_key:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Idempotency key required via body or X-Idempotency-Key header.",
            )
        limit_str = f"{Decimal(str(payload.limit_price)):.2f}" if payload.limit_price is not None else "NONE"
        canonical_str = f"{user_id}:{sym}:{side}:{Decimal(str(qty)):.4f}:{order_type}:{limit_str}"
        fingerprint = hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()

        existing_order = next(
            (o for o in _ORDERS_STORE.values() if o["account_id"] == acct_id and o["idempotency_key"] == idemp_key),
            None,
        )
        if existing_order:
            # Check for conflict: compare all execution fields exactly
            limit_price_mismatch = False
            if order_type == "LIMIT":
                if existing_order.get("limit_price") is None or payload.limit_price is None:
                    limit_price_mismatch = existing_order.get("limit_price") != payload.limit_price
                else:
                    limit_price_mismatch = Decimal(str(existing_order["limit_price"])) != Decimal(
                        str(payload.limit_price)
                    )
            elif existing_order.get("limit_price") is not None:
                limit_price_mismatch = True

            if (
                existing_order["symbol"] != sym
                or existing_order["side"] != side
                or Decimal(str(existing_order["quantity"])) != Decimal(str(qty))
                or existing_order["order_type"] != order_type
                or limit_price_mismatch
            ):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Idempotency conflict (payload collision): Key was previously submitted with a different order payload.",
                )

            # Replay identical prior result with exact saved execution receipt
            return ExecutionResult(
                order_id=existing_order["id"],
                account_id=acct_id,
                symbol=existing_order["symbol"],
                side=existing_order["side"],
                quantity=existing_order["quantity"],
                fill_price=existing_order["fill_price"] or Decimal("0.00"),
                gross_value=existing_order.get("gross_value", Decimal("0.00")),
                fee=existing_order.get("fee", Decimal("0.00")),
                net_value=existing_order.get("net_value", Decimal("0.00")),
                status=existing_order["status"],
                rejection_reason=existing_order.get("rejection_reason"),
                cash_balance_after=existing_order.get("cash_balance_after", acct["current_cash"]),
                realized_pnl=existing_order.get("realized_pnl"),
                executed_at=existing_order["created_at"],
                disclaimer=self.SIMULATION_DISCLAIMER,
                replayed=True,
            )

        # 2. Price verification & freshness checks
        quote = self.get_market_quote_sync(sym)
        order_id = f"ord-{uuid.uuid4().hex[:12]}"

        if not quote:
            order_record = {
                "id": order_id,
                "account_id": acct_id,
                "user_id": user_id,
                "symbol": sym,
                "side": side,
                "quantity": qty,
                "order_type": order_type,
                "limit_price": payload.limit_price,
                "fill_price": Decimal("0.00"),
                "gross_value": Decimal("0.00"),
                "fee": Decimal("0.00"),
                "net_value": Decimal("0.00"),
                "status": "REJECTED",
                "rejection_reason": f"No verified market quote available for symbol '{sym}'. Trade rejected.",
                "cash_balance_after": acct["current_cash"],
                "idempotency_key": idemp_key,
                "fingerprint": fingerprint,
                "created_at": now_str,
            }
            _ORDERS_STORE[order_id] = order_record
            return ExecutionResult(
                order_id=order_id,
                account_id=acct_id,
                symbol=sym,
                side=side,
                quantity=qty,
                fill_price=Decimal("0.00"),
                gross_value=Decimal("0.00"),
                fee=Decimal("0.00"),
                net_value=Decimal("0.00"),
                status="REJECTED",
                rejection_reason=order_record["rejection_reason"],
                cash_balance_after=acct["current_cash"],
                realized_pnl=None,
                executed_at=now_str,
                disclaimer=self.SIMULATION_DISCLAIMER,
            )

        if quote.is_stale or quote.data_status == "stale":
            order_record = {
                "id": order_id,
                "account_id": acct_id,
                "user_id": user_id,
                "symbol": sym,
                "side": side,
                "quantity": qty,
                "order_type": order_type,
                "limit_price": payload.limit_price,
                "fill_price": Decimal("0.00"),
                "gross_value": Decimal("0.00"),
                "fee": Decimal("0.00"),
                "net_value": Decimal("0.00"),
                "status": "REJECTED",
                "rejection_reason": f"Market quote for symbol '{sym}' is stale (observed at {quote.observed_at.isoformat()}). Trade rejected per freshness policy.",
                "cash_balance_after": acct["current_cash"],
                "idempotency_key": idemp_key,
                "fingerprint": fingerprint,
                "created_at": now_str,
            }
            _ORDERS_STORE[order_id] = order_record
            return ExecutionResult(
                order_id=order_id,
                account_id=acct_id,
                symbol=sym,
                side=side,
                quantity=qty,
                fill_price=Decimal("0.00"),
                gross_value=Decimal("0.00"),
                fee=Decimal("0.00"),
                net_value=Decimal("0.00"),
                status="REJECTED",
                rejection_reason=order_record["rejection_reason"],
                cash_balance_after=acct["current_cash"],
                realized_pnl=None,
                executed_at=now_str,
                disclaimer=self.SIMULATION_DISCLAIMER,
            )
        market_price = quote.price

        # Enforce non-marketable limit rules (never fill above limit buy or below limit sell)
        if order_type == "LIMIT":
            assert payload.limit_price is not None
            if side == "BUY" and market_price > payload.limit_price:
                order_record = {
                    "id": order_id,
                    "account_id": acct_id,
                    "user_id": user_id,
                    "symbol": sym,
                    "side": side,
                    "quantity": qty,
                    "order_type": order_type,
                    "limit_price": payload.limit_price,
                    "fill_price": Decimal("0.00"),
                    "gross_value": Decimal("0.00"),
                    "fee": Decimal("0.00"),
                    "net_value": Decimal("0.00"),
                    "status": "REJECTED",
                    "rejection_reason": f"Non-marketable LIMIT buy: Market price (₹{market_price:,.2f}) exceeds submitted limit price (₹{payload.limit_price:,.2f}).",
                    "cash_balance_after": acct["current_cash"],
                    "idempotency_key": idemp_key,
                    "fingerprint": fingerprint,
                    "created_at": now_str,
                }
                _ORDERS_STORE[order_id] = order_record
                return ExecutionResult(
                    order_id=order_id,
                    account_id=acct_id,
                    symbol=sym,
                    side=side,
                    quantity=qty,
                    fill_price=Decimal("0.00"),
                    gross_value=Decimal("0.00"),
                    fee=Decimal("0.00"),
                    net_value=Decimal("0.00"),
                    status="REJECTED",
                    rejection_reason=order_record["rejection_reason"],
                    cash_balance_after=acct["current_cash"],
                    realized_pnl=None,
                    executed_at=now_str,
                    disclaimer=self.SIMULATION_DISCLAIMER,
                )
            if side == "SELL" and market_price < payload.limit_price:
                order_record = {
                    "id": order_id,
                    "account_id": acct_id,
                    "user_id": user_id,
                    "symbol": sym,
                    "side": side,
                    "quantity": qty,
                    "order_type": order_type,
                    "limit_price": payload.limit_price,
                    "fill_price": Decimal("0.00"),
                    "gross_value": Decimal("0.00"),
                    "fee": Decimal("0.00"),
                    "net_value": Decimal("0.00"),
                    "status": "REJECTED",
                    "rejection_reason": f"Non-marketable LIMIT sell: Market price (₹{market_price:,.2f}) is below submitted limit price (₹{payload.limit_price:,.2f}).",
                    "cash_balance_after": acct["current_cash"],
                    "idempotency_key": idemp_key,
                    "fingerprint": fingerprint,
                    "created_at": now_str,
                }
                _ORDERS_STORE[order_id] = order_record
                return ExecutionResult(
                    order_id=order_id,
                    account_id=acct_id,
                    symbol=sym,
                    side=side,
                    quantity=qty,
                    fill_price=Decimal("0.00"),
                    gross_value=Decimal("0.00"),
                    fee=Decimal("0.00"),
                    net_value=Decimal("0.00"),
                    status="REJECTED",
                    rejection_reason=order_record["rejection_reason"],
                    cash_balance_after=acct["current_cash"],
                    realized_pnl=None,
                    executed_at=now_str,
                    disclaimer=self.SIMULATION_DISCLAIMER,
                )

        fill_price = market_price
        gross_val = (qty * fill_price).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        fee = Decimal("0.00")  # Zero brokerage for educational tier

        positions = _POSITIONS_STORE.setdefault(acct_id, {})
        current_pos = positions.get(sym)

        # 3. Validation by side
        if side == "BUY":
            required_cash = gross_val + fee
            if payload.max_total_cost is not None and required_cash > payload.max_total_cost:
                order_record = {
                    "id": order_id,
                    "account_id": acct_id,
                    "user_id": user_id,
                    "symbol": sym,
                    "side": side,
                    "quantity": qty,
                    "order_type": order_type,
                    "limit_price": payload.limit_price,
                    "fill_price": fill_price,
                    "gross_value": gross_val,
                    "fee": fee,
                    "net_value": required_cash,
                    "status": "REJECTED",
                    "rejection_reason": f"Execution cost of ₹{required_cash:,.2f} exceeds authorized budget limit of ₹{payload.max_total_cost:,.2f}. Trade rejected.",
                    "cash_balance_after": acct["current_cash"],
                    "idempotency_key": idemp_key,
                    "fingerprint": fingerprint,
                    "created_at": now_str,
                }
                _ORDERS_STORE[order_id] = order_record
                return ExecutionResult(
                    order_id=order_id,
                    account_id=acct_id,
                    symbol=sym,
                    side=side,
                    quantity=qty,
                    fill_price=fill_price,
                    gross_value=gross_val,
                    fee=fee,
                    net_value=required_cash,
                    status="REJECTED",
                    rejection_reason=order_record["rejection_reason"],
                    cash_balance_after=acct["current_cash"],
                    realized_pnl=None,
                    executed_at=now_str,
                    disclaimer=self.SIMULATION_DISCLAIMER,
                )

            if acct["current_cash"] < required_cash:
                order_record = {
                    "id": order_id,
                    "account_id": acct_id,
                    "user_id": user_id,
                    "symbol": sym,
                    "side": side,
                    "quantity": qty,
                    "order_type": order_type,
                    "limit_price": payload.limit_price,
                    "fill_price": fill_price,
                    "gross_value": gross_val,
                    "fee": fee,
                    "net_value": required_cash,
                    "status": "REJECTED",
                    "rejection_reason": f"Insufficient virtual cash. Required: ₹{required_cash:,.2f}, Available: ₹{acct['current_cash']:,.2f}.",
                    "cash_balance_after": acct["current_cash"],
                    "idempotency_key": idemp_key,
                    "fingerprint": fingerprint,
                    "created_at": now_str,
                }
                _ORDERS_STORE[order_id] = order_record
                return ExecutionResult(
                    order_id=order_id,
                    account_id=acct_id,
                    symbol=sym,
                    side=side,
                    quantity=qty,
                    fill_price=fill_price,
                    gross_value=gross_val,
                    fee=fee,
                    net_value=required_cash,
                    status="REJECTED",
                    rejection_reason=order_record["rejection_reason"],
                    cash_balance_after=acct["current_cash"],
                    realized_pnl=None,
                    executed_at=now_str,
                    disclaimer=self.SIMULATION_DISCLAIMER,
                )

            # Deduct cash
            acct["current_cash"] -= required_cash
            cash_after = acct["current_cash"]

            # Update position (weighted average cost basis)
            if current_pos:
                old_qty = current_pos["quantity"]
                old_cost = current_pos["total_cost_basis"]
                new_qty = old_qty + qty
                new_cost = old_cost + gross_val
                new_avg = (new_cost / new_qty).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                current_pos["quantity"] = new_qty
                current_pos["total_cost_basis"] = new_cost
                current_pos["average_buy_price"] = new_avg
                current_pos["updated_at"] = now_str
            else:
                positions[sym] = {
                    "account_id": acct_id,
                    "symbol": sym,
                    "quantity": qty,
                    "average_buy_price": fill_price,
                    "total_cost_basis": gross_val,
                    "updated_at": now_str,
                }

            # Append to cash ledger
            _LEDGER_STORE.setdefault(acct_id, []).append(
                {
                    "id": f"led-{uuid.uuid4().hex[:12]}",
                    "account_id": acct_id,
                    "entry_type": "BUY_DEBIT",
                    "amount": -required_cash,
                    "balance_after": cash_after,
                    "reference_id": order_id,
                    "description": f"Bought {qty} shares of {sym} @ ₹{fill_price:,.2f}",
                    "created_at": now_str,
                }
            )

            realized_pnl = None

        elif side == "SELL":
            current_holding_qty = current_pos["quantity"] if current_pos else Decimal("0.0")
            if current_holding_qty < qty:
                order_record = {
                    "id": order_id,
                    "account_id": acct_id,
                    "user_id": user_id,
                    "symbol": sym,
                    "side": side,
                    "quantity": qty,
                    "order_type": order_type,
                    "limit_price": payload.limit_price,
                    "fill_price": fill_price,
                    "gross_value": gross_val,
                    "fee": fee,
                    "net_value": gross_val - fee,
                    "status": "REJECTED",
                    "rejection_reason": f"Insufficient holding quantity. Attempted to sell {qty} shares, but you hold {current_holding_qty} shares of {sym}.",
                    "cash_balance_after": acct["current_cash"],
                    "idempotency_key": idemp_key,
                    "fingerprint": fingerprint,
                    "created_at": now_str,
                }
                _ORDERS_STORE[order_id] = order_record
                return ExecutionResult(
                    order_id=order_id,
                    account_id=acct_id,
                    symbol=sym,
                    side=side,
                    quantity=qty,
                    fill_price=fill_price,
                    gross_value=gross_val,
                    fee=fee,
                    net_value=gross_val - fee,
                    status="REJECTED",
                    rejection_reason=order_record["rejection_reason"],
                    cash_balance_after=acct["current_cash"],
                    realized_pnl=None,
                    executed_at=now_str,
                    disclaimer=self.SIMULATION_DISCLAIMER,
                )

            # Credit cash
            net_proceeds = gross_val - fee
            acct["current_cash"] += net_proceeds
            cash_after = acct["current_cash"]

            # Calculate realized P&L
            avg_cost = current_pos["average_buy_price"]
            realized_pnl = ((fill_price - avg_cost) * qty).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

            # Update position
            new_qty = current_pos["quantity"] - qty
            if new_qty == Decimal("0"):
                del positions[sym]
            else:
                current_pos["quantity"] = new_qty
                current_pos["total_cost_basis"] = (new_qty * avg_cost).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                current_pos["updated_at"] = now_str

            # Append to cash ledger
            _LEDGER_STORE.setdefault(acct_id, []).append(
                {
                    "id": f"led-{uuid.uuid4().hex[:12]}",
                    "account_id": acct_id,
                    "entry_type": "SELL_CREDIT",
                    "amount": net_proceeds,
                    "balance_after": cash_after,
                    "reference_id": order_id,
                    "description": f"Sold {qty} shares of {sym} @ ₹{fill_price:,.2f} (Realized P&L: ₹{realized_pnl:+,.2f})",
                    "created_at": now_str,
                }
            )
        else:
            raise ValueError(f"Unsupported order side: {side}")

        # Store successful filled order
        order_record = {
            "id": order_id,
            "account_id": acct_id,
            "user_id": user_id,
            "symbol": sym,
            "side": side,
            "quantity": qty,
            "order_type": order_type,
            "limit_price": payload.limit_price,
            "fill_price": fill_price,
            "gross_value": gross_val,
            "fee": fee,
            "net_value": gross_val,
            "status": "FILLED",
            "realized_pnl": realized_pnl,
            "cash_balance_after": cash_after,
            "idempotency_key": idemp_key,
            "fingerprint": fingerprint,
            "created_at": now_str,
        }
        _ORDERS_STORE[order_id] = order_record

        return ExecutionResult(
            order_id=order_id,
            account_id=acct_id,
            symbol=sym,
            side=side,
            quantity=qty,
            fill_price=fill_price,
            gross_value=gross_val,
            fee=fee,
            net_value=gross_val,
            status="FILLED",
            rejection_reason=None,
            cash_balance_after=cash_after,
            realized_pnl=realized_pnl,
            executed_at=now_str,
            disclaimer=self.SIMULATION_DISCLAIMER,
        )

    def reset_account(self, user_id: str) -> Dict:
        """Reset virtual paper account back to ₹1,00,000 with audit trail."""
        acct = self.get_or_create_account(user_id)
        acct_id = acct["id"]
        now_str = datetime.now(timezone.utc).isoformat()

        # Clear active positions
        _POSITIONS_STORE[acct_id] = {}

        # Reset cash
        acct["current_cash"] = Decimal("100000.00")
        acct["reset_count"] += 1
        acct["updated_at"] = now_str

        # Add audit ledger record
        _LEDGER_STORE.setdefault(acct_id, []).append(
            {
                "id": f"led-{uuid.uuid4().hex[:12]}",
                "account_id": acct_id,
                "entry_type": "RESET_ADJUST",
                "amount": Decimal("100000.00"),
                "balance_after": Decimal("100000.00"),
                "reference_id": f"RESET-{acct['reset_count']}",
                "description": f"Virtual account reset #{acct['reset_count']} by user. Restored ₹1,00,000 cash balance.",
                "created_at": now_str,
            }
        )

        return acct

    def deposit_funds(self, user_id: str, amount: Decimal) -> Dict:
        """Credit authorized virtual paper cash to account with immutable ledger audit record."""
        acct = self.get_or_create_account(user_id)
        acct_id = acct["id"]
        now_str = datetime.now(timezone.utc).isoformat()
        acct["current_cash"] += amount
        acct["updated_at"] = now_str
        cash_after = acct["current_cash"]
        entry = {
            "id": f"led-{uuid.uuid4().hex[:12]}",
            "account_id": acct_id,
            "entry_type": "DEPOSIT",
            "amount": amount,
            "balance_after": cash_after,
            "reference_id": f"DEP-{uuid.uuid4().hex[:6].upper()}",
            "description": f"Virtual sandbox funds deposit of ₹{amount:,.2f}",
            "created_at": now_str,
        }
        _LEDGER_STORE.setdefault(acct_id, []).append(entry)
        return {
            "account_id": acct_id,
            "deposited": float(amount),
            "cash_balance": float(cash_after),
            "current_cash": float(cash_after),
            "entry": {
                **entry,
                "amount": float(amount),
                "balance_after": float(cash_after),
            },
        }

    def get_portfolio_summary(self, user_id: str) -> Dict:
        """Calculate total equity, positions valuation, unrealized P&L deterministically."""
        acct = self.get_or_create_account(user_id)
        acct_id = acct["id"]
        positions = _POSITIONS_STORE.get(acct_id, {})

        pos_list = []
        total_market_val = Decimal("0.00")
        total_cost_basis = Decimal("0.00")

        for sym, pos in positions.items():
            qty = pos["quantity"]
            avg_cost = pos["average_buy_price"]
            cost_basis = pos["total_cost_basis"]
            current_price = self.get_market_price(sym) or avg_cost
            market_val = (qty * current_price).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            unrealized_pnl = (market_val - cost_basis).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            pnl_pct = (
                (unrealized_pnl / cost_basis * Decimal("100.00")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                if cost_basis > 0
                else Decimal("0.00")
            )

            total_market_val += market_val
            total_cost_basis += cost_basis

            pos_list.append(
                {
                    "symbol": sym,
                    "quantity": float(qty),
                    "average_buy_price": float(avg_cost),
                    "avg_cost": float(avg_cost),
                    "current_price": float(current_price),
                    "market_value": float(market_val),
                    "cost_basis": float(cost_basis),
                    "unrealized_pnl": float(unrealized_pnl),
                    "unrealized_pnl_pct": float(pnl_pct),
                }
            )

        cash = acct["current_cash"]
        total_equity = cash + total_market_val
        total_unrealized = total_market_val - total_cost_basis

        return {
            "account_id": acct_id,
            "currency": acct["currency"],
            "cash_balance": float(cash),
            "current_cash": float(cash),
            "positions_market_value": float(total_market_val),
            "total_cost_basis": float(total_cost_basis),
            "total_equity": float(total_equity),
            "total_portfolio_value": float(total_equity),
            "unrealized_pnl": float(total_unrealized),
            "positions": pos_list,
            "reset_count": acct["reset_count"],
            "disclaimer": self.SIMULATION_DISCLAIMER,
        }

    async def get_or_create_account_db(self, user_id: str, db: Optional[AsyncSession] = None) -> PaperAccount:
        """Fetch or bootstrap the default paper trading account in PostgreSQL."""
        owns_session = db is None
        session = db if db is not None else AsyncSessionLocal()
        try:
            # Ensure user exists in users table to satisfy foreign key
            u_stmt = select(User).where(User.id == user_id)
            u_res = await session.execute(u_stmt)
            if not u_res.scalar_one_or_none():
                u = User(
                    id=user_id,
                    email=f"{user_id}@finex.internal",
                    provider="local_dev",
                    provider_subject=f"sub-{user_id}",
                    is_active=True,
                    is_verified=True,
                )
                session.add(u)
                await session.flush()

            stmt = select(PaperAccount).where(PaperAccount.user_id == user_id)
            res = await session.execute(stmt)
            acct = res.scalar_one_or_none()
            if not acct:
                acct_id = f"acct-{uuid.uuid4().hex[:12]}"
                acct = PaperAccount(
                    id=acct_id,
                    user_id=user_id,
                    account_number=f"FINEX-{uuid.uuid4().hex[:8].upper()}",
                    initial_balance=Decimal("100000.00"),
                    current_cash=Decimal("100000.00"),
                    currency="INR",
                    status="ACTIVE",
                    reset_count=0,
                )
                session.add(acct)
                await session.flush()

                led = PaperCashLedger(
                    id=f"led-{uuid.uuid4().hex[:12]}",
                    account_id=acct.id,
                    entry_type="INITIAL_CREDIT",
                    amount=Decimal("100000.00"),
                    balance_after=Decimal("100000.00"),
                    reference_id="INIT",
                    description="Initial virtual paper cash deposit",
                )
                session.add(led)
                if owns_session:
                    await session.commit()
            return acct
        except Exception:
            if owns_session:
                await session.rollback()
            raise
        finally:
            if owns_session:
                await session.close()

    async def execute_order_db(
        self,
        user_id: str,
        payload: OrderSubmitRequest,
        db: Optional[AsyncSession] = None,
    ) -> ExecutionResult:
        """Atomic market order execution with idempotency, cash check, and ledger updates in PostgreSQL."""
        owns_session = db is None
        session = db if db is not None else AsyncSessionLocal()
        try:
            # 0. Acquire row lock on user account
            await self.get_or_create_account_db(user_id, db=session)
            stmt = select(PaperAccount).where(PaperAccount.user_id == user_id).with_for_update()
            res = await session.execute(stmt)
            acct = res.scalar_one()
            acct_id = acct.id

            sym = payload.symbol.upper().strip()
            side = payload.side.upper().strip()
            qty = payload.quantity
            now = datetime.now(timezone.utc)
            now_str = now.isoformat()
            order_type = payload.order_type.upper().strip()

            if order_type not in ["MARKET", "LIMIT"]:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Unsupported order type '{payload.order_type}'. Supported types: 'MARKET', 'LIMIT'.",
                )

            if order_type == "LIMIT" and (payload.limit_price is None or payload.limit_price <= Decimal("0.00")):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="LIMIT orders require a strictly positive limit_price.",
                )

            # 1. Canonical Fingerprint & Idempotency Check in DB
            idemp_key = payload.idempotency_key
            if not idemp_key:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Idempotency key required via body or X-Idempotency-Key header.",
                )

            # Check existing order in DB
            stmt_order = select(PaperOrder).where(
                PaperOrder.account_id == acct_id,
                PaperOrder.idempotency_key == idemp_key,
            )
            res_order = await session.execute(stmt_order)
            existing_order = res_order.scalar_one_or_none()
            if existing_order:
                # Compare all execution fields exactly
                limit_price_mismatch = False
                if order_type == "LIMIT":
                    if existing_order.limit_price is None or payload.limit_price is None:
                        limit_price_mismatch = existing_order.limit_price != payload.limit_price
                    else:
                        limit_price_mismatch = Decimal(str(existing_order.limit_price)) != Decimal(
                            str(payload.limit_price)
                        )
                elif existing_order.limit_price is not None:
                    limit_price_mismatch = True

                if (
                    existing_order.symbol != sym
                    or existing_order.side != side
                    or Decimal(str(existing_order.quantity)) != Decimal(str(qty))
                    or existing_order.order_type != order_type
                    or limit_price_mismatch
                ):
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Idempotency conflict (payload collision): Key was previously submitted with a different order payload.",
                    )

                # Return saved execution receipt
                receipt = existing_order.execution_receipt
                if receipt:
                    rec_dict = dict(receipt)
                    rec_dict["replayed"] = True
                    rec_dict["disclaimer"] = self.SIMULATION_DISCLAIMER
                    return ExecutionResult(**rec_dict)

            # 2. Price verification & Limit marketability rules
            quote = await self.market_provider.get_latest_quote(sym)
            if not quote and getattr(self.market_provider, "allow_fixture_fallback", False):
                quote = self.get_market_quote_sync(sym)
            order_id = f"ord-{uuid.uuid4().hex[:12]}"

            if not quote:
                reason = f"No verified market quote available for symbol '{sym}'. Trade rejected."
                exec_result = ExecutionResult(
                    order_id=order_id,
                    account_id=acct_id,
                    symbol=sym,
                    side=side,
                    quantity=qty,
                    fill_price=Decimal("0.00"),
                    gross_value=Decimal("0.00"),
                    fee=Decimal("0.00"),
                    net_value=Decimal("0.00"),
                    status="REJECTED",
                    rejection_reason=reason,
                    cash_balance_after=Decimal(str(acct.current_cash)),
                    realized_pnl=None,
                    executed_at=now_str,
                    disclaimer=self.SIMULATION_DISCLAIMER,
                )
                order_rec = PaperOrder(
                    id=order_id,
                    account_id=acct_id,
                    user_id=user_id,
                    symbol=sym,
                    side=side,
                    order_type=order_type,
                    quantity=qty,
                    limit_price=payload.limit_price,
                    fill_price=Decimal("0.00"),
                    fee=Decimal("0.00"),
                    status="REJECTED",
                    rejection_reason=reason,
                    idempotency_key=idemp_key,
                    execution_receipt=exec_result.model_dump(mode="json"),
                )
                session.add(order_rec)
                if owns_session:
                    await session.commit()
                return exec_result

            if quote.is_stale or quote.data_status == "stale":
                reason = f"Market quote for symbol '{sym}' is stale (observed at {quote.observed_at.isoformat()}). Trade rejected per freshness policy."
                exec_result = ExecutionResult(
                    order_id=order_id,
                    account_id=acct_id,
                    symbol=sym,
                    side=side,
                    quantity=qty,
                    fill_price=Decimal("0.00"),
                    gross_value=Decimal("0.00"),
                    fee=Decimal("0.00"),
                    net_value=Decimal("0.00"),
                    status="REJECTED",
                    rejection_reason=reason,
                    cash_balance_after=Decimal(str(acct.current_cash)),
                    realized_pnl=None,
                    executed_at=now_str,
                    disclaimer=self.SIMULATION_DISCLAIMER,
                )
                order_rec = PaperOrder(
                    id=order_id,
                    account_id=acct_id,
                    user_id=user_id,
                    symbol=sym,
                    side=side,
                    order_type=order_type,
                    quantity=qty,
                    limit_price=payload.limit_price,
                    fill_price=Decimal("0.00"),
                    fee=Decimal("0.00"),
                    status="REJECTED",
                    rejection_reason=reason,
                    idempotency_key=idemp_key,
                    execution_receipt=exec_result.model_dump(mode="json"),
                )
                session.add(order_rec)
                if owns_session:
                    await session.commit()
                return exec_result

            market_price = quote.price

            if order_type == "LIMIT":
                assert payload.limit_price is not None
                if side == "BUY" and market_price > payload.limit_price:
                    reason = f"Non-marketable LIMIT buy: Market price (₹{market_price:,.2f}) exceeds submitted limit price (₹{payload.limit_price:,.2f})."
                    exec_result = ExecutionResult(
                        order_id=order_id,
                        account_id=acct_id,
                        symbol=sym,
                        side=side,
                        quantity=qty,
                        fill_price=Decimal("0.00"),
                        gross_value=Decimal("0.00"),
                        fee=Decimal("0.00"),
                        net_value=Decimal("0.00"),
                        status="REJECTED",
                        rejection_reason=reason,
                        cash_balance_after=Decimal(str(acct.current_cash)),
                        realized_pnl=None,
                        executed_at=now_str,
                        disclaimer=self.SIMULATION_DISCLAIMER,
                    )
                    order_rec = PaperOrder(
                        id=order_id,
                        account_id=acct_id,
                        user_id=user_id,
                        symbol=sym,
                        side=side,
                        order_type=order_type,
                        quantity=qty,
                        limit_price=payload.limit_price,
                        fill_price=Decimal("0.00"),
                        fee=Decimal("0.00"),
                        status="REJECTED",
                        rejection_reason=reason,
                        idempotency_key=idemp_key,
                        execution_receipt=exec_result.model_dump(mode="json"),
                    )
                    session.add(order_rec)
                    if owns_session:
                        await session.commit()
                    return exec_result
                if side == "SELL" and market_price < payload.limit_price:
                    reason = f"Non-marketable LIMIT sell: Market price (₹{market_price:,.2f}) is below submitted limit price (₹{payload.limit_price:,.2f})."
                    exec_result = ExecutionResult(
                        order_id=order_id,
                        account_id=acct_id,
                        symbol=sym,
                        side=side,
                        quantity=qty,
                        fill_price=Decimal("0.00"),
                        gross_value=Decimal("0.00"),
                        fee=Decimal("0.00"),
                        net_value=Decimal("0.00"),
                        status="REJECTED",
                        rejection_reason=reason,
                        cash_balance_after=Decimal(str(acct.current_cash)),
                        realized_pnl=None,
                        executed_at=now_str,
                        disclaimer=self.SIMULATION_DISCLAIMER,
                    )
                    order_rec = PaperOrder(
                        id=order_id,
                        account_id=acct_id,
                        user_id=user_id,
                        symbol=sym,
                        side=side,
                        order_type=order_type,
                        quantity=qty,
                        limit_price=payload.limit_price,
                        fill_price=Decimal("0.00"),
                        fee=Decimal("0.00"),
                        status="REJECTED",
                        rejection_reason=reason,
                        idempotency_key=idemp_key,
                        execution_receipt=exec_result.model_dump(mode="json"),
                    )
                    session.add(order_rec)
                    if owns_session:
                        await session.commit()
                    return exec_result

            fill_price = market_price
            gross_val = (qty * fill_price).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            fee = Decimal("0.00")

            # Query existing position with lock
            pos_stmt = (
                select(PaperPosition)
                .where(
                    PaperPosition.account_id == acct_id,
                    PaperPosition.symbol == sym,
                )
                .with_for_update()
            )
            pos_res = await session.execute(pos_stmt)
            pos = pos_res.scalar_one_or_none()

            if side == "BUY":
                required_cash = gross_val + fee
                current_cash = Decimal(str(acct.current_cash))
                if payload.max_total_cost is not None and required_cash > payload.max_total_cost:
                    reason = f"Execution cost of ₹{required_cash:,.2f} exceeds authorized budget limit of ₹{payload.max_total_cost:,.2f}. Trade rejected."
                    exec_result = ExecutionResult(
                        order_id=order_id,
                        account_id=acct_id,
                        symbol=sym,
                        side=side,
                        quantity=qty,
                        fill_price=fill_price,
                        gross_value=gross_val,
                        fee=fee,
                        net_value=required_cash,
                        status="REJECTED",
                        rejection_reason=reason,
                        cash_balance_after=current_cash,
                        realized_pnl=None,
                        executed_at=now_str,
                        disclaimer=self.SIMULATION_DISCLAIMER,
                    )
                    order_rec = PaperOrder(
                        id=order_id,
                        account_id=acct_id,
                        user_id=user_id,
                        symbol=sym,
                        side=side,
                        order_type=order_type,
                        quantity=qty,
                        limit_price=payload.limit_price,
                        fill_price=fill_price,
                        fee=fee,
                        status="REJECTED",
                        rejection_reason=reason,
                        idempotency_key=idemp_key,
                        execution_receipt=exec_result.model_dump(mode="json"),
                    )
                    session.add(order_rec)
                    if owns_session:
                        await session.commit()
                    return exec_result

                if current_cash < required_cash:
                    reason = (
                        f"Insufficient virtual cash. Required: ₹{required_cash:,.2f}, Available: ₹{current_cash:,.2f}."
                    )
                    exec_result = ExecutionResult(
                        order_id=order_id,
                        account_id=acct_id,
                        symbol=sym,
                        side=side,
                        quantity=qty,
                        fill_price=fill_price,
                        gross_value=gross_val,
                        fee=fee,
                        net_value=required_cash,
                        status="REJECTED",
                        rejection_reason=reason,
                        cash_balance_after=current_cash,
                        realized_pnl=None,
                        executed_at=now_str,
                        disclaimer=self.SIMULATION_DISCLAIMER,
                    )
                    order_rec = PaperOrder(
                        id=order_id,
                        account_id=acct_id,
                        user_id=user_id,
                        symbol=sym,
                        side=side,
                        order_type=order_type,
                        quantity=qty,
                        limit_price=payload.limit_price,
                        fill_price=fill_price,
                        fee=fee,
                        status="REJECTED",
                        rejection_reason=reason,
                        idempotency_key=idemp_key,
                        execution_receipt=exec_result.model_dump(mode="json"),
                    )
                    session.add(order_rec)
                    if owns_session:
                        await session.commit()
                    return exec_result

                # Deduct cash
                new_cash = current_cash - required_cash
                acct.current_cash = new_cash
                acct.updated_at = now

                # Update position
                if pos:
                    old_qty = Decimal(str(pos.quantity))
                    old_cost = Decimal(str(pos.total_cost_basis))
                    new_qty = old_qty + qty
                    new_cost = old_cost + gross_val
                    new_avg = (new_cost / new_qty).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                    pos.quantity = new_qty
                    pos.total_cost_basis = new_cost
                    pos.average_buy_price = new_avg
                    pos.updated_at = now
                else:
                    pos = PaperPosition(
                        id=f"pos-{uuid.uuid4().hex[:12]}",
                        account_id=acct_id,
                        symbol=sym,
                        quantity=qty,
                        average_buy_price=fill_price,
                        total_cost_basis=gross_val,
                    )
                    session.add(pos)

                # Cash ledger
                led = PaperCashLedger(
                    id=f"led-{uuid.uuid4().hex[:12]}",
                    account_id=acct_id,
                    entry_type="BUY_DEBIT",
                    amount=-required_cash,
                    balance_after=new_cash,
                    reference_id=order_id,
                    description=f"Bought {qty} shares of {sym} @ ₹{fill_price:,.2f}",
                )
                session.add(led)
                realized_pnl = None

            elif side == "SELL":
                current_qty = Decimal(str(pos.quantity)) if pos else Decimal("0.0")
                if current_qty < qty:
                    reason = f"Insufficient holding quantity. Attempted to sell {qty} shares, but you hold {current_qty} shares of {sym}."
                    exec_result = ExecutionResult(
                        order_id=order_id,
                        account_id=acct_id,
                        symbol=sym,
                        side=side,
                        quantity=qty,
                        fill_price=fill_price,
                        gross_value=gross_val,
                        fee=fee,
                        net_value=gross_val - fee,
                        status="REJECTED",
                        rejection_reason=reason,
                        cash_balance_after=Decimal(str(acct.current_cash)),
                        realized_pnl=None,
                        executed_at=now_str,
                        disclaimer=self.SIMULATION_DISCLAIMER,
                    )
                    order_rec = PaperOrder(
                        id=order_id,
                        account_id=acct_id,
                        user_id=user_id,
                        symbol=sym,
                        side=side,
                        order_type=order_type,
                        quantity=qty,
                        limit_price=payload.limit_price,
                        fill_price=fill_price,
                        fee=fee,
                        status="REJECTED",
                        rejection_reason=reason,
                        idempotency_key=idemp_key,
                        execution_receipt=exec_result.model_dump(mode="json"),
                    )
                    session.add(order_rec)
                    if owns_session:
                        await session.commit()
                    return exec_result

                net_proceeds = gross_val - fee
                new_cash = Decimal(str(acct.current_cash)) + net_proceeds
                acct.current_cash = new_cash
                acct.updated_at = now

                avg_cost = Decimal(str(pos.average_buy_price))
                realized_pnl = ((fill_price - avg_cost) * qty).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

                new_qty = current_qty - qty
                if new_qty == Decimal("0"):
                    await session.delete(pos)
                else:
                    pos.quantity = new_qty
                    pos.total_cost_basis = (new_qty * avg_cost).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                    pos.updated_at = now

                # Cash ledger
                led = PaperCashLedger(
                    id=f"led-{uuid.uuid4().hex[:12]}",
                    account_id=acct_id,
                    entry_type="SELL_CREDIT",
                    amount=net_proceeds,
                    balance_after=new_cash,
                    reference_id=order_id,
                    description=f"Sold {qty} shares of {sym} @ ₹{fill_price:,.2f} (Realized P&L: ₹{realized_pnl:+,.2f})",
                )
                session.add(led)

            exec_result = ExecutionResult(
                order_id=order_id,
                account_id=acct_id,
                symbol=sym,
                side=side,
                quantity=qty,
                fill_price=fill_price,
                gross_value=gross_val,
                fee=fee,
                net_value=gross_val,
                status="FILLED",
                rejection_reason=None,
                cash_balance_after=new_cash,
                realized_pnl=realized_pnl,
                executed_at=now_str,
                disclaimer=self.SIMULATION_DISCLAIMER,
            )

            # Persist order and trade atomically
            order_rec = PaperOrder(
                id=order_id,
                account_id=acct_id,
                user_id=user_id,
                symbol=sym,
                side=side,
                order_type=order_type,
                quantity=qty,
                limit_price=payload.limit_price,
                fill_price=fill_price,
                fee=fee,
                status="FILLED",
                idempotency_key=idemp_key,
                execution_receipt=exec_result.model_dump(mode="json"),
            )
            session.add(order_rec)
            await session.flush()

            trade_rec = PaperTrade(
                id=f"trd-{uuid.uuid4().hex[:12]}",
                order_id=order_id,
                account_id=acct_id,
                symbol=sym,
                side=side,
                quantity=qty,
                price=fill_price,
                gross_value=gross_val,
                fee=fee,
                net_value=gross_val,
            )
            session.add(trade_rec)

            if owns_session:
                await session.commit()

            # Sync in-memory stores as well
            self._sync_to_memory(acct_id, user_id, order_rec, exec_result, new_cash, pos=pos, led=led)
            return exec_result

        except Exception:
            if owns_session:
                await session.rollback()
            raise
        finally:
            if owns_session:
                await session.close()

    async def get_portfolio_summary_db(self, user_id: str, db: Optional[AsyncSession] = None) -> Dict:
        """Fetch real account, positions, and live valuations from PostgreSQL."""
        owns_session = db is None
        session = db if db is not None else AsyncSessionLocal()
        try:
            acct = await self.get_or_create_account_db(user_id, db=session)
            acct_id = acct.id

            stmt_pos = select(PaperPosition).where(PaperPosition.account_id == acct_id)
            res_pos = await session.execute(stmt_pos)
            positions = res_pos.scalars().all()

            pos_list = []
            total_market_val = Decimal("0.00")
            total_cost_basis = Decimal("0.00")

            for pos in positions:
                sym = pos.symbol
                qty = Decimal(str(pos.quantity))
                avg_cost = Decimal(str(pos.average_buy_price))
                cost_basis = Decimal(str(pos.total_cost_basis))
                current_price = self.get_market_price(sym) or avg_cost
                market_val = (qty * current_price).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                unrealized_pnl = (market_val - cost_basis).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                pnl_pct = (
                    (unrealized_pnl / cost_basis * Decimal("100.00")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                    if cost_basis > 0
                    else Decimal("0.00")
                )

                total_market_val += market_val
                total_cost_basis += cost_basis

                pos_list.append(
                    {
                        "symbol": sym,
                        "quantity": float(qty),
                        "average_buy_price": float(avg_cost),
                        "avg_cost": float(avg_cost),
                        "current_price": float(current_price),
                        "market_value": float(market_val),
                        "cost_basis": float(cost_basis),
                        "unrealized_pnl": float(unrealized_pnl),
                        "unrealized_pnl_pct": float(pnl_pct),
                    }
                )

            cash = Decimal(str(acct.current_cash))
            total_equity = cash + total_market_val
            total_unrealized = total_market_val - total_cost_basis

            return {
                "account_id": acct_id,
                "currency": acct.currency,
                "cash_balance": float(cash),
                "current_cash": float(cash),
                "positions_market_value": float(total_market_val),
                "total_cost_basis": float(total_cost_basis),
                "total_equity": float(total_equity),
                "total_portfolio_value": float(total_equity),
                "unrealized_pnl": float(total_unrealized),
                "positions": pos_list,
                "reset_count": acct.reset_count,
                "disclaimer": self.SIMULATION_DISCLAIMER,
            }
        finally:
            if owns_session:
                await session.close()

    async def reset_account_db(self, user_id: str, db: Optional[AsyncSession] = None) -> Dict:
        """Reset virtual paper account back to ₹1,00,000 in PostgreSQL with audit trail."""
        owns_session = db is None
        session = db if db is not None else AsyncSessionLocal()
        try:
            stmt = select(PaperAccount).where(PaperAccount.user_id == user_id).with_for_update()
            res = await session.execute(stmt)
            acct = res.scalar_one_or_none()
            if not acct:
                acct = await self.get_or_create_account_db(user_id, db=session)
            acct_id = acct.id

            # Clear positions
            await session.execute(delete(PaperPosition).where(PaperPosition.account_id == acct_id))

            acct.current_cash = Decimal("100000.00")
            acct.reset_count += 1
            acct.updated_at = datetime.now(timezone.utc)

            # Audit ledger
            led = PaperCashLedger(
                id=f"led-{uuid.uuid4().hex[:12]}",
                account_id=acct_id,
                entry_type="RESET_CREDIT",
                amount=Decimal("100000.00"),
                balance_after=Decimal("100000.00"),
                reference_id=f"RST-{acct.reset_count}",
                description=f"Account reset #{acct.reset_count} back to initial virtual funds",
            )
            session.add(led)
            if owns_session:
                await session.commit()

            _POSITIONS_STORE[acct_id] = {}
            if acct_id in _ACCOUNTS_STORE:
                _ACCOUNTS_STORE[acct_id]["current_cash"] = Decimal("100000.00")
                _ACCOUNTS_STORE[acct_id]["reset_count"] = acct.reset_count

            return {
                "account_id": acct_id,
                "reset_count": acct.reset_count,
                "cash_balance": 100000.00,
                "current_cash": 100000.00,
                "status": "ACTIVE",
                "message": f"Paper trading account successfully reset to ₹1,00,000.00. (Reset count: {acct.reset_count})",
                "disclaimer": self.SIMULATION_DISCLAIMER,
            }
        except Exception:
            if owns_session:
                await session.rollback()
            raise
        finally:
            if owns_session:
                await session.close()

    async def deposit_funds_db(self, user_id: str, amount: Decimal, db: Optional[AsyncSession] = None) -> Dict:
        """Deposit funds atomically in PostgreSQL with audit trail."""
        owns_session = db is None
        session = db if db is not None else AsyncSessionLocal()
        try:
            stmt = select(PaperAccount).where(PaperAccount.user_id == user_id).with_for_update()
            res = await session.execute(stmt)
            acct = res.scalar_one_or_none()
            if not acct:
                acct = await self.get_or_create_account_db(user_id, db=session)
            acct_id = acct.id

            new_cash = Decimal(str(acct.current_cash)) + amount
            acct.current_cash = new_cash
            acct.updated_at = datetime.now(timezone.utc)

            led_id = f"led-{uuid.uuid4().hex[:12]}"
            ref_id = f"DEP-{uuid.uuid4().hex[:6].upper()}"
            led = PaperCashLedger(
                id=led_id,
                account_id=acct_id,
                entry_type="SANDBOX_DEPOSIT",
                amount=amount,
                balance_after=new_cash,
                reference_id=ref_id,
                description=f"Virtual sandbox funds deposit of ₹{amount:,.2f}",
            )
            session.add(led)
            if owns_session:
                await session.commit()

            if acct_id in _ACCOUNTS_STORE:
                _ACCOUNTS_STORE[acct_id]["current_cash"] = new_cash

            return {
                "account_id": acct_id,
                "deposited": float(amount),
                "cash_balance": float(new_cash),
                "current_cash": float(new_cash),
                "entry": {
                    "id": led_id,
                    "account_id": acct_id,
                    "entry_type": "SANDBOX_DEPOSIT",
                    "amount": float(amount),
                    "balance_after": float(new_cash),
                    "reference_id": ref_id,
                    "description": f"Virtual sandbox funds deposit of ₹{amount:,.2f}",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                },
            }
        except Exception:
            if owns_session:
                await session.rollback()
            raise
        finally:
            if owns_session:
                await session.close()

    async def get_orders_db(self, user_id: str, limit: int = 50, db: Optional[AsyncSession] = None) -> List[Dict]:
        """Fetch historical orders from PostgreSQL."""
        owns_session = db is None
        session = db if db is not None else AsyncSessionLocal()
        try:
            acct = await self.get_or_create_account_db(user_id, db=session)
            stmt = (
                select(PaperOrder)
                .where(PaperOrder.account_id == acct.id)
                .order_by(PaperOrder.created_at.desc())
                .limit(limit)
            )
            res = await session.execute(stmt)
            orders = res.scalars().all()
            out = []
            for o in orders:
                receipt = o.execution_receipt or {}
                out.append(
                    {
                        "id": o.id,
                        "account_id": o.account_id,
                        "user_id": o.user_id,
                        "symbol": o.symbol,
                        "side": o.side,
                        "order_type": o.order_type,
                        "quantity": float(o.quantity),
                        "limit_price": float(o.limit_price) if o.limit_price is not None else None,
                        "fill_price": float(o.fill_price) if o.fill_price is not None else 0.0,
                        "gross_value": float(receipt.get("gross_value", 0.0)),
                        "fee": float(o.fee),
                        "net_value": float(receipt.get("net_value", 0.0)),
                        "status": o.status,
                        "rejection_reason": o.rejection_reason,
                        "realized_pnl": float(receipt.get("realized_pnl"))
                        if receipt.get("realized_pnl") is not None
                        else None,
                        "cash_balance_after": float(receipt.get("cash_balance_after", 0.0)),
                        "idempotency_key": o.idempotency_key,
                        "created_at": o.created_at.isoformat() if o.created_at else "",
                    }
                )
            return out
        finally:
            if owns_session:
                await session.close()

    async def get_ledger_db(self, user_id: str, db: Optional[AsyncSession] = None) -> List[Dict]:
        """Fetch ledger entries from PostgreSQL."""
        owns_session = db is None
        session = db if db is not None else AsyncSessionLocal()
        try:
            acct = await self.get_or_create_account_db(user_id, db=session)
            stmt = (
                select(PaperCashLedger)
                .where(PaperCashLedger.account_id == acct.id)
                .order_by(PaperCashLedger.created_at.desc())
            )
            res = await session.execute(stmt)
            entries = res.scalars().all()
            return [
                {
                    "id": e.id,
                    "account_id": e.account_id,
                    "entry_type": e.entry_type,
                    "amount": float(e.amount),
                    "balance_after": float(e.balance_after),
                    "reference_id": e.reference_id,
                    "description": e.description,
                    "created_at": e.created_at.isoformat() if e.created_at else "",
                }
                for e in entries
            ]
        finally:
            if owns_session:
                await session.close()

    async def get_positions_db(self, user_id: str, db: Optional[AsyncSession] = None) -> List[Dict]:
        """Fetch positions from PostgreSQL."""
        summary = await self.get_portfolio_summary_db(user_id, db=db)
        return summary.get("positions", [])

    def _sync_to_memory(
        self,
        acct_id: str,
        user_id: str,
        order: PaperOrder,
        receipt: ExecutionResult,
        cash_after: Decimal,
        pos: Optional[PaperPosition] = None,
        led: Optional[PaperCashLedger] = None,
    ):
        """Synchronize DB state into in-memory store for any external modules."""
        now_str = datetime.now(timezone.utc).isoformat()
        if acct_id not in _ACCOUNTS_STORE:
            _ACCOUNTS_STORE[acct_id] = {
                "id": acct_id,
                "user_id": user_id,
                "initial_balance": Decimal("100000.00"),
                "current_cash": cash_after,
                "currency": "INR",
                "status": "ACTIVE",
                "reset_count": 0,
                "created_at": now_str,
                "updated_at": now_str,
            }
        else:
            _ACCOUNTS_STORE[acct_id]["current_cash"] = cash_after

        if acct_id not in _LEDGER_STORE or not _LEDGER_STORE[acct_id]:
            _LEDGER_STORE[acct_id] = [
                {
                    "id": f"led-init-{acct_id[-6:]}",
                    "account_id": acct_id,
                    "entry_type": "INITIAL_CREDIT",
                    "amount": Decimal("100000.00"),
                    "balance_after": Decimal("100000.00"),
                    "reference_id": "INIT",
                    "description": "Initial virtual paper cash deposit",
                    "created_at": now_str,
                }
            ]

        order_dict = {
            "id": order.id,
            "account_id": acct_id,
            "user_id": user_id,
            "symbol": order.symbol,
            "side": order.side,
            "quantity": order.quantity,
            "order_type": order.order_type,
            "limit_price": order.limit_price,
            "fill_price": order.fill_price,
            "gross_value": receipt.gross_value,
            "fee": receipt.fee,
            "net_value": receipt.net_value,
            "status": order.status,
            "rejection_reason": order.rejection_reason,
            "cash_balance_after": cash_after,
            "realized_pnl": receipt.realized_pnl,
            "idempotency_key": order.idempotency_key,
            "created_at": order.created_at.isoformat() if order.created_at else now_str,
        }
        _ORDERS_STORE[order.id] = order_dict

        if receipt.status == "FILLED":
            if pos is not None and pos.quantity > Decimal("0"):
                _POSITIONS_STORE.setdefault(acct_id, {})[pos.symbol] = {
                    "account_id": acct_id,
                    "symbol": pos.symbol,
                    "quantity": pos.quantity,
                    "average_buy_price": pos.average_buy_price,
                    "total_cost_basis": pos.total_cost_basis,
                    "updated_at": now_str,
                }
            elif order.side == "SELL":
                _POSITIONS_STORE.setdefault(acct_id, {}).pop(order.symbol, None)

            if led is not None:
                _LEDGER_STORE.setdefault(acct_id, []).append(
                    {
                        "id": led.id,
                        "account_id": acct_id,
                        "entry_type": led.entry_type,
                        "amount": led.amount,
                        "balance_after": led.balance_after,
                        "reference_id": led.reference_id,
                        "description": led.description,
                        "created_at": now_str,
                    }
                )
