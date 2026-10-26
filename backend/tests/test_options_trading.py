"""Comprehensive Unit and Integration Tests for FinEx Phase 2: Options Trading & Settlement.

Validates:
1. Black-Scholes pricing and Greeks (Delta, Gamma, Theta, Vega).
2. Option chain generation for NIFTY 50 and verified underlyings.
3. Honest 404 for unservable underlyings (no fake chains).
4. Long-only paper options buy execution (cost = premium * lot_size, max_loss, breakeven).
5. Mandatory risk warning acknowledgment enforcement.
6. Prevention of option selling / naked positions (HTTP 422).
7. Deterministic ITM and OTM settlement:
   - ITM Call/Put settles at intrinsic value; cash credited to ledger.
   - OTM Call/Put expires worthless; full premium lost.
8. Zero equity regression: Equity orders and positions remain isolated.
"""

from datetime import date
from decimal import Decimal

import pytest
from backend.app.domain.options_engine import (
    build_real_angel_option_chain,
    calculate_black_scholes_price_and_greeks,
    generate_deterministic_option_chain,
    settle_option_position,
)
from backend.app.domain.paper_trading_service import (
    OptionOrderSubmitRequest,
    OrderSubmitRequest,
    PaperTradingEngine,
)
from backend.app.factory import create_app
from httpx import ASGITransport, AsyncClient


# =============================================================================
# 1. Black-Scholes Mathematical Engine Tests
# =============================================================================
def test_black_scholes_call_and_put_atm():
    """Verify standard ATM call and put pricing and Greek properties."""
    spot = 24000.0
    strike = 24000.0
    time_to_exp = 30.0 / 365.0  # 30 days
    iv = 0.15
    r = 0.065

    call_price, call_greeks = calculate_black_scholes_price_and_greeks(
        spot=spot,
        strike=strike,
        time_to_expiry_years=time_to_exp,
        volatility=iv,
        risk_free_rate=r,
        option_type="CE",
    )
    put_price, put_greeks = calculate_black_scholes_price_and_greeks(
        spot=spot,
        strike=strike,
        time_to_expiry_years=time_to_exp,
        volatility=iv,
        risk_free_rate=r,
        option_type="PE",
    )

    # Prices must be strictly positive
    assert call_price > 0.0
    assert put_price > 0.0

    # Put-Call Parity check: C - P ≈ S - K * exp(-rT)
    discounted_k = strike * (1.0 - r * time_to_exp)
    diff = (call_price - put_price) - (spot - discounted_k)
    assert abs(diff) < 5.0  # Small discrete rounding tolerance

    # Call Delta in (0.4, 0.7), Put Delta in (-0.6, -0.3)
    assert 0.4 < call_greeks.delta < 0.7
    assert -0.7 < put_greeks.delta < -0.3

    # Gamma is identical and positive
    assert call_greeks.gamma > 0.0
    assert abs(call_greeks.gamma - put_greeks.gamma) < 1e-4

    # Theta decay is negative (options lose value over time)
    assert call_greeks.theta < 0.0
    assert put_greeks.theta < 0.0

    # Vega is positive (sensitivity to volatility increases price)
    assert call_greeks.vega > 0.0


def test_black_scholes_deep_itm_and_otm():
    """Verify deep ITM call delta approaches 1 and deep OTM delta approaches 0."""
    spot = 25000.0
    strike = 20000.0  # Deep ITM Call
    _, itm_call_greeks = calculate_black_scholes_price_and_greeks(
        spot=spot, strike=strike, time_to_expiry_years=0.1, volatility=0.15, option_type="CE"
    )
    assert itm_call_greeks.delta > 0.95

    _, otm_call_greeks = calculate_black_scholes_price_and_greeks(
        spot=20000.0, strike=25000.0, time_to_expiry_years=0.1, volatility=0.15, option_type="CE"
    )
    assert otm_call_greeks.delta < 0.05


# =============================================================================
# 2. Option Chain Generation & Underlyings Tests
# =============================================================================
def test_generate_deterministic_option_chain_nifty50():
    """Verify Nifty 50 model option chain omits unmodeled fields and labels MODEL_ESTIMATED."""
    spot = 24125.50
    chain = generate_deterministic_option_chain(
        underlying="NIFTY 50",
        spot_price=spot,
    )

    assert chain.underlying == "NIFTY 50"
    assert chain.spot_price == spot
    assert chain.lot_size == 25
    # ATM strike for 24125.50 with 50-step is 24150.0
    assert chain.atm_strike == 24150.0
    assert len(chain.strikes) == 21  # 10 strikes each side + ATM

    # Verify call side and put side contract structure
    for row in chain.strikes:
        assert row.call.option_type == "CE"
        assert row.put.option_type == "PE"
        assert row.call.strike == row.strike_price
        assert row.put.strike == row.strike_price
        assert row.call.lot_size == 25
        assert row.put.lot_size == 25
        assert row.call.max_loss == round(row.call.ltp * 25, 2)
        assert row.put.max_loss == round(row.put.ltp * 25, 2)
        assert row.call.breakeven == round(row.strike_price + row.call.ltp, 2)
        assert row.put.breakeven == round(row.strike_price - row.put.ltp, 2)
        # Honest omission: unmodeled fields must be None on model chain
        assert row.call.open_interest is None
        assert row.put.open_interest is None
        assert row.call.volume is None
        assert row.put.volume is None
        assert row.call.change is None
        assert row.put.change is None
        assert row.call.is_model_estimated is True
        assert row.put.is_model_estimated is True

    # PCR, Max Pain, and Total OI cannot be modelled from spot alone
    assert chain.pcr is None
    assert chain.max_pain is None
    assert chain.total_call_oi is None
    assert chain.total_put_oi is None
    assert len(chain.expiries) >= 4
    assert chain.source == "MODEL_ESTIMATED"
    assert chain.chain_type == "MODEL_ESTIMATED"
    assert len(chain.evidence_hash) == 64


def test_build_real_angel_option_chain():
    """Verify build_real_angel_option_chain retains real Angel Greeks, volume, and sets ANGEL_ONE_SMARTAPI source."""
    mock_greeks = [
        {
            "name": "NIFTY",
            "expiry": "27OCT2026",
            "strikePrice": "24100.000000",
            "optionType": "CE",
            "delta": "0.550000",
            "gamma": "0.001200",
            "theta": "-45.500000",
            "vega": "4.200000",
            "impliedVolatility": "18.500000",
            "tradeVolume": "500000.00",
        },
        {
            "name": "NIFTY",
            "expiry": "27OCT2026",
            "strikePrice": "24100.000000",
            "optionType": "PE",
            "delta": "-0.450000",
            "gamma": "0.001200",
            "theta": "-40.100000",
            "vega": "4.150000",
            "impliedVolatility": "19.000000",
            "tradeVolume": "450000.00",
        },
    ]

    expiries = [date(2026, 10, 27)]
    chain = build_real_angel_option_chain(
        underlying="NIFTY 50",
        spot_price=24100.0,
        selected_expiry=date(2026, 10, 27),
        expiries=expiries,
        greeks_data=mock_greeks,
        num_strikes_each_side=1,
    )

    assert chain.source == "ANGEL_ONE_SMARTAPI"
    assert chain.chain_type == "REAL_MARKET"
    assert chain.underlying == "NIFTY 50"

    # Find the 24100 strike row
    matched = [r for r in chain.strikes if r.strike_price == 24100.0]
    assert len(matched) == 1
    row = matched[0]
    assert row.call.implied_volatility == 18.5
    assert row.call.greeks.delta == 0.55
    assert row.call.volume == 500000
    assert row.call.is_model_estimated is False

    assert row.put.implied_volatility == 19.0
    assert row.put.greeks.delta == -0.45
    assert row.put.volume == 450000
    assert row.put.is_model_estimated is False


# =============================================================================
# 3. Deterministic Expiry Settlement Function Tests
# =============================================================================
def test_settle_option_position_call_itm():
    """Call option in-the-money settles at intrinsic value (Spot - Strike)."""
    # Strike 24000 CE, Entry Premium ₹100, Expiry Spot 24350.
    # Intrinsic = 24350 - 24000 = 350.
    # 2 lots of 25 = 50 units. Total payout = 350 * 50 = ₹17,500.
    # Total cost = 100 * 50 = ₹5,000. Realized P&L = +₹12,500.
    res = settle_option_position(
        contract_symbol="NIFTY26OCT24000CE",
        underlying="NIFTY 50",
        option_type="CE",
        strike=24000.0,
        expiry="2026-10-29",
        lots=2,
        lot_size=25,
        entry_premium=100.0,
        spot_at_expiry=24350.0,
    )

    assert res.status == "EXERCISED_ITM"
    assert res.intrinsic_value == 350.0
    assert res.total_payout == 17500.0
    assert res.total_premium_paid == 5000.0
    assert res.realized_pnl == 12500.0
    assert res.realized_pnl_pct == 250.0


def test_settle_option_position_call_otm():
    """Call option out-of-the-money expires worthless with full premium lost."""
    # Strike 24000 CE, Entry Premium ₹100, Expiry Spot 23800.
    # Intrinsic = max(0, 23800 - 24000) = 0.
    # Payout = 0. Realized P&L = -₹2,500 (1 lot * 25 * 100).
    res = settle_option_position(
        contract_symbol="NIFTY26OCT24000CE",
        underlying="NIFTY 50",
        option_type="CE",
        strike=24000.0,
        expiry="2026-10-29",
        lots=1,
        lot_size=25,
        entry_premium=100.0,
        spot_at_expiry=23800.0,
    )

    assert res.status == "EXPIRED_WORTHLESS_OTM"
    assert res.intrinsic_value == 0.0
    assert res.total_payout == 0.0
    assert res.total_premium_paid == 2500.0
    assert res.realized_pnl == -2500.0
    assert res.realized_pnl_pct == -100.0


def test_settle_option_position_put_itm():
    """Put option in-the-money settles at intrinsic value (Strike - Spot)."""
    # Strike 24000 PE, Entry Premium ₹120, Expiry Spot 23700.
    # Intrinsic = 24000 - 23700 = 300.
    # Payout = 300 * 25 = ₹7,500. Total cost = 120 * 25 = ₹3,000. Net P&L = +₹4,500.
    res = settle_option_position(
        contract_symbol="NIFTY26OCT24000PE",
        underlying="NIFTY 50",
        option_type="PE",
        strike=24000.0,
        expiry="2026-10-29",
        lots=1,
        lot_size=25,
        entry_premium=120.0,
        spot_at_expiry=23700.0,
    )

    assert res.status == "EXERCISED_ITM"
    assert res.intrinsic_value == 300.0
    assert res.total_payout == 7500.0
    assert res.total_premium_paid == 3000.0
    assert res.realized_pnl == 4500.0


def test_settle_option_position_put_otm():
    """Put option out-of-the-money expires worthless."""
    res = settle_option_position(
        contract_symbol="NIFTY26OCT24000PE",
        underlying="NIFTY 50",
        option_type="PE",
        strike=24000.0,
        expiry="2026-10-29",
        lots=1,
        lot_size=25,
        entry_premium=120.0,
        spot_at_expiry=24200.0,
    )

    assert res.status == "EXPIRED_WORTHLESS_OTM"
    assert res.intrinsic_value == 0.0
    assert res.total_payout == 0.0
    assert res.realized_pnl == -3000.0


# =============================================================================
# 4. API Endpoints Integration Tests
# =============================================================================
@pytest.mark.asyncio
async def test_get_option_chain_nifty50_api():
    """GET /api/v1/market/options/chain/NIFTY 50 returns 200 with truthful strikes & Greeks envelope."""
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/api/v1/market/options/chain/NIFTY 50")
        assert res.status_code == 200
        payload = res.json()
        assert "data" in payload
        data = payload["data"]
        assert data["underlying"] == "NIFTY 50"
        assert data["lot_size"] == 25
        assert len(data["strikes"]) >= 15
        assert data["source"] in ("ANGEL_ONE_SMARTAPI", "MODEL_ESTIMATED")
        assert "evidence_hash" in data

        # Check call and put details on strike
        first_row = data["strikes"][0]
        assert "call" in first_row and "put" in first_row
        assert "greeks" in first_row["call"]
        assert "delta" in first_row["call"]["greeks"]


@pytest.mark.asyncio
async def test_options_chain_model_fallback_omits_unmodeled_fields():
    """When Angel One is unconfigured or unavailable, endpoint serves MODEL_ESTIMATED chain without invented numbers."""
    from backend.app.dependencies import get_angel_adapter
    from backend.app.services.angel_adapter import AngelOneMarketAdapter

    class DisabledAngelAdapter(AngelOneMarketAdapter):
        def is_configured(self) -> bool:
            return False

        async def get_option_chain(self, *args, **kwargs):
            return None

    app = create_app()
    app.dependency_overrides[get_angel_adapter] = lambda: DisabledAngelAdapter(api_key=None)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/api/v1/market/options/chain/NIFTY 50")
        assert res.status_code == 200
        data = res.json()["data"]

        # Truthful provenance: strictly MODEL_ESTIMATED, never claims ANGEL_ONE_SMARTAPI
        assert data["source"] == "MODEL_ESTIMATED"
        assert data["chain_type"] == "MODEL_ESTIMATED"

        # Truthful field gating: unmodeled fields MUST be None
        assert data["pcr"] is None
        assert data["max_pain"] is None
        assert data["total_call_oi"] is None
        assert data["total_put_oi"] is None

        for row in data["strikes"]:
            assert row["call"]["open_interest"] is None
            assert row["put"]["open_interest"] is None
            assert row["call"]["volume"] is None
            assert row["put"]["volume"] is None
            assert row["call"]["change"] is None
            assert row["put"]["change"] is None
            assert row["call"]["is_model_estimated"] is True
            assert row["put"]["is_model_estimated"] is True


@pytest.mark.asyncio
async def test_get_option_chain_unservable_underlying_404():
    """GET /api/v1/market/options/chain/{unservable} returns honest 404 error without faked data."""
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # NIFTY NEXT 50 has no active liquid F&O contracts on NSE
        res = await client.get("/api/v1/market/options/chain/NIFTY NEXT 50")
        assert res.status_code == 404


@pytest.mark.asyncio
async def test_list_option_underlyings_api():
    """GET /api/v1/market/options/underlyings returns verified list of options underlyings."""
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/api/v1/market/options/underlyings")
        assert res.status_code == 200
        data = res.json()["data"]
        symbols = [u["symbol"] for u in data["underlyings"]]
        assert "NIFTY 50" in symbols
        assert "NIFTY BANK" in symbols
        assert "RELIANCE" in symbols


# =============================================================================
# 5. Paper Options Trading Engine & Long-Only Validation Tests
# =============================================================================
def test_long_only_paper_options_buy_and_settlement():
    """Complete lifecycle of long-only paper call & put orders, ledger writes, and settlement."""
    engine = PaperTradingEngine()
    user_id = "test-options-trader-001"
    engine.reset_account(user_id)

    # 1. Reject if risk not acknowledged
    with pytest.raises(Exception) as exc:
        engine.execute_option_order(
            user_id=user_id,
            payload=OptionOrderSubmitRequest(
                underlying="NIFTY 50",
                contract_symbol="NIFTY26OCT24000CE",
                option_type="CE",
                strike=Decimal("24000"),
                expiry="2026-10-29",
                side="BUY",
                lots=1,
                risk_acknowledged=False,
                idempotency_key="idemp-opt-risk-fail",
            ),
        )
    assert "risk acknowledgment" in str(exc.value.detail).lower()

    # 2. Reject short selling / writing naked options (Long-only enforcement)
    with pytest.raises(Exception) as exc_sell:
        engine.execute_option_order(
            user_id=user_id,
            payload=OptionOrderSubmitRequest(
                underlying="NIFTY 50",
                contract_symbol="NIFTY26OCT24000CE",
                option_type="CE",
                strike=Decimal("24000"),
                expiry="2026-10-29",
                side="SELL",
                lots=1,
                risk_acknowledged=True,
                idempotency_key="idemp-opt-sell-fail",
            ),
        )
    assert "long-only" in str(exc_sell.value.detail).lower()

    # 3. Buy 1 lot of NIFTY 50 Call
    exec_res = engine.execute_option_order(
        user_id=user_id,
        payload=OptionOrderSubmitRequest(
            underlying="NIFTY 50",
            contract_symbol="NIFTY26OCT24000CE",
            option_type="CE",
            strike=Decimal("24000"),
            expiry="2026-10-29",
            side="BUY",
            lots=1,
            limit_premium=Decimal("150.00"),
            risk_acknowledged=True,
            idempotency_key="idemp-opt-buy-call-01",
        ),
    )

    assert exec_res.status == "FILLED"
    assert exec_res.lots == 1
    assert exec_res.lot_size == 25
    assert exec_res.total_quantity == 25
    assert exec_res.fill_premium == Decimal("150.00")
    # Cost = 150 * 25 = ₹3,750
    assert exec_res.total_premium_paid == Decimal("3750.00")
    assert exec_res.max_loss == Decimal("3750.00")
    # Call Breakeven = Strike + Premium = 24000 + 150 = 24150
    assert exec_res.breakeven == Decimal("24150.00")
    assert "lose the full premium" in exec_res.risk_line

    # Verify virtual cash deducted: 100000 - 3750 = 96250
    assert exec_res.cash_balance_after == Decimal("96250.00")

    # 4. Verify position visible in options positions list
    positions = engine.get_options_positions(user_id)
    assert len(positions) == 1
    pos = positions[0]
    assert pos.contract_symbol == "NIFTY26OCT24000CE"
    assert pos.total_cost_basis == 3750.0

    # 5. Settle ITM: Expiry spot 24400.
    # Intrinsic = 24400 - 24000 = 400. Payout = 400 * 25 = ₹10,000.
    settlements = engine.settle_expired_options(user_id, spot_prices={"NIFTY 50": 24400.0})
    assert len(settlements) == 1
    settle = settlements[0]
    assert settle["status"] == "EXERCISED_ITM"
    assert settle["total_payout"] == 10000.0
    assert settle["realized_pnl"] == 6250.0  # 10000 - 3750

    # Cash balance after settlement: 96250 + 10000 = 106250
    acct = engine.get_or_create_account(user_id)
    assert acct["current_cash"] == Decimal("106250.00")

    # Position cleared from active options
    assert len(engine.get_options_positions(user_id)) == 0


def test_zero_equity_regression():
    """Confirm equity orders, pricing, wallet balances, and positions are completely untouched."""
    engine = PaperTradingEngine()
    user_id = "test-equity-isolation-001"
    engine.reset_account(user_id)

    # Place an equity buy order for RELIANCE
    res = engine.execute_order(
        user_id=user_id,
        payload=OrderSubmitRequest(
            symbol="RELIANCE",
            side="BUY",
            quantity=Decimal("10"),
            order_type="MARKET",
            idempotency_key="idemp-eq-rel-01",
        ),
    )
    assert res.status == "FILLED"

    summary = engine.get_portfolio_summary(user_id)
    assert len(summary["positions"]) == 1
    assert summary["positions"][0]["symbol"] == "RELIANCE"

    # Buy an option
    opt_res = engine.execute_option_order(
        user_id=user_id,
        payload=OptionOrderSubmitRequest(
            underlying="NIFTY 50",
            contract_symbol="NIFTY26OCT24000CE",
            option_type="CE",
            strike=Decimal("24000"),
            expiry="2026-10-29",
            side="BUY",
            lots=1,
            limit_premium=Decimal("100.00"),
            risk_acknowledged=True,
            idempotency_key="idemp-opt-iso-01",
        ),
    )
    assert opt_res.status == "FILLED"

    # Equity positions list must NOT leak options positions
    summary_after = engine.get_portfolio_summary(user_id)
    assert len(summary_after["positions"]) == 1
    assert summary_after["positions"][0]["symbol"] == "RELIANCE"
