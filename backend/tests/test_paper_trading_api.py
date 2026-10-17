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

import pytest
from backend.app.domain.paper_trading_coach import generate_trade_coaching
from backend.app.domain.paper_trading_service import (
    _ACCOUNTS_STORE,
    _LEDGER_STORE,
    _ORDERS_STORE,
    _POSITIONS_STORE,
    PaperTradingEngine,
)
from data.quality.paper_trading_reconciliation import PaperTradingReconciler
from httpx import ASGITransport, AsyncClient


@pytest.fixture(scope="module", autouse=True)
def setup_paper_trading_module():
    import asyncio
    from decimal import Decimal

    from backend.app.database import AsyncSessionLocal
    from backend.app.models.paper_trading import PaperAccount, PaperCashLedger, PaperOrder, PaperPosition, PaperTrade
    from sqlalchemy import delete, select

    async def _clean():
        async with AsyncSessionLocal() as session:
            stmt_acct = select(PaperAccount).where(PaperAccount.user_id == "usr-shivraj-001")
            res = await session.execute(stmt_acct)
            acct = res.scalar_one_or_none()
            if acct:
                acct_id = acct.id
                await session.execute(delete(PaperTrade).where(PaperTrade.account_id == acct_id))
                await session.execute(delete(PaperOrder).where(PaperOrder.account_id == acct_id))
                await session.execute(delete(PaperPosition).where(PaperPosition.account_id == acct_id))
                await session.execute(delete(PaperCashLedger).where(PaperCashLedger.account_id == acct_id))
                acct.current_cash = Decimal("100000.00")
                acct.reset_count = 0
                led_init = PaperCashLedger(
                    id=f"led-init-{acct_id[-6:]}",
                    account_id=acct_id,
                    entry_type="INITIAL_CREDIT",
                    amount=Decimal("100000.00"),
                    balance_after=Decimal("100000.00"),
                    reference_id="INIT",
                    description="Initial virtual paper cash deposit",
                )
                session.add(led_init)
                await session.commit()

    _ORDERS_STORE.clear()
    _POSITIONS_STORE.clear()
    _LEDGER_STORE.clear()
    _ACCOUNTS_STORE.clear()
    asyncio.run(_clean())
    yield


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
        assert (
            "Capital Discipline" in coach_buy.learning_points[0] or "Opportunity Cost" in coach_buy.learning_points[0]
        )
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


@pytest.mark.asyncio
async def test_non_marketable_limit_buy_rejected_never_fills_above_limit(app, auth_headers):
    """CH-05: LIMIT buy at INR 1.00 must never fill at market price of INR 2,500."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/v1/paper-trading/orders",
            json={
                "symbol": "RELIANCE",
                "side": "BUY",
                "quantity": 10.0,
                "order_type": "LIMIT",
                "limit_price": 1.00,
                "idempotency_key": "idemp-limit-buy-underpriced-01",
            },
            headers=auth_headers,
        )
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["status"] == "REJECTED"
        assert "exceeds submitted limit price" in data["rejection_reason"]
        assert float(data["fill_price"]) == 0.0


@pytest.mark.asyncio
async def test_idempotency_same_key_same_payload_returns_identical_receipt(app, auth_headers):
    """CH-05: Submitting identical key and payload returns saved receipt with 1 financial effect."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # First execution
        payload = {
            "symbol": "RELIANCE",
            "side": "BUY",
            "quantity": 2.0,
            "order_type": "MARKET",
            "idempotency_key": "idemp-repro-exact-01",
        }
        res1 = await client.post("/api/v1/paper-trading/orders", json=payload, headers=auth_headers)
        assert res1.status_code == 200
        data1 = res1.json()["data"]
        assert data1["status"] == "FILLED"
        order_id1 = data1["order_id"]
        cash_after1 = data1["cash_balance_after"]

        # Identical second execution
        res2 = await client.post("/api/v1/paper-trading/orders", json=payload, headers=auth_headers)
        assert res2.status_code == 200
        data2 = res2.json()["data"]
        assert data2["order_id"] == order_id1
        assert data2["cash_balance_after"] == cash_after1


@pytest.mark.asyncio
async def test_idempotency_same_key_changed_payload_returns_409_conflict(app, auth_headers):
    """CH-05: Submitting same key with changed payload produces HTTP 409 Conflict without second execution."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # First order: 2 RELIANCE
        res1 = await client.post(
            "/api/v1/paper-trading/orders",
            json={
                "symbol": "RELIANCE",
                "side": "BUY",
                "quantity": 2.0,
                "order_type": "MARKET",
                "idempotency_key": "idemp-collision-test-01",
            },
            headers=auth_headers,
        )
        assert res1.status_code == 200

        # Second order: Same key, changed symbol TCS
        res2 = await client.post(
            "/api/v1/paper-trading/orders",
            json={
                "symbol": "TCS",
                "side": "BUY",
                "quantity": 2.0,
                "order_type": "MARKET",
                "idempotency_key": "idemp-collision-test-01",
            },
            headers=auth_headers,
        )
        assert res2.status_code == 409
        assert "collision" in res2.json()["detail"].lower()


@pytest.mark.asyncio
async def test_idempotency_replay_preserves_historical_cash_after(app, auth_headers):
    """CH-05: Replaying an old order after subsequent trades returns original cash-after receipt."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Order 1: 1 RELIANCE
        res1 = await client.post(
            "/api/v1/paper-trading/orders",
            json={
                "symbol": "RELIANCE",
                "side": "BUY",
                "quantity": 1.0,
                "order_type": "MARKET",
                "idempotency_key": "idemp-history-test-01",
            },
            headers=auth_headers,
        )
        cash_after1 = res1.json()["data"]["cash_balance_after"]

        # Order 2: 1 TCS (causes cash balance to decrease further)
        res2 = await client.post(
            "/api/v1/paper-trading/orders",
            json={
                "symbol": "TCS",
                "side": "BUY",
                "quantity": 1.0,
                "order_type": "MARKET",
                "idempotency_key": "idemp-history-test-02",
            },
            headers=auth_headers,
        )
        cash_after2 = res2.json()["data"]["cash_balance_after"]
        assert cash_after2 < cash_after1

        # Replay Order 1 with original key: MUST return original cash_after1, not current cash_after2!
        replay = await client.post(
            "/api/v1/paper-trading/orders",
            json={
                "symbol": "RELIANCE",
                "side": "BUY",
                "quantity": 1.0,
                "order_type": "MARKET",
                "idempotency_key": "idemp-history-test-01",
            },
            headers=auth_headers,
        )
        assert replay.status_code == 200
        assert replay.json()["data"]["cash_balance_after"] == cash_after1


@pytest.mark.asyncio
async def test_paper_trading_deposit_and_contract_fields(app, auth_headers):
    """Test authorized deposit endpoint and verify both cash_balance and current_cash contract fields."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Check account before deposit
        acct_before = await client.get("/api/v1/paper-trading/account", headers=auth_headers)
        assert acct_before.status_code == 200
        data_before = acct_before.json()["data"]
        assert "cash_balance" in data_before
        assert "current_cash" in data_before
        assert data_before["cash_balance"] == data_before["current_cash"]
        initial_cash = data_before["cash_balance"]

        # 2. Deposit ₹25,000
        deposit_res = await client.post(
            "/api/v1/paper-trading/deposit",
            json={"amount": 25000.0},
            headers=auth_headers,
        )
        assert deposit_res.status_code == 200
        deposit_data = deposit_res.json()["data"]
        assert deposit_data["deposited"] == 25000.0
        assert deposit_data["cash_balance"] == initial_cash + 25000.0

        # 3. Check account after deposit
        acct_after = await client.get("/api/v1/paper-trading/account", headers=auth_headers)
        assert acct_after.status_code == 200
        data_after = acct_after.json()["data"]
        assert data_after["cash_balance"] == initial_cash + 25000.0
        assert data_after["current_cash"] == initial_cash + 25000.0


@pytest.mark.asyncio
async def test_stale_quote_rejects_trade_execution(app, auth_headers):
    """Verify that an ineligible stale market quote cannot execute a trade."""
    from datetime import datetime, timedelta, timezone
    from decimal import Decimal

    from backend.app.ports.market_data import Quote
    from backend.app.routers.paper_trading import engine

    # Inject a quote that is 10 days old (severely stale)
    stale_time = datetime.now(timezone.utc) - timedelta(days=10)
    stale_quote = Quote(
        canonical_id="NSE:STALECO",
        symbol="STALECO.NS",
        price=Decimal("500.00"),
        currency="INR",
        observed_at=stale_time,
        ingested_at=datetime.now(timezone.utc),
        source="stale_feed",
        served_from_cache=False,
        is_delayed=True,
        is_stale=True,
        data_status="stale",
    )
    engine.market_provider.set_quote_override("STALECO", stale_quote)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Check cash before
        acct_before = await client.get("/api/v1/paper-trading/account", headers=auth_headers)
        cash_before = acct_before.json()["data"]["cash_balance"]

        # Attempt to buy STALECO
        res = await client.post(
            "/api/v1/paper-trading/orders",
            json={
                "symbol": "STALECO",
                "side": "BUY",
                "quantity": 5.0,
                "order_type": "MARKET",
                "idempotency_key": "idemp-stale-quote-order-01",
            },
            headers=auth_headers,
        )
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["status"] == "REJECTED"
        assert "stale" in data["rejection_reason"].lower()
        assert float(data["fill_price"]) == 0.0

        # Verify cash was untouched
        acct_after = await client.get("/api/v1/paper-trading/account", headers=auth_headers)
        cash_after = acct_after.json()["data"]["cash_balance"]
        assert cash_after == cash_before
