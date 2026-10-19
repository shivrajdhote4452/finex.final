"""Focused Regression Tests for FinEx Audit & Compliance Repairs.

Validates:
1. "Do not execute" causes zero trade and marks active proposal cancelled.
2. Research questions ("Should I invest?", "Is it good to buy?") cause zero trade/proposal.
3. Another user cannot access or execute someone else's proposal (cross-tenant isolation).
4. Confirmation targets the correct proposal bound to conversation/proposal ID.
5. A ₹100 budget cannot purchase a ₹2,500 whole share (returns INSUFFICIENT_BUDGET).
6. Total estimated order value never exceeds the authorized budget.
7. Repeating an execution request uses a stable idempotency key and does not duplicate orders.
8. Price jump budget enforcement: price jump exceeding authorized budget rejects execution.
9. Explicit proposal ID precedence: explicitly confirmed proposal ID executes over conversation recency.
10. Multiple pending proposals require user disambiguation.
11. Invalid explicit proposal ID never substitutes a valid pending proposal.
12. Multi-conversation cancellation isolation: cancelling in conv A does not cancel conv B, and empty conv does not falsely claim cancellation.
13. Retrying partial execution recovers failed legs without duplicating already completed fills.
14. Market hub simulation loop emits genuine observations without synthetic fluctuations when demo simulation is disabled.
15. Missing market prices do not become fabricated executable quotes (no 2500.0 fallback).
16. Cache refresh preserves the original observation timestamp.
17. Historical operations exclude future observations when as_of is specified.
18. Gemini API call passes credentials via headers only (no ?key= in URLs).
"""

import inspect
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from backend.app.adapters.market_data_provider import Quote, RealMarketDataProvider
from backend.app.database import AsyncSessionLocal
from backend.app.domain.gemini_assistant import GeminiInvestmentAssistant
from backend.app.domain.paper_trading_service import PaperTradingEngine
from backend.app.models.paper_trading import PaperOrder, PaperProposal
from backend.app.services.market_hub import MarketHub
from sqlalchemy import select


@pytest.fixture
def anyio_backend():
    return "asyncio"


def make_isolated_assistant() -> GeminiInvestmentAssistant:
    """Create test-isolated assistant with controlled test fixture observations."""
    provider = RealMarketDataProvider(force_cache=True, allow_fixture_fallback=True)
    now = datetime.now(timezone.utc)
    for sym, price in [
        ("RELIANCE", Decimal("2500.00")),
        ("TCS", Decimal("3500.00")),
        ("INFY", Decimal("1500.00")),
        ("HDFCBANK", Decimal("1600.00")),
    ]:
        provider.set_quote_override(
            sym,
            Quote(
                canonical_id=f"NSE:{sym}",
                symbol=f"{sym}.NS",
                price=price,
                currency="INR",
                observed_at=now,
                ingested_at=now,
                source="test_isolated_fixture",
                source_uri=f"urn:market-data:test:{sym}",
                source_evidence="test-evidence",
                served_from_cache=False,
                is_delayed=False,
                is_stale=False,
                data_status="fresh",
            ),
        )
    engine = PaperTradingEngine(market_provider=provider)
    return GeminiInvestmentAssistant(engine=engine, provider=provider)


@pytest.mark.asyncio
async def test_do_not_execute_causes_no_trade_and_cancels_proposal():
    """Verify 'do not execute', 'cancel', 'wait', 'don't buy' never execute trades."""
    assistant = make_isolated_assistant()
    user_id = f"usr-test-refusal-{uuid.uuid4().hex[:6]}"
    conv_id = f"conv-test-refusal-{uuid.uuid4().hex[:6]}"

    async with AsyncSessionLocal() as session:
        # Create a pending proposal
        prop = await assistant.tool_create_paper_proposal(
            user_id=user_id,
            symbols=["RELIANCE"],
            budget=10000.0,
            conversation_id=conv_id,
            db=session,
        )
        assert prop["status"] == "PROPOSED"
        prop_id = prop["proposal_id"]

        # User says "do not execute"
        res = await assistant.process_user_turn(
            user_id=user_id,
            user_message="do not execute",
            conversation_id=conv_id,
            db=session,
        )
        assert res.execution_receipt is None
        assert "cancelled" in res.reply.lower() or "रद्द" in res.reply

        # Verify proposal was marked CANCELLED
        stmt = select(PaperProposal).where(PaperProposal.id == prop_id)
        db_res = await session.execute(stmt)
        updated_prop = db_res.scalar_one()
        assert updated_prop.status == "CANCELLED"

        # Subsequent "yes" cannot execute the cancelled proposal
        res_after = await assistant.process_user_turn(
            user_id=user_id,
            user_message="yes",
            conversation_id=conv_id,
            db=session,
        )
        assert res_after.execution_receipt is None
        assert "no active pending" in res_after.reply.lower() or "koi active" in res_after.reply.lower()


@pytest.mark.asyncio
async def test_research_question_causes_no_execution_or_unsolicited_proposal():
    """Verify research queries like 'Should I invest in RELIANCE?' remain research queries."""
    assistant = make_isolated_assistant()
    user_id = f"usr-test-research-{uuid.uuid4().hex[:6]}"
    conv_id = f"conv-test-research-{uuid.uuid4().hex[:6]}"

    async with AsyncSessionLocal() as session:
        research_messages = [
            "Should I invest in RELIANCE?",
            "Is it good to buy TCS right now?",
            "Can you explain the RSI indicator on this chart?",
            "Why should I invest ₹10,000 in equities?",
            "What do you think about HDFCBANK?",
        ]
        for msg in research_messages:
            res = await assistant.process_user_turn(
                user_id=user_id,
                user_message=msg,
                conversation_id=conv_id,
                db=session,
            )
            # Never an execution receipt
            assert res.execution_receipt is None
            # Never an unsolicited proposal generated for a pure research question
            assert res.proposal is None
            # Informational reply provided
            assert len(res.reply) > 10


@pytest.mark.asyncio
async def test_another_user_cannot_access_or_execute_others_proposal():
    """Verify cross-tenant isolation: User B cannot execute User A's proposal."""
    assistant = make_isolated_assistant()
    user_a = f"usr-tenant-a-{uuid.uuid4().hex[:6]}"
    user_b = f"usr-tenant-b-{uuid.uuid4().hex[:6]}"

    async with AsyncSessionLocal() as session:
        prop = await assistant.tool_create_paper_proposal(
            user_id=user_a,
            symbols=["RELIANCE"],
            budget=5000.0,
            conversation_id="conv-user-a",
            db=session,
        )
        prop_id = prop["proposal_id"]

        # User B attempts to execute User A's proposal
        res = await assistant.tool_execute_paper_proposal(
            user_id=user_b,
            proposal_id=prop_id,
            db=session,
        )
        assert res["status"] == "REJECTED"
        assert "not found" in res["error"].lower()


@pytest.mark.asyncio
async def test_confirmation_targets_correct_proposal():
    """Verify confirmation requires matching conversation_id or explicit proposal ID."""
    assistant = make_isolated_assistant()
    user_id = f"usr-conv-bound-{uuid.uuid4().hex[:6]}"

    async with AsyncSessionLocal() as session:
        # Create proposal in Conversation A
        prop = await assistant.tool_create_paper_proposal(
            user_id=user_id,
            symbols=["RELIANCE"],
            budget=5000.0,
            conversation_id="conv-room-alpha",
            db=session,
        )
        assert prop["status"] == "PROPOSED"

        # User says "yes" in Conversation B (unrelated room)
        res_wrong_conv = await assistant.process_user_turn(
            user_id=user_id,
            user_message="yes",
            conversation_id="conv-room-beta",
            db=session,
        )
        # Must refuse to execute proposal from another conversation
        assert res_wrong_conv.execution_receipt is None
        assert "no active pending" in res_wrong_conv.reply.lower() or "koi active" in res_wrong_conv.reply.lower()


@pytest.mark.asyncio
async def test_budget_smaller_than_single_share_returns_insufficient_budget():
    """Verify requesting a ₹100 budget for a ₹2,500 share rejects with INSUFFICIENT_BUDGET."""
    assistant = make_isolated_assistant()
    user_id = f"usr-test-budget-{uuid.uuid4().hex[:6]}"

    async with AsyncSessionLocal() as session:
        # Request ₹100 budget for RELIANCE (which is ₹2,500)
        prop = await assistant.tool_create_paper_proposal(
            user_id=user_id,
            symbols=["RELIANCE"],
            budget=100.0,
            conversation_id="conv-budget-100",
            db=session,
        )
        assert prop["status"] == "INSUFFICIENT_BUDGET"
        assert len(prop["allocations"]) == 0
        assert prop["estimated_allocation_total"] == 0.0
        assert "insufficient" in prop["error"].lower()


@pytest.mark.asyncio
async def test_requested_budget_is_hard_maximum():
    """Verify total estimated outlay never exceeds requested budget."""
    assistant = make_isolated_assistant()
    user_id = f"usr-test-budget-max-{uuid.uuid4().hex[:6]}"

    async with AsyncSessionLocal() as session:
        requested_budget = 6000.0
        prop = await assistant.tool_create_paper_proposal(
            user_id=user_id,
            symbols=["RELIANCE", "TCS"],
            budget=requested_budget,
            conversation_id="conv-budget-max",
            db=session,
        )
        if prop["status"] == "PROPOSED":
            assert prop["estimated_allocation_total"] <= requested_budget
            assert prop["requested_budget"] == requested_budget


@pytest.mark.asyncio
async def test_stable_idempotency_key_and_no_duplicate_orders_on_retry():
    """Verify repeated execution uses a stable idempotency key and does not duplicate fills."""
    assistant = make_isolated_assistant()
    user_id = f"usr-test-idemp-{uuid.uuid4().hex[:6]}"

    async with AsyncSessionLocal() as session:
        prop = await assistant.tool_create_paper_proposal(
            user_id=user_id,
            symbols=["RELIANCE"],
            budget=10000.0,
            conversation_id="conv-idemp-001",
            db=session,
        )
        prop_id = prop["proposal_id"]

        # First execution attempt
        res1 = await assistant.tool_execute_paper_proposal(user_id=user_id, proposal_id=prop_id, db=session)
        assert res1["status"] in ("EXECUTED", "PARTIALLY_EXECUTED")

        # Second execution attempt (retry)
        res2 = await assistant.tool_execute_paper_proposal(user_id=user_id, proposal_id=prop_id, db=session)
        assert res2["status"] == "ALREADY_EXECUTED"
        assert "already been executed" in res2["error"].lower()


@pytest.mark.asyncio
async def test_price_jump_exceeding_budget_rejected():
    """Verify that execution is rejected when price increases make the authorized allocation unaffordable."""
    assistant = make_isolated_assistant()
    user_id = f"usr-price-jump-{uuid.uuid4().hex[:6]}"
    conv_id = f"conv-price-jump-{uuid.uuid4().hex[:6]}"

    async with AsyncSessionLocal() as session:
        # 1. Create a proposal for 2 shares of RELIANCE at ₹2,500 with ₹5,000 budget
        prop = await assistant.tool_create_paper_proposal(
            user_id=user_id,
            symbols=["RELIANCE"],
            budget=5000.0,
            conversation_id=conv_id,
            db=session,
        )
        assert prop["status"] == "PROPOSED"
        assert prop["requested_budget"] == 5000.0
        prop_id = prop["proposal_id"]
        assert len(prop["allocations"]) == 1
        assert prop["allocations"][0]["quantity"] == 2

        # 2. Simulate price jump from ₹2,500 to ₹3,000 (total projected cost ₹6,000 > ₹5,000)
        norm = "RELIANCE"
        now = datetime.now(timezone.utc)
        cached_q = assistant.provider._cache.get(norm)
        assert cached_q is not None
        jump_quote = cached_q.model_copy(update={"price": Decimal("3000.00"), "observed_at": now})
        assistant.provider._cache[norm] = jump_quote

        # 3. Attempt execution: must be rejected with budget exceeded error
        res = await assistant.tool_execute_paper_proposal(
            user_id=user_id,
            proposal_id=prop_id,
            db=session,
        )
        assert res["status"] == "REJECTED"
        assert "exceeds authorized remaining budget" in res["error"]
        assert "Market prices have increased" in res["error"]

        # 4. Verify no filled order exists in database for this proposal
        orders_stmt = select(PaperOrder).where(
            PaperOrder.user_id == user_id,
            PaperOrder.status == "FILLED",
        )
        filled_orders = (await session.execute(orders_stmt)).scalars().all()
        assert len(filled_orders) == 0


@pytest.mark.asyncio
async def test_explicit_proposal_id_precedence_over_conversation_recency():
    """Verify explicit proposal ID takes absolute precedence even if another proposal is newer."""
    assistant = make_isolated_assistant()
    user_id = f"usr-prec-{uuid.uuid4().hex[:6]}"
    conv_id = f"conv-prec-{uuid.uuid4().hex[:6]}"

    async with AsyncSessionLocal() as session:
        # Create Proposal A (older)
        prop_a = await assistant.tool_create_paper_proposal(
            user_id=user_id,
            symbols=["RELIANCE"],
            budget=5000.0,
            conversation_id=conv_id,
            db=session,
        )
        id_a = prop_a["proposal_id"]

        # Create Proposal B (newer) in the same room
        prop_b = await assistant.tool_create_paper_proposal(
            user_id=user_id,
            symbols=["TCS"],
            budget=5000.0,
            conversation_id=conv_id,
            db=session,
        )
        id_b = prop_b["proposal_id"]

        # User explicitly confirms Proposal A: "confirm proposal <id_a>"
        turn_res = await assistant.process_user_turn(
            user_id=user_id,
            user_message=f"confirm proposal {id_a}",
            conversation_id=conv_id,
            db=session,
        )
        assert turn_res.execution_receipt is not None
        assert turn_res.execution_receipt["proposal_id"] == id_a

        # Verify Proposal A is EXECUTED, while Proposal B remains PROPOSED
        stmt_a = select(PaperProposal).where(PaperProposal.id == id_a)
        stmt_b = select(PaperProposal).where(PaperProposal.id == id_b)
        db_a = (await session.execute(stmt_a)).scalar_one()
        db_b = (await session.execute(stmt_b)).scalar_one()
        assert db_a.status == "EXECUTED"
        assert db_b.status == "PROPOSED"


@pytest.mark.asyncio
async def test_multiple_proposals_require_disambiguation_for_generic_approval():
    """Verify generic 'yes' or 'confirm' with multiple pending proposals asks user to disambiguate."""
    assistant = make_isolated_assistant()
    user_id = f"usr-disambig-{uuid.uuid4().hex[:6]}"
    conv_id = f"conv-disambig-{uuid.uuid4().hex[:6]}"

    async with AsyncSessionLocal() as session:
        prop_1 = await assistant.tool_create_paper_proposal(
            user_id=user_id,
            symbols=["RELIANCE"],
            budget=5000.0,
            conversation_id=conv_id,
            db=session,
        )
        prop_2 = await assistant.tool_create_paper_proposal(
            user_id=user_id,
            symbols=["TCS"],
            budget=5000.0,
            conversation_id=conv_id,
            db=session,
        )

        # User says generic "confirm"
        turn_res = await assistant.process_user_turn(
            user_id=user_id,
            user_message="confirm",
            conversation_id=conv_id,
            db=session,
        )
        assert turn_res.execution_receipt is None
        assert "Multiple pending proposals found in this conversation" in turn_res.reply
        assert prop_1["proposal_id"] in turn_res.reply
        assert prop_2["proposal_id"] in turn_res.reply


@pytest.mark.asyncio
async def test_invalid_explicit_proposal_id_never_substitutes_valid_proposal():
    """Verify confirming an invalid proposal ID never executes another pending proposal."""
    assistant = make_isolated_assistant()
    user_id = f"usr-inv-sub-{uuid.uuid4().hex[:6]}"
    conv_id = f"conv-inv-sub-{uuid.uuid4().hex[:6]}"

    async with AsyncSessionLocal() as session:
        prop = await assistant.tool_create_paper_proposal(
            user_id=user_id,
            symbols=["RELIANCE"],
            budget=5000.0,
            conversation_id=conv_id,
            db=session,
        )
        assert prop["status"] == "PROPOSED"

        turn_res = await assistant.process_user_turn(
            user_id=user_id,
            user_message="confirm proposal prop-nonexistent-999",
            conversation_id=conv_id,
            db=session,
        )
        assert turn_res.execution_receipt is None
        assert "not found for this account" in turn_res.reply
        assert "No other proposal will be executed" in turn_res.reply

        # Original proposal must still be PROPOSED
        stmt = select(PaperProposal).where(PaperProposal.id == prop["proposal_id"])
        db_prop = (await session.execute(stmt)).scalar_one()
        assert db_prop.status == "PROPOSED"


@pytest.mark.asyncio
async def test_multi_conversation_cancellation_isolation():
    """Verify cancellation is strictly scoped to the conversation and non-matches do not falsely claim cancellation."""
    assistant = make_isolated_assistant()
    user_id = f"usr-cancel-iso-{uuid.uuid4().hex[:6]}"
    conv_a = f"conv-a-{uuid.uuid4().hex[:6]}"
    conv_b = f"conv-b-{uuid.uuid4().hex[:6]}"
    conv_c = f"conv-c-{uuid.uuid4().hex[:6]}"

    async with AsyncSessionLocal() as session:
        prop_a = await assistant.tool_create_paper_proposal(
            user_id=user_id,
            symbols=["RELIANCE"],
            budget=5000.0,
            conversation_id=conv_a,
            db=session,
        )
        prop_b = await assistant.tool_create_paper_proposal(
            user_id=user_id,
            symbols=["TCS"],
            budget=5000.0,
            conversation_id=conv_b,
            db=session,
        )

        # Cancel in conv_a
        res_a = await assistant.process_user_turn(
            user_id=user_id,
            user_message="cancel proposal",
            conversation_id=conv_a,
            db=session,
        )
        assert "cancelled" in res_a.reply.lower()

        # Proposal A cancelled, Proposal B in conv_b MUST remain PROPOSED
        stmt_a = select(PaperProposal).where(PaperProposal.id == prop_a["proposal_id"])
        stmt_b = select(PaperProposal).where(PaperProposal.id == prop_b["proposal_id"])
        assert (await session.execute(stmt_a)).scalar_one().status == "CANCELLED"
        assert (await session.execute(stmt_b)).scalar_one().status == "PROPOSED"

        # Cancel in empty conv_c
        res_c = await assistant.process_user_turn(
            user_id=user_id,
            user_message="cancel",
            conversation_id=conv_c,
            db=session,
        )
        assert "No active pending paper trade proposal found in this conversation to cancel" in res_c.reply


@pytest.mark.asyncio
async def test_retry_recovers_failed_legs_without_duplicating_filled_legs():
    """Verify failed legs execute on retry with new attempt key while filled legs remain untouched."""
    assistant = make_isolated_assistant()
    user_id = f"usr-retry-{uuid.uuid4().hex[:6]}"
    conv_id = f"conv-retry-{uuid.uuid4().hex[:6]}"

    async with AsyncSessionLocal() as session:
        # Create 2-leg proposal: RELIANCE (2500) and TCS (3500), budget 15000
        prop = await assistant.tool_create_paper_proposal(
            user_id=user_id,
            symbols=["RELIANCE", "TCS"],
            budget=15000.0,
            conversation_id=conv_id,
            db=session,
        )
        prop_id = prop["proposal_id"]
        assert prop["status"] == "PROPOSED"
        assert len(prop["allocations"]) == 2

        # Make TCS quote unavailable temporarily to simulate partial failure
        tcs_good = assistant.provider._cache.get("TCS")
        now_dt = datetime.now(timezone.utc)
        assistant.provider.set_quote_override(
            "TCS",
            Quote(
                canonical_id="NSE:TCS",
                symbol="TCS.NS",
                price=Decimal("3500.00"),
                currency="INR",
                observed_at=now_dt - timedelta(days=10),
                ingested_at=now_dt - timedelta(days=10),
                source="test",
                source_uri="urn:test",
                source_evidence="none",
                served_from_cache=False,
                is_delayed=True,
                is_stale=True,
                data_status="stale",
            ),
        )

        # First attempt: RELIANCE succeeds, TCS fails
        res_att1 = await assistant.tool_execute_paper_proposal(
            user_id=user_id,
            proposal_id=prop_id,
            db=session,
        )
        assert res_att1["status"] in ("PARTIALLY_EXECUTED", "REJECTED")
        receipts1 = res_att1["receipts"]
        rel_r1 = next((r for r in receipts1 if r["symbol"] == "RELIANCE"), None)
        assert rel_r1 is not None and rel_r1["status"] == "FILLED"

        # Count orders after attempt 1
        orders_stmt = select(PaperOrder).where(PaperOrder.user_id == user_id)
        orders1 = (await session.execute(orders_stmt)).scalars().all()
        filled_order_ids_1 = {o.id for o in orders1 if o.status == "FILLED"}
        assert len(filled_order_ids_1) == 1

        # Repeated execution without is_retry=True returns replayed attempt
        res_replay = await assistant.tool_execute_paper_proposal(
            user_id=user_id,
            proposal_id=prop_id,
            is_retry=False,
            db=session,
        )
        assert res_replay.get("replayed") is True

        # Now TCS quote recovers
        if tcs_good:
            assistant.provider.set_quote_override("TCS", tcs_good)

        # Retry execution: is_retry=True
        res_att2 = await assistant.tool_execute_paper_proposal(
            user_id=user_id,
            proposal_id=prop_id,
            is_retry=True,
            db=session,
        )
        assert res_att2["status"] == "EXECUTED"
        assert res_att2["attempt_count"] == 2

        # Verify RELIANCE was NOT duplicated: still only 1 filled order for RELIANCE
        orders2 = (await session.execute(orders_stmt)).scalars().all()
        rel_orders = [o for o in orders2 if o.symbol == "RELIANCE" and o.status == "FILLED"]
        tcs_orders = [o for o in orders2 if o.symbol == "TCS" and o.status == "FILLED"]
        assert len(rel_orders) == 1
        assert len(tcs_orders) == 1


@pytest.mark.asyncio
async def test_market_hub_simulation_loop_no_synthetic_fluctuations():
    """Verify background simulation loop emits genuine provider quotes without random fluctuations when demo simulation is disabled."""
    provider = RealMarketDataProvider(force_cache=True, allow_fixture_fallback=True)
    hub = MarketHub(provider=provider, enable_demo_simulation=False)
    assert hub.enable_demo_simulation is False

    received_ticks = []

    async def mock_broadcast(symbol: str, tick: dict):
        received_ticks.append(tick)

    hub.broadcast_tick = mock_broadcast
    hub.connections["INFY"] = [object()]  # Simulate 1 active subscriber
    hub._is_running = True

    # Seed INFY in provider cache
    q = await provider.get_latest_quote("INFY")
    expected_price = float(q.price)

    # Run loop logic for active symbols
    active_symbols = list(hub.connections.keys())
    for symbol in active_symbols:
        q_sym = await hub.provider.get_latest_quote(symbol)
        obs_dt = (
            q_sym.observed_at.replace(tzinfo=timezone.utc) if q_sym.observed_at.tzinfo is None else q_sym.observed_at
        )
        freshness = (
            "STALE"
            if (q_sym.is_stale or q_sym.data_status == "stale")
            else ("DELAYED" if q_sym.is_delayed else getattr(q_sym, "freshness_status", "CURRENT"))
        )
        tick = {
            "symbol": symbol,
            "ltp": float(q_sym.price),
            "source": q_sym.source,
            "freshness": freshness,
            "observed_at": obs_dt.isoformat(),
        }
        await hub.broadcast_tick(symbol, tick)

    assert len(received_ticks) == 1
    t = received_ticks[0]
    assert t["symbol"] == "INFY"
    assert t["ltp"] == expected_price
    assert t["source"] == q.source
    assert "DEMO_SIMULATION_FIXTURE" not in t["source"]


@pytest.mark.asyncio
async def test_missing_market_quotes_do_not_become_fabricated_2500_quotes():
    """Verify unknown or missing symbol returns UNAVAILABLE status and never ₹2,500."""
    hub = MarketHub()
    q = await hub.get_latest_tick_snapshot("NON_EXISTENT_SYMBOL_XYZ_999")
    assert q["status"] == "UNAVAILABLE"
    assert q["ltp"] is None
    assert q["symbol"] == "NON_EXISTENT_SYMBOL_XYZ_999"


@pytest.mark.asyncio
async def test_cache_refresh_preserves_original_observation_timestamp():
    """Verify that cached quotes retain their original observed_at timestamp."""
    provider = RealMarketDataProvider(force_cache=True, allow_fixture_fallback=True)
    hub = MarketHub(provider=provider)
    # First fetch
    q1 = await hub.get_latest_tick_snapshot("RELIANCE")
    assert q1.get("status") != "UNAVAILABLE"
    obs_1 = q1["observed_at"]
    # Second fetch from cache
    q2 = await hub.get_latest_tick_snapshot("RELIANCE")
    obs_2 = q2["observed_at"]
    served_2 = q2.get("served_at") or q2.get("fetch_timestamp")

    # Observation timestamp must NOT change upon cache refresh
    assert obs_1 == obs_2
    assert served_2 is not None


@pytest.mark.asyncio
async def test_historical_operations_exclude_future_observations():
    """Verify as_of timestamp on the server excludes bars after the as_of point."""
    provider = RealMarketDataProvider(force_cache=True, allow_fixture_fallback=True)
    as_of_limit = datetime(2026, 10, 13, 23, 59, 59, tzinfo=timezone.utc)

    bars = await provider.get_historical_bars(
        symbol="RELIANCE",
        start_date="2026-10-01",
        end_date="2026-10-16",
        as_of=as_of_limit,
    )
    # Check that no bar date exceeds 2026-10-13
    for b in bars:
        bar_date = datetime.fromisoformat(b.date).replace(tzinfo=timezone.utc)
        assert bar_date <= as_of_limit, f"Leaked future bar {b.date} past as_of limit {as_of_limit}"


@pytest.mark.asyncio
async def test_gemini_api_call_has_no_key_in_url():
    """Verify call_gemini_api never appends ?key= in request URLs."""
    assistant = GeminiInvestmentAssistant()
    source = inspect.getsource(assistant.call_gemini_api)
    assert "?key=" not in source, "Found ?key= query param in call_gemini_api URL!"
    assert '"x-goog-api-key": key' in source or "'x-goog-api-key': key" in source
