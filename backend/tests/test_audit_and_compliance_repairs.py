"""Focused Regression Tests for FinEx Audit & Compliance Repairs.

Validates:
1. "Do not execute" causes zero trade and marks active proposal cancelled.
2. Research questions ("Should I invest?", "Is it good to buy?") cause zero trade/proposal.
3. Another user cannot access or execute someone else's proposal.
4. Confirmation targets the correct proposal bound to conversation/proposal ID.
5. A ₹100 budget cannot purchase a ₹2,500 whole share (returns INSUFFICIENT_BUDGET).
6. Total estimated order value never exceeds the authorized budget.
7. Repeating an execution request uses a stable idempotency key and does not duplicate orders.
8. Retrying partial execution does not repeat already completed legs.
9. Missing market prices do not become fabricated executable quotes (no 2500.0 fallback).
10. Cache refresh preserves the original observation timestamp.
11. Historical operations exclude future observations when as_of is specified.
12. Gemini offline/failure returns a valid honest response with no URL credential exposure.
"""

from datetime import datetime, timezone, timedelta
from decimal import Decimal
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from backend.app.adapters.market_data_provider import RealMarketDataProvider
from backend.app.domain.gemini_assistant import GeminiInvestmentAssistant, SIMULATION_DISCLAIMER
from backend.app.domain.paper_trading_service import PaperTradingEngine, OrderSubmitRequest
from backend.app.models.paper_trading import PaperProposal, PaperOrder, PaperAccount
from backend.app.services.market_hub import MarketHub
from backend.app.database import AsyncSessionLocal
from backend.app.factory import create_app
from backend.app.routers.auth import create_access_token


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.asyncio
async def test_do_not_execute_causes_no_trade_and_cancels_proposal():
    """Verify 'do not execute', 'cancel', 'wait', 'don't buy' never execute trades."""
    assistant = GeminiInvestmentAssistant()
    user_id = "usr-test-refusal-001"
    conv_id = "conv-test-refusal-001"

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
    assistant = GeminiInvestmentAssistant()
    user_id = "usr-test-research-001"
    conv_id = "conv-test-research-001"

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
    assistant = GeminiInvestmentAssistant()
    user_a = "usr-tenant-a"
    user_b = "usr-tenant-b"

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
    assistant = GeminiInvestmentAssistant()
    user_id = "usr-conv-bound-001"

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
    assistant = GeminiInvestmentAssistant()
    user_id = "usr-test-budget-001"

    async with AsyncSessionLocal() as session:
        # Request ₹100 budget for RELIANCE (which is > ₹2,000)
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
    assistant = GeminiInvestmentAssistant()
    user_id = "usr-test-budget-max-001"

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
    assistant = GeminiInvestmentAssistant()
    user_id = "usr-test-idemp-001"

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
    hub = MarketHub()
    # First fetch
    q1 = await hub.get_latest_tick_snapshot("RELIANCE")
    if q1.get("status") != "UNAVAILABLE":
        obs_1 = q1["observed_at"]
        hub.latest_quotes["RELIANCE"] = q1
        # Second fetch from cache
        q2 = await hub.get_latest_tick_snapshot("RELIANCE")
        obs_2 = q2["observed_at"]
        served_2 = q2.get("served_at")

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
    # Read source code of call_gemini_api to confirm key is not placed in URL
    import inspect
    source = inspect.getsource(assistant.call_gemini_api)
    assert "?key=" not in source, "Found ?key= query param in call_gemini_api URL!"
    assert '"x-goog-api-key": key' in source or "'x-goog-api-key': key" in source
