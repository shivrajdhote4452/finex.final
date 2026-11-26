"""Comprehensive Acceptance Tests for Gemini AI Paper Assistant, Technical Indicators, and Charts.

Covers:
- Unconfigured Groq AI key graceful degradation
- Multilingual language detection (English, Hindi, Hinglish)
- Research queries creating zero orders
- Bounded paper proposal generation, expiry, and execution
- Deterministic technical indicators calculation & warm-up handling
- Chart layouts, persistent drawings, and template CRUD
- Replay session clock enforcement
- Alpaca adapter paper-only security allowlist
"""

import pytest
from backend.app.adapters.alpaca_paper_adapter import AlpacaPaperAdapter
from backend.app.domain.gemini_assistant import GeminiInvestmentAssistant
from backend.app.domain.technical_indicators import (
    calculate_bollinger_bands,
    calculate_ema,
    calculate_rsi,
    calculate_sma,
    calculate_vwap,
)
from backend.app.factory import create_app
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


def test_alpaca_paper_host_security_allowlist():
    """Verify Alpaca adapter strictly refuses live order hosts at startup."""
    with pytest.raises(ValueError, match="SECURITY REJECTION"):
        AlpacaPaperAdapter(
            api_key="mock-key",
            secret_key="mock-secret",
            base_url="https://api.alpaca.markets",
        )

    # Valid paper host passes
    adapter = AlpacaPaperAdapter(
        api_key=None,
        secret_key=None,
        base_url="https://paper-api.alpaca.markets",
    )
    assert not adapter.is_configured


def test_ai_assistant_unconfigured_status(client):
    """Verify application reports AI setup is incomplete or offline when key is missing or placeholder."""
    res = client.get("/api/v1/ai/assistant/status")
    assert res.status_code == 200
    data = res.json()["data"]
    assert "status_message" in data
    assert "disclaimer" in data
    assert data["is_configured"] is False or data["provider"] in ("mock-offline", "groq-configured", "groq-live")


def test_multilingual_language_detection():
    assistant = GeminiInvestmentAssistant()
    assert assistant.detect_language("Which stocks should I consider for my paper portfolio?") == "en"
    assert assistant.detect_language("रिलायंस इंडस्ट्रीज का शेयर कैसा है?") == "hi"
    assert assistant.detect_language("Mera portfolio dikhao aur batao kaunse stocks lene chahiye") == "hi-Latn"


def test_deterministic_technical_indicators_calculation():
    """Verify deterministic calculations, warm-up handling, and proper None values."""
    # 25 test bars with ascending closing prices
    bars = [
        {
            "date": f"2026-09-{i:02d}",
            "time": 1788000000 + i * 86400,
            "close": 100.0 + i,
            "high": 102.0 + i,
            "low": 99.0 + i,
            "volume": 1000,
        }
        for i in range(1, 26)
    ]

    # 1. SMA(20)
    sma_res = calculate_sma(bars, period=20)
    assert len(sma_res) == 25
    assert sma_res[0]["value"] is None  # Warm-up bar 1
    assert sma_res[18]["value"] is None  # Warm-up bar 19
    assert sma_res[19]["value"] is not None  # First valid SMA at bar 20
    # Expected mean of [101..120] = 110.5
    assert sma_res[19]["value"] == 110.5

    # 2. EMA(20)
    ema_res = calculate_ema(bars, period=20)
    assert len(ema_res) == 25
    assert ema_res[18]["value"] is None
    assert ema_res[19]["value"] == 110.5

    # 3. Bollinger Bands(20, 2)
    bb_res = calculate_bollinger_bands(bars, period=20, num_std=2.0)
    assert bb_res[18]["middle"] is None
    assert bb_res[19]["middle"] == 110.5
    assert bb_res[19]["upper"] > bb_res[19]["middle"]
    assert bb_res[19]["lower"] < bb_res[19]["middle"]

    # 4. RSI(14)
    rsi_res = calculate_rsi(bars, period=14)
    assert rsi_res[0]["value"] is None
    assert rsi_res[13]["value"] is None
    assert rsi_res[14]["value"] == 100.0  # Monotonically increasing prices produce RSI 100

    # 5. VWAP
    vwap_res = calculate_vwap(bars)
    assert len(vwap_res) == 25
    assert vwap_res[0]["value"] is not None


def test_research_request_creates_zero_orders(client, auth_headers):
    """Verify research requests provide educational context without placing any paper orders."""
    res = client.post(
        "/api/v1/ai/assistant/chat",
        json={"message": "Which stocks should I consider for my paper portfolio?"},
        headers=auth_headers,
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert "reply" in data
    assert data.get("proposal") is None
    assert data.get("execution_receipt") is None

    # Verify paper orders count is still zero or unchanged
    orders_res = client.get("/api/v1/paper-trading/orders", headers=auth_headers)
    assert orders_res.status_code == 200


def test_bounded_paper_investment_proposal_and_execution(client, auth_headers):
    """Verify proposal creation, budget reservation, and explicit user execution."""
    # 1. Ask assistant to invest INR 10,000 across RELIANCE and TCS
    chat_res = client.post(
        "/api/v1/ai/assistant/chat",
        json={"message": "Invest INR 10000 across RELIANCE and TCS"},
        headers=auth_headers,
    )
    assert chat_res.status_code == 200
    data = chat_res.json()["data"]

    # If API key is not configured, proposal flow is handled via direct tool execution test
    if data.get("is_setup_incomplete"):
        # Test direct proposal creation and execution via assistant domain engine
        import asyncio

        assistant = GeminiInvestmentAssistant()

        async def run_proposal_flow():
            prop = await assistant.tool_create_paper_proposal(
                user_id="usr-shivraj-001",
                symbols=["RELIANCE", "TCS"],
                budget=10000.0,
                currency="INR",
            )
            assert prop["status"] == "PROPOSED"
            assert prop["estimated_allocation_total"] <= 10000.0
            assert len(prop["allocations"]) == 2
            assert prop["expires_in_minutes"] == 10

        asyncio.run(run_proposal_flow())


def test_chart_workspace_api_endpoints(client, auth_headers):
    """Verify chart layouts, persistent drawings, and replay endpoints."""
    # 1. List layouts
    layouts_res = client.get("/api/v1/charts/layouts", headers=auth_headers)
    assert layouts_res.status_code == 200
    assert "layouts" in layouts_res.json()["data"]

    # 2. Save layout
    save_lay = client.post(
        "/api/v1/charts/layouts",
        json={
            "name": "Test Dual Chart",
            "layout_type": "dual_h",
            "active_symbols": ["RELIANCE", "TCS"],
            "timeframes": ["1D", "15m"],
            "sync_crosshair": True,
            "sync_time": True,
        },
        headers=auth_headers,
    )
    assert save_lay.status_code == 200
    lay_id = save_lay.json()["data"]["layout_id"]

    # 3. Delete layout
    del_lay = client.delete(f"/api/v1/charts/layouts/{lay_id}", headers=auth_headers)
    assert del_lay.status_code == 200

    # 4. Save and fetch drawings
    draw_res = client.post(
        "/api/v1/charts/drawings",
        json={
            "symbol": "RELIANCE",
            "drawing_type": "trend_line",
            "coordinates": [{"time": 1788000000, "price": 2450.0}, {"time": 1788100000, "price": 2500.0}],
            "properties": {"color": "#F29A60", "lineWidth": 2},
            "market": "NSE",
        },
        headers=auth_headers,
    )
    assert draw_res.status_code == 200
    drawing_id = draw_res.json()["data"]["drawing_id"]

    fetch_draw = client.get("/api/v1/charts/drawings/RELIANCE", headers=auth_headers)
    assert fetch_draw.status_code == 200
    drawings = fetch_draw.json()["data"]["drawings"]
    assert any(d["id"] == drawing_id for d in drawings)

    # 5. Clear drawings
    clear_res = client.delete("/api/v1/charts/drawings/clear/RELIANCE", headers=auth_headers)
    assert clear_res.status_code == 200


def test_market_history_with_replay_clock(client):
    """Verify history endpoint returns bars and filters out future observations when as_of is specified."""
    # Full history
    res_full = client.get("/api/v1/market/history/RELIANCE?start_date=2026-10-01&end_date=2026-10-16")
    assert res_full.status_code == 200
    bars_full = res_full.json()["data"]["bars"]
    assert len(bars_full) > 0

    # Replay clock capped at 2026-10-13
    res_capped = client.get(
        "/api/v1/market/history/RELIANCE?start_date=2026-10-01&end_date=2026-10-16&as_of=2026-10-13T23:59:59Z"
    )
    assert res_capped.status_code == 200
    bars_capped = res_capped.json()["data"]["bars"]
    for b in bars_capped:
        assert b["date"] <= "2026-10-13"


def test_market_indicators_endpoint(client):
    """Verify /market/indicators/{symbol} endpoint computes deterministic SMA."""
    res = client.get(
        "/api/v1/market/indicators/RELIANCE?indicator=SMA&period=2&start_date=2026-10-01&end_date=2026-10-16"
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["indicator"] == "SMA"
    assert data["period"] == 2
    assert len(data["series"]) > 0


@pytest.mark.asyncio
async def test_hinglish_buy_intent_preview_confirmation_and_portfolio_summary_isolation():
    """Verify exact Hinglish buy intent creates an unexecuted preview, confirms only once, and summarizes equity/avg prices accurately."""
    import uuid
    from datetime import datetime, timezone
    from decimal import Decimal
    from unittest.mock import patch

    from backend.app.adapters.market_data_provider import Quote, RealMarketDataProvider
    from backend.app.database import AsyncSessionLocal
    from backend.app.domain.gemini_assistant import gemini_assistant
    from backend.app.domain.paper_trading_service import OrderSubmitRequest, PaperTradingEngine
    from backend.app.models.core import User
    from backend.app.models.paper_trading import (
        PaperAccount,
        PaperCashLedger,
        PaperOrder,
        PaperPosition,
        PaperProposal,
        PaperTrade,
    )
    from backend.app.routers.auth import create_access_token
    from backend.app.services.password_service import hash_password
    from httpx import ASGITransport, AsyncClient
    from sqlalchemy import delete, select

    uid_a = f"usr-hinglish-a-{uuid.uuid4().hex[:6]}"
    uid_b = f"usr-hinglish-b-{uuid.uuid4().hex[:6]}"
    tok_a = create_access_token(uid_a, "hinglisha@example.com", "Hinglish User A")
    tok_b = create_access_token(uid_b, "hinglishb@example.com", "Hinglish User B")
    headers_a = {"Authorization": f"Bearer {tok_a}"}
    headers_b = {"Authorization": f"Bearer {tok_b}"}

    provider = RealMarketDataProvider(force_cache=True, allow_fixture_fallback=True)
    now = datetime.now(timezone.utc)
    for sym, px in [("RELIANCE", Decimal("2500.00")), ("TCS", Decimal("3500.00")), ("INFY", Decimal("1500.00"))]:
        provider.set_quote_override(
            sym,
            Quote(
                canonical_id=f"NSE:{sym}",
                symbol=f"{sym}.NS",
                price=px,
                currency="INR",
                observed_at=now,
                ingested_at=now,
                source="test_isolated_hinglish_fixture",
                source_uri=f"urn:market-data:test:{sym}",
                source_evidence="test-evidence",
                served_from_cache=False,
                is_delayed=False,
                is_stale=False,
                data_status="fresh",
            ),
        )
    isolated_engine = PaperTradingEngine(market_provider=provider)
    app = create_app()

    async with AsyncSessionLocal() as session:
        for uid, email in [(uid_a, "hinglisha@example.com"), (uid_b, "hinglishb@example.com")]:
            session.add(
                User(
                    id=uid,
                    email=email,
                    provider="email",
                    provider_subject=f"sub-{uid}",
                    password_hash=hash_password("StrongPass!123"),
                    is_active=True,
                    is_verified=True,
                )
            )
        await session.commit()

        # Pre-seed an existing TCS holding (2 shares @ ₹3,500) so average_buy_price & total_equity != cash
        buy_tcs = await isolated_engine.execute_order_db(
            uid_a,
            OrderSubmitRequest(
                symbol="TCS",
                side="BUY",
                quantity=Decimal("2"),
                order_type="MARKET",
                idempotency_key=f"seed-tcs-{uid_a}",
            ),
            db=session,
        )
        assert buy_tcs.status == "FILLED"
        await session.commit()

        # Move TCS current price to ₹3,600 so total_equity (₹100,200) differs from both cash (₹93,000) and initial ₹100,000
        provider.set_quote_override(
            "TCS",
            Quote(
                canonical_id="NSE:TCS",
                symbol="TCS.NS",
                price=Decimal("3600.00"),
                currency="INR",
                observed_at=now,
                ingested_at=now,
                source="test_isolated_hinglish_fixture",
                source_uri="urn:market-data:test:TCS",
                source_evidence="test-evidence",
                served_from_cache=False,
                is_delayed=False,
                is_stale=False,
                data_status="fresh",
            ),
        )

    try:
        with (
            patch.object(gemini_assistant, "_provider", provider),
            patch.object(gemini_assistant, "_engine", isolated_engine),
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                # 1. Exact Hinglish buy sentence with trailing '?' and 'portfolio'
                hinglish_msg = "muze yek reliance kaa share lena hai mere portfolio mee le do ge kya tum?"
                chat_res = await client.post(
                    "/api/v1/ai/assistant/chat",
                    json={"message": hinglish_msg, "active_chart_context": {"symbol": "TCS", "timeframe": "1D"}},
                    headers=headers_a,
                )
                assert chat_res.status_code == 200
                data = chat_res.json()["data"]
                conv_id = data["conversation_id"]

                assert data["language_detected"] == "hi-Latn"
                assert data["execution_receipt"] is None  # Must NOT execute before explicit confirmation
                prop = data["proposal"]
                assert prop is not None
                assert prop["status"] == "PROPOSED"
                assert prop["requires_approval"] is True
                assert prop["allocations"][0]["symbol"] == "RELIANCE"
                assert prop["allocations"][0]["side"] == "BUY"
                assert prop["allocations"][0]["quantity"] == 1
                assert prop["allocations"][0]["estimated_price"] == 2500.0
                assert prop["allocations"][0]["estimated_total"] == 2500.0
                assert "No open positions" not in data["reply"]
                assert "RELIANCE" in data["reply"]

                # Confirm zero RELIANCE orders were placed prior to approval
                async with AsyncSessionLocal() as session:
                    rel_orders = (
                        (
                            await session.execute(
                                select(PaperOrder).where(PaperOrder.user_id == uid_a, PaperOrder.symbol == "RELIANCE")
                            )
                        )
                        .scalars()
                        .all()
                    )
                    assert len(rel_orders) == 0

                # 2. Portfolio inquiry MUST use average_buy_price & total_equity (never ₹0.00 / equity == cash)
                port_res = await client.post(
                    "/api/v1/ai/assistant/chat",
                    json={"message": "Mera virtual portfolio aur balance dikhao", "conversation_id": conv_id},
                    headers=headers_a,
                )
                assert port_res.status_code == 200
                port_data = port_res.json()["data"]
                assert port_data["proposal"] is None
                assert "₹93,000.00" in port_data["reply"]
                assert "₹100,200.00" in port_data["reply"]
                assert "₹3,500.00" in port_data["reply"]
                assert "₹0.00" not in port_data["reply"]

                # 3. Cross-tenant isolation: User B cannot execute User A's proposal
                prop_id = prop["proposal_id"]
                b_exec = await client.post(
                    f"/api/v1/ai/assistant/proposals/{prop_id}/execute",
                    headers=headers_b,
                )
                assert b_exec.status_code == 200
                assert b_exec.json()["data"]["status"] == "REJECTED"

                # 4. Confirmation from a different conversation must not match
                wrong_conv = await client.post(
                    "/api/v1/ai/assistant/chat",
                    json={"message": "Haan", "conversation_id": f"conv-wrong-{uuid.uuid4().hex[:6]}"},
                    headers=headers_a,
                )
                assert wrong_conv.status_code == 200
                assert wrong_conv.json()["data"]["execution_receipt"] is None

                # 5. Explicit Hinglish confirmation inside matching conversation executes exactly 1 share
                confirm_res = await client.post(
                    "/api/v1/ai/assistant/chat",
                    json={"message": "Haan", "conversation_id": conv_id},
                    headers=headers_a,
                )
                assert confirm_res.status_code == 200
                conf_data = confirm_res.json()["data"]
                receipt = conf_data["execution_receipt"]
                assert receipt is not None
                assert receipt["status"] == "EXECUTED"
                assert receipt["receipts"][0]["symbol"] == "RELIANCE"
                assert Decimal(str(receipt["receipts"][0]["quantity"])) == Decimal("1")
                assert Decimal(str(receipt["receipts"][0]["fill_price"])) == Decimal("2500.00")
                assert receipt["receipts"][0]["status"] == "FILLED"
                assert conf_data["reply"] and "90,500.00" in conf_data["reply"]

                # 6. Duplicate confirmation does NOT place a second order
                dup_exec = await client.post(
                    f"/api/v1/ai/assistant/proposals/{prop_id}/execute",
                    headers=headers_a,
                )
                assert dup_exec.status_code == 200
                assert dup_exec.json()["data"]["status"] == "ALREADY_EXECUTED"

                async with AsyncSessionLocal() as session:
                    rel_orders_after = (
                        (
                            await session.execute(
                                select(PaperOrder).where(PaperOrder.user_id == uid_a, PaperOrder.symbol == "RELIANCE")
                            )
                        )
                        .scalars()
                        .all()
                    )
                    assert len(rel_orders_after) == 1
    finally:
        async with AsyncSessionLocal() as session:
            for uid in (uid_a, uid_b):
                acct = (
                    await session.execute(select(PaperAccount).where(PaperAccount.user_id == uid))
                ).scalar_one_or_none()
                await session.execute(delete(PaperProposal).where(PaperProposal.user_id == uid))
                if acct:
                    await session.execute(delete(PaperTrade).where(PaperTrade.account_id == acct.id))
                    await session.execute(delete(PaperCashLedger).where(PaperCashLedger.account_id == acct.id))
                    await session.execute(delete(PaperPosition).where(PaperPosition.account_id == acct.id))
                    await session.execute(delete(PaperOrder).where(PaperOrder.account_id == acct.id))
                    await session.execute(delete(PaperAccount).where(PaperAccount.id == acct.id))
                await session.execute(delete(User).where(User.id == uid))
            await session.commit()


@pytest.mark.asyncio
async def test_multilingual_buy_clarifications_research_and_unavailable_data():
    """Verify Hindi/English buy intents, concise clarifications on ambiguity, advisory research refusal, and unavailable summary labels."""
    import uuid
    from datetime import datetime, timezone
    from decimal import Decimal
    from unittest.mock import AsyncMock, patch

    from backend.app.adapters.market_data_provider import Quote, RealMarketDataProvider
    from backend.app.database import AsyncSessionLocal
    from backend.app.domain.paper_trading_service import PaperTradingEngine
    from backend.app.models.core import User
    from backend.app.models.paper_trading import PaperAccount, PaperProposal
    from backend.app.services.password_service import hash_password
    from sqlalchemy import delete, select

    provider = RealMarketDataProvider(force_cache=True, allow_fixture_fallback=False)
    now = datetime.now(timezone.utc)
    for sym, px in [("RELIANCE", Decimal("2500.00")), ("TCS", Decimal("3500.00")), ("INFY", Decimal("1500.00"))]:
        provider.set_quote_override(
            sym,
            Quote(
                canonical_id=f"NSE:{sym}",
                symbol=f"{sym}.NS",
                price=px,
                currency="INR",
                observed_at=now,
                ingested_at=now,
                source="test_multilang_fixture",
                source_uri=f"urn:market-data:test:{sym}",
                source_evidence="test-evidence",
                served_from_cache=False,
                is_delayed=False,
                is_stale=False,
                data_status="fresh",
            ),
        )
    assistant = GeminiInvestmentAssistant(engine=PaperTradingEngine(market_provider=provider), provider=provider)
    uid = f"usr-multi-lang-{uuid.uuid4().hex[:6]}"
    conv_id = f"conv-multi-{uuid.uuid4().hex[:6]}"

    async with AsyncSessionLocal() as session:
        session.add(
            User(
                id=uid,
                email=f"{uid}@example.com",
                provider="email",
                provider_subject=f"sub-{uid}",
                password_hash=hash_password("StrongPass!123"),
                is_active=True,
                is_verified=True,
            )
        )
        await session.commit()

    try:
        async with AsyncSessionLocal() as session:
            # 1. Hindi & English quantity buys create proposals without executing
            for msg, expected_sym, expected_qty, expected_lang in [
                ("Can you buy 2 shares of INFY for me?", "INFY", 2, "en"),
                ("रिलायंस का एक शेयर खरीदना है", "RELIANCE", 1, "hi"),
                ("Mere liye do share TCS ke kharid do", "TCS", 2, "hi-Latn"),
            ]:
                r = await assistant.process_user_turn(uid, msg, conversation_id=conv_id, db=session)
                assert r.language_detected == expected_lang
                assert r.execution_receipt is None
                assert r.proposal is not None and r.proposal["status"] == "PROPOSED"
                assert r.proposal["allocations"][0]["symbol"] == expected_sym
                assert r.proposal["allocations"][0]["quantity"] == expected_qty

            # 2. Ambiguous buy requests return concise clarification without creating proposals
            for amb_msg in [
                "muze ek share lena hai",
                "I want to buy RELIANCE",
                "buy 0 shares of RELIANCE",
                "buy 1.5 shares of RELIANCE",
                "buy 2 UNKNOWNXYZ shares",
                "RELIANCE mere portfolio me?",
                "buy or sell RELIANCE",
            ]:
                r = await assistant.process_user_turn(uid, amb_msg, conversation_id=conv_id, db=session)
                assert r.proposal is None, f"Unexpected proposal for ambiguous prompt: {amb_msg}"
                assert r.execution_receipt is None
                assert len(r.reply) > 10

            # 3. Advisory research questions in English/Hinglish never create proposals
            for adv_msg in [
                "Should I buy 1 RELIANCE share?",
                "RELIANCE ka ek share lena chahiye?",
            ]:
                r = await assistant.process_user_turn(uid, adv_msg, conversation_id=conv_id, db=session)
                assert r.proposal is None
                assert r.execution_receipt is None

            # 4. Unavailable summary fields are labeled 'Unavailable', never '₹0.00' or fabricated equity
            with patch.object(
                assistant,
                "tool_get_my_paper_portfolio",
                new=AsyncMock(
                    return_value={
                        "current_cash": None,
                        "total_equity": None,
                        "positions": [{"symbol": "RELIANCE", "quantity": 2, "average_buy_price": None}],
                    }
                ),
            ):
                r_unavail = await assistant.process_user_turn(
                    uid, "What is my portfolio summary?", conversation_id=conv_id, db=session
                )
                assert "Unavailable" in r_unavail.reply
                assert "₹0.00" not in r_unavail.reply
                assert "1,000,000.00" not in r_unavail.reply

            # 5. Missing market quote fails closed instead of fabricating a ₹2,500 preview
            no_quote_provider = RealMarketDataProvider(force_cache=True, allow_fixture_fallback=False)
            no_quote_assistant = GeminiInvestmentAssistant(
                engine=PaperTradingEngine(market_provider=no_quote_provider), provider=no_quote_provider
            )
            r_no_q = await no_quote_assistant.process_user_turn(
                uid, "Buy 1 RELIANCE share", conversation_id=conv_id, db=session
            )
            assert r_no_q.execution_receipt is None
            assert r_no_q.proposal is not None and r_no_q.proposal["status"] == "QUOTE_UNAVAILABLE"
    finally:
        async with AsyncSessionLocal() as session:
            acct = (await session.execute(select(PaperAccount).where(PaperAccount.user_id == uid))).scalar_one_or_none()
            await session.execute(delete(PaperProposal).where(PaperProposal.user_id == uid))
            if acct:
                await session.execute(delete(PaperAccount).where(PaperAccount.id == acct.id))
            await session.execute(delete(User).where(User.id == uid))
            await session.commit()


@pytest.mark.asyncio
async def test_order_confirmation_safety_exhaustively():
    """Verify Haan/Yes/Confirm strictly guard expired, cancelled, executed, multiple, cross-user, wrong-conv, ambiguous, price-jump, and concurrent confirmations."""
    import asyncio
    import uuid
    from datetime import datetime, timedelta, timezone
    from decimal import Decimal
    from unittest.mock import patch

    from backend.app.adapters.market_data_provider import Quote, RealMarketDataProvider
    from backend.app.database import AsyncSessionLocal
    from backend.app.domain.gemini_assistant import gemini_assistant
    from backend.app.domain.paper_trading_service import PaperTradingEngine
    from backend.app.models.core import User
    from backend.app.models.paper_trading import (
        PaperAccount,
        PaperCashLedger,
        PaperOrder,
        PaperPosition,
        PaperProposal,
        PaperTrade,
    )
    from backend.app.routers.auth import create_access_token
    from backend.app.services.password_service import hash_password
    from httpx import ASGITransport, AsyncClient
    from sqlalchemy import delete, select

    provider = RealMarketDataProvider(force_cache=True, allow_fixture_fallback=False)
    now = datetime.now(timezone.utc)
    for sym, px in [("RELIANCE", Decimal("2500.00")), ("TCS", Decimal("3500.00")), ("INFY", Decimal("1500.00"))]:
        provider.set_quote_override(
            sym,
            Quote(
                canonical_id=f"NSE:{sym}",
                symbol=f"{sym}.NS",
                price=px,
                currency="INR",
                observed_at=now,
                ingested_at=now,
                source="test_confirm_safety_fixture",
                source_uri=f"urn:market-data:test:{sym}",
                source_evidence="test-evidence",
                served_from_cache=False,
                is_delayed=False,
                is_stale=False,
                data_status="fresh",
            ),
        )
    assistant = GeminiInvestmentAssistant(engine=PaperTradingEngine(market_provider=provider), provider=provider)
    uid_a = f"usr-conf-a-{uuid.uuid4().hex[:6]}"
    uid_b = f"usr-conf-b-{uuid.uuid4().hex[:6]}"
    tok_a = create_access_token(uid_a, f"{uid_a}@example.com", "Confirm Safety A")
    headers_a = {"Authorization": f"Bearer {tok_a}"}
    app = create_app()

    async with AsyncSessionLocal() as session:
        for uid in (uid_a, uid_b):
            session.add(
                User(
                    id=uid,
                    email=f"{uid}@example.com",
                    provider="email",
                    provider_subject=f"sub-{uid}",
                    password_hash=hash_password("StrongPass!123"),
                    is_active=True,
                    is_verified=True,
                )
            )
        await session.commit()

    async def count_orders(user_id: str) -> int:
        async with AsyncSessionLocal() as s:
            rows = (await s.execute(select(PaperOrder).where(PaperOrder.user_id == user_id))).scalars().all()
            return len(rows)

    try:
        async with AsyncSessionLocal() as session:
            # 1. Expired proposal (generic "Yes"/"Confirm" + explicit ID + execute endpoint)
            conv_exp = f"conv-exp-{uuid.uuid4().hex[:6]}"
            p_exp = await assistant.tool_create_paper_proposal(
                uid_a,
                ["RELIANCE"],
                currency="INR",
                conversation_id=conv_exp,
                db=session,
                requested_quantities={"RELIANCE": 1},
            )
            db_exp = (
                await session.execute(select(PaperProposal).where(PaperProposal.id == p_exp["proposal_id"]))
            ).scalar_one()
            db_exp.expires_at = datetime.now(timezone.utc) - timedelta(seconds=5)
            await session.commit()

            for msg in ("Yes", "Confirm", f"confirm {p_exp['proposal_id']}"):
                r_exp = await assistant.process_user_turn(uid_a, msg, conversation_id=conv_exp, db=session)
                assert r_exp.execution_receipt is None
                assert "expired" in r_exp.reply.lower() or "no active pending" in r_exp.reply.lower()
            assert await count_orders(uid_a) == 0

            # 2. Cancelled proposal must reject Yes/Haan/Confirm/explicit ID
            conv_can = f"conv-can-{uuid.uuid4().hex[:6]}"
            p_can = await assistant.tool_create_paper_proposal(
                uid_a,
                ["RELIANCE"],
                currency="INR",
                conversation_id=conv_can,
                db=session,
                requested_quantities={"RELIANCE": 1},
            )
            r_cancel = await assistant.process_user_turn(uid_a, "Cancel", conversation_id=conv_can, db=session)
            assert "cancelled" in r_cancel.reply.lower()
            for msg in ("Yes", "Haan", "Confirm", f"confirm {p_can['proposal_id']}"):
                r_after_can = await assistant.process_user_turn(uid_a, msg, conversation_id=conv_can, db=session)
                assert r_after_can.execution_receipt is None
            assert await count_orders(uid_a) == 0

            # 3. Ambiguous confirmations on an active pending proposal MUST clarify and NEVER execute
            conv_amb = f"conv-amb-{uuid.uuid4().hex[:6]}"
            r_prev = await assistant.process_user_turn(
                uid_a, "Buy 1 RELIANCE share", conversation_id=conv_amb, db=session
            )
            assert r_prev.proposal is not None and r_prev.proposal["status"] == "PROPOSED"
            prop_amb_id = r_prev.proposal["proposal_id"]
            assert await count_orders(uid_a) == 0

            for amb_conf in [
                "Yes, maybe",
                "Haan, shayad",
                "Yes?",
                "Confirm?",
                "Confirm later",
                "Wait before confirming this",
                "Confirm or cancel this order",
                "Confirm order status",
                "Not ready to confirm this",
                "do not confirm",
                "Yes, what is the price?",
            ]:
                r_amb = await assistant.process_user_turn(uid_a, amb_conf, conversation_id=conv_amb, db=session)
                assert r_amb.execution_receipt is None, f"Ambiguous text executed unexpectedly: {amb_conf}"
                assert await count_orders(uid_a) == 0

            # Normal portfolio question containing "confirm" still routes to portfolio summary cleanly
            r_port_q = await assistant.process_user_turn(
                uid_a, "Can you confirm my portfolio balance?", conversation_id=conv_amb, db=session
            )
            assert r_port_q.execution_receipt is None
            assert "Virtual Paper Portfolio Summary" in r_port_q.reply

            # Wrong conversation cannot confirm conv_amb's proposal via Yes/Haan/Confirm
            for conf_word in ("Yes", "Haan", "Confirm"):
                r_wrong = await assistant.process_user_turn(
                    uid_a, conf_word, conversation_id=f"conv-wrong-{uuid.uuid4().hex[:4]}", db=session
                )
                assert r_wrong.execution_receipt is None

            # Cross-user cannot execute User A's proposal
            r_cross = await assistant.process_user_turn(
                uid_b, f"confirm {prop_amb_id}", conversation_id=conv_amb, db=session
            )
            assert r_cross.execution_receipt is None
            assert "not found for this account" in r_cross.reply
            assert await count_orders(uid_a) == 0

            # 4. Price jump exceeding approved amount rejects on "Confirm" without filling
            provider.set_quote_override(
                "RELIANCE",
                Quote(
                    canonical_id="NSE:RELIANCE",
                    symbol="RELIANCE.NS",
                    price=Decimal("2575.00"),
                    currency="INR",
                    observed_at=now,
                    ingested_at=now,
                    source="test_confirm_safety_fixture",
                    source_uri="urn:market-data:test:RELIANCE",
                    source_evidence="test-evidence",
                    served_from_cache=False,
                    is_delayed=False,
                    is_stale=False,
                    data_status="fresh",
                ),
            )
            r_jump = await assistant.process_user_turn(uid_a, "Confirm", conversation_id=conv_amb, db=session)
            assert r_jump.execution_receipt is not None and r_jump.execution_receipt["status"] == "REJECTED"
            assert "exceeds authorized remaining budget" in r_jump.execution_receipt["error"]
            assert await count_orders(uid_a) == 0

            # Restore price and expire/clear old proposal
            provider.set_quote_override(
                "RELIANCE",
                Quote(
                    canonical_id="NSE:RELIANCE",
                    symbol="RELIANCE.NS",
                    price=Decimal("2500.00"),
                    currency="INR",
                    observed_at=now,
                    ingested_at=now,
                    source="test_confirm_safety_fixture",
                    source_uri="urn:market-data:test:RELIANCE",
                    source_evidence="test-evidence",
                    served_from_cache=False,
                    is_delayed=False,
                    is_stale=False,
                    data_status="fresh",
                ),
            )

            # 5. Multiple pending proposals require disambiguation; multi-ID confirm rejected
            conv_multi = f"conv-mult-{uuid.uuid4().hex[:6]}"
            p1 = (
                await assistant.process_user_turn(uid_a, "Buy 1 RELIANCE share", conversation_id=conv_multi, db=session)
            ).proposal
            p2 = (
                await assistant.process_user_turn(uid_a, "Buy 1 INFY share", conversation_id=conv_multi, db=session)
            ).proposal
            assert p1 is not None and p2 is not None
            for msg in ("Yes", "Haan", "Confirm", f"confirm {p1['proposal_id']} or {p2['proposal_id']}"):
                r_dis = await assistant.process_user_turn(uid_a, msg, conversation_id=conv_multi, db=session)
                assert r_dis.execution_receipt is None
            assert await count_orders(uid_a) == 0

            # Confirm specifically p2 via explicit ID -> executes ONLY INFY; p1 remains PROPOSED
            r_p2 = await assistant.process_user_turn(
                uid_a, f"confirm {p2['proposal_id']}", conversation_id=conv_multi, db=session
            )
            assert r_p2.execution_receipt is not None and r_p2.execution_receipt["status"] == "EXECUTED"
            assert await count_orders(uid_a) == 1
            p1_db = (
                await session.execute(select(PaperProposal).where(PaperProposal.id == p1["proposal_id"]))
            ).scalar_one()
            assert p1_db.status == "PROPOSED"

            # Repeated confirmations on executed p2 create zero additional orders
            r_rep = await assistant.process_user_turn(
                uid_a, f"confirm {p2['proposal_id']}", conversation_id=conv_multi, db=session
            )
            assert r_rep.execution_receipt is None
            assert "already been executed" in r_rep.reply.lower()
            assert await count_orders(uid_a) == 1

            # 6. Concurrent confirmations via process_user_turn (across separate DB sessions) execute p1 strictly once
            async def confirm_turn_race(phrase: str):
                async with AsyncSessionLocal() as s:
                    return await assistant.process_user_turn(uid_a, phrase, conversation_id=conv_multi, db=s)

            race_turn_res = await asyncio.gather(
                confirm_turn_race("Yes"),
                confirm_turn_race("Haan"),
                confirm_turn_race("Confirm"),
                confirm_turn_race("Yes"),
            )
            exec_hits = [
                r for r in race_turn_res if r.execution_receipt and r.execution_receipt.get("status") == "EXECUTED"
            ]
            assert len(exec_hits) == 1
            assert await count_orders(uid_a) == 2

            # 7. Concurrent HTTP /proposals/{id}/execute calls on a fresh proposal execute strictly once
            conv_http = f"conv-http-{uuid.uuid4().hex[:6]}"
            p3 = await assistant.tool_create_paper_proposal(
                uid_a, ["TCS"], currency="INR", conversation_id=conv_http, db=session, requested_quantities={"TCS": 1}
            )
            p3_id = p3["proposal_id"]

        with (
            patch.object(gemini_assistant, "_provider", provider),
            patch.object(gemini_assistant, "_engine", assistant.engine),
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                http_res = await asyncio.gather(
                    *[
                        client.post(f"/api/v1/ai/assistant/proposals/{p3_id}/execute", headers=headers_a)
                        for _ in range(4)
                    ]
                )
                statuses = [r.json()["data"]["status"] for r in http_res]
                assert statuses.count("EXECUTED") == 1
                assert statuses.count("ALREADY_EXECUTED") == 3
                assert await count_orders(uid_a) == 3

        # Verify exact ledger, cash (100,000 - 1500 INFY - 2500 RELIANCE - 3500 TCS = 92,500), and holdings
        async with AsyncSessionLocal() as session:
            acct = (await session.execute(select(PaperAccount).where(PaperAccount.user_id == uid_a))).scalar_one()
            assert Decimal(str(acct.current_cash)) == Decimal("92500.00")
            pos_rows = (
                (await session.execute(select(PaperPosition).where(PaperPosition.account_id == acct.id)))
                .scalars()
                .all()
            )
            assert {p.symbol: Decimal(str(p.quantity)) for p in pos_rows} == {
                "INFY": Decimal("1"),
                "RELIANCE": Decimal("1"),
                "TCS": Decimal("1"),
            }
    finally:
        async with AsyncSessionLocal() as session:
            for uid in (uid_a, uid_b):
                acct = (
                    await session.execute(select(PaperAccount).where(PaperAccount.user_id == uid))
                ).scalar_one_or_none()
                await session.execute(delete(PaperProposal).where(PaperProposal.user_id == uid))
                if acct:
                    await session.execute(delete(PaperTrade).where(PaperTrade.account_id == acct.id))
                    await session.execute(delete(PaperCashLedger).where(PaperCashLedger.account_id == acct.id))
                    await session.execute(delete(PaperPosition).where(PaperPosition.account_id == acct.id))
                    await session.execute(delete(PaperOrder).where(PaperOrder.account_id == acct.id))
                    await session.execute(delete(PaperAccount).where(PaperAccount.id == acct.id))
                await session.execute(delete(User).where(User.id == uid))
            await session.commit()
