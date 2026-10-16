"""Integration, Reconciliation, and Contract Tests for Sprint 5 Paper Trading.

Task ID: S5-PRD-03, S5-API-01, S5-API-02, S5-API-03, S5-DAT-03, S5-AI-01
Tests:
- Account bootstrap with ₹1,00,000 virtual cash
- Atomic Market BUY: cash deduction, position creation, append-only ledger
- Insufficient cash order rejection without state alteration
- Oversell / Short-selling rejection without holding
- Market SELL: partial position liquidation, realized P&L, cash credit
- Idempotency key deduplication: identical payload returns original result without duplicate debit
- Reconciliation: verify cash balance equals ledger sum and position equals trade history
- Account Reset: restores ₹1,00,000 and records audit trail
- Paper Trading Coach: deterministic coaching insight and simulation disclaimer
"""

from decimal import Decimal
import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.config import Settings
from backend.app.domain.paper_trading_coach import generate_performance_narrative, generate_trade_coaching
from backend.app.domain.paper_trading_service import (
    OrderSubmitRequest,
    PaperTradingEngine,
    _LEDGER_STORE,
    _ORDERS_STORE,
    _POSITIONS_STORE,
)
from backend.app.factory import create_app
from data.quality.paper_trading_reconciliation import PaperTradingReconciler


@pytest.fixture
def app():
    settings = Settings(
        ENVIRONMENT="testing",
        SECRET_KEY="test_secret_key_minimum_32_characters_long_for_security",
    )
    return create_app(settings)


@pytest.fixture
def auth_headers():
    return {"Authorization": "Bearer mock-valid-token-user-123"}


@pytest.mark.asyncio
async def test_paper_account_bootstrap_and_get(app, auth_headers):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/paper-trading/account", headers=auth_headers)
        assert res.status_code == 200
        data = res.json()["data"]

        assert data["cash_balance"] == 100000.00
        assert data["total_equity"] == 100000.00
        assert data["currency"] == "INR"
        assert "VIRTUAL TRADING DISCLAIMER" in data["disclaimer"]


@pytest.mark.asyncio
async def test_paper_buy_insufficient_cash_rejected(app, auth_headers):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # RELIANCE price is ₹2,500. 100 shares = ₹2,50,000 (exceeds ₹1,00,000 virtual balance)
        res = await client.post(
            "/api/v1/paper-trading/orders",
            json={
                "symbol": "RELIANCE",
                "side": "BUY",
                "quantity": 100.0,
                "order_type": "MARKET",
                "idempotency_key": "idemp-insufficient-cash-01",
            },
            headers=auth_headers,
        )
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["status"] == "REJECTED"
        assert "Insufficient virtual cash" in data["rejection_reason"]
        assert float(data["cash_balance_after"]) == 100000.00


@pytest.mark.asyncio
async def test_paper_sell_insufficient_holdings_rejected(app, auth_headers):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Attempting to sell TCS without holding any shares
        res = await client.post(
            "/api/v1/paper-trading/orders",
            json={
                "symbol": "TCS",
                "side": "SELL",
                "quantity": 10.0,
                "order_type": "MARKET",
                "idempotency_key": "idemp-short-sell-prevent-01",
            },
            headers=auth_headers,
        )
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["status"] == "REJECTED"
        assert "Insufficient holding quantity" in data["rejection_reason"]


@pytest.mark.asyncio
async def test_paper_buy_and_partial_sell_lifecycle(app, auth_headers):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Buy 10 shares of RELIANCE @ ₹2,500 = ₹25,000
        buy_res = await client.post(
            "/api/v1/paper-trading/orders",
            json={
                "symbol": "RELIANCE",
                "side": "BUY",
                "quantity": 10.0,
                "order_type": "MARKET",
                "idempotency_key": "idemp-buy-rel-01",
            },
            headers=auth_headers,
        )
        assert buy_res.status_code == 200
        buy_data = buy_res.json()["data"]
        assert buy_data["status"] == "FILLED"
        assert float(buy_data["cash_balance_after"]) == 75000.00

        # Verify coaching commentary on buy
        from backend.app.domain.paper_trading_service import ExecutionResult
        coach_buy = generate_trade_coaching(ExecutionResult(**buy_data))
        assert "Buy Order Filled" in coach_buy.headline
        assert "Capital Discipline" in coach_buy.learning_points[0] or "Opportunity Cost" in coach_buy.learning_points[0]
        assert "SIMULATION NOTICE" in coach_buy.disclaimer

        # 2. Re-submitting the exact same idempotency key must deduplicate
        dup_res = await client.post(
            "/api/v1/paper-trading/orders",
            json={
                "symbol": "RELIANCE",
                "side": "BUY",
                "quantity": 10.0,
                "order_type": "MARKET",
                "idempotency_key": "idemp-buy-rel-01",
            },
            headers=auth_headers,
        )
        assert dup_res.status_code == 200
        assert dup_res.json()["data"]["order_id"] == buy_data["order_id"]
        # Cash must remain ₹75,000 (NOT deducted twice)
        assert float(dup_res.json()["data"]["cash_balance_after"]) == 75000.00

        # 3. Sell partial position (4 shares of RELIANCE @ ₹2,500 = ₹10,000 credit)
        sell_res = await client.post(
            "/api/v1/paper-trading/orders",
            json={
                "symbol": "RELIANCE",
                "side": "SELL",
                "quantity": 4.0,
                "order_type": "MARKET",
                "idempotency_key": "idemp-sell-rel-01",
            },
            headers=auth_headers,
        )
        assert sell_res.status_code == 200
        sell_data = sell_res.json()["data"]
        assert sell_data["status"] == "FILLED"
        assert float(sell_data["cash_balance_after"]) == 85000.00

        # 4. Check positions: remaining quantity must be 6
        pos_res = await client.get("/api/v1/paper-trading/positions", headers=auth_headers)
        assert pos_res.status_code == 200
        positions = pos_res.json()["data"]["positions"]
        rel_pos = next(p for p in positions if p["symbol"] == "RELIANCE")
        assert rel_pos["quantity"] == 6.0

        # 5. Check append-only cash ledger
        led_res = await client.get("/api/v1/paper-trading/ledger", headers=auth_headers)
        assert led_res.status_code == 200
        ledger = led_res.json()["data"]["ledger"]
        assert len(ledger) >= 3  # Initial + Buy + Sell


@pytest.mark.asyncio
async def test_paper_trading_reconciliation_zero_breaks(app, auth_headers):
    """Verify that ledger entries sum exactly to cash balance, and positions equal trade totals."""
    engine = PaperTradingEngine()
    user_id = "usr-shivraj-001"
    acct = engine.get_or_create_account(user_id)
    acct_id = acct["id"]

    orders = list(_ORDERS_STORE.values())
    positions = list(_POSITIONS_STORE.get(acct_id, {}).values())
    ledger = _LEDGER_STORE.get(acct_id, [])

    # Synthesize trades from filled orders
    trades = [
        {
            "account_id": o["account_id"],
            "symbol": o["symbol"],
            "side": o["side"],
            "quantity": o["quantity"],
            "price": o["fill_price"],
        }
        for o in orders
        if o["account_id"] == acct_id and o["status"] == "FILLED"
    ]

    reconciler = PaperTradingReconciler()
    report = reconciler.reconcile_account(
        account=acct,
        orders=orders,
        trades=trades,
        positions=positions,
        ledger=ledger,
    )

    assert report.is_clean is True
    assert report.cash_reconciled is True
    assert report.positions_reconciled is True
    assert len(report.breaks) == 0


@pytest.mark.asyncio
async def test_paper_account_reset(app, auth_headers):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/v1/paper-trading/reset",
            json={"confirm_reset": True},
            headers=auth_headers,
        )
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["reset"] is True
        assert data["summary"]["cash_balance"] == 100000.00
        assert len(data["summary"]["positions"]) == 0
