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

from backend.app.adapters.market_data_provider import VERIFIED_OBSERVATIONS
from fastapi import HTTPException, status
from pydantic import BaseModel, Field


class OrderSubmitRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=20)
    side: str = Field(..., description="'BUY' or 'SELL'")
    quantity: Decimal = Field(..., gt=0, description="Positive quantity of shares to trade")
    order_type: str = Field("MARKET", description="'MARKET' or 'LIMIT'")
    limit_price: Optional[Decimal] = None
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

    def get_market_price(self, symbol: str) -> Optional[Decimal]:
        """Fetch verified observation price for symbol."""
        sym = symbol.upper().strip()
        obs = VERIFIED_OBSERVATIONS.get(sym)
        if obs:
            return obs["price"]
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
            # Check for conflict: same key with different payload
            if existing_order.get("fingerprint") and existing_order["fingerprint"] != fingerprint:
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

        # 2. Price verification & Limit marketability rules
        market_price = self.get_market_price(sym)
        order_id = f"ord-{uuid.uuid4().hex[:12]}"

        if not market_price:
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
            "positions_market_value": float(total_market_val),
            "total_cost_basis": float(total_cost_basis),
            "total_equity": float(total_equity),
            "unrealized_pnl": float(total_unrealized),
            "positions": pos_list,
            "reset_count": acct["reset_count"],
            "disclaimer": self.SIMULATION_DISCLAIMER,
        }
