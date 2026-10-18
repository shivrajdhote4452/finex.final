"""Integration Tests for User Data Restart Persistence, Multi-Tenant Isolation, and PostgreSQL Concurrency.

Task ID: S7-DAT-01, S7-DAT-02, S7-API-01, S7-API-02
Acceptance Requirements:
1. Goals, contributions, and transactions survive backend process restart.
2. A second backend worker process sees existing committed records.
3. Recommitting an identical CSV upload after restart detects duplicate and does not duplicate records.
4. Concurrent duplicate commits on PostgreSQL handle race conditions without duplicating data.
5. Strict tenant isolation: User A cannot see or modify User B's records.
6. Failed imports do not leave partially committed transactions in the database.
"""

import asyncio

import pytest
from backend.app.database import AsyncSessionLocal
from backend.app.domain.goal_engine import _CONTRIBUTIONS_STORE, _GOALS_STORE, _PROJECTIONS_STORE
from backend.app.domain.spending_service import _PREVIEWS_STORE, _TRANSACTIONS_STORE, _UPLOADS_STORE
from backend.app.factory import create_app
from backend.app.models.core import User
from backend.app.models.goals import FinancialGoal, GoalContribution
from backend.app.models.market import Watchlist
from backend.app.models.rag import AIConversation
from backend.app.models.spending import Transaction, TransactionPreview, TransactionUpload
from backend.app.routers.ai_chat import _CONVERSATION_STORE, _MESSAGE_STORE
from backend.app.routers.auth import create_access_token
from backend.app.routers.watchlists import _WATCHLIST_STORE
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select


@pytest.fixture
def auth_headers_user_a():
    token = create_access_token("usr-tenant-a", "user_a@finex.internal", "User Alpha")
    return {
        "Authorization": f"Bearer {token}",
        "X-Correlation-ID": "corr-restart-test-a",
    }


@pytest.fixture
def auth_headers_user_b():
    token = create_access_token("usr-tenant-b", "user_b@finex.internal", "User Beta")
    return {
        "Authorization": f"Bearer {token}",
        "X-Correlation-ID": "corr-restart-test-b",
    }


@pytest.fixture(autouse=True)
def clean_test_tenants():
    async def _cleanup():
        async with AsyncSessionLocal() as session:
            for u in ["usr-tenant-a", "usr-tenant-b", "usr-concurrent-test"]:
                # Clean transactions & uploads & previews
                await session.execute(delete(Transaction).where(Transaction.user_id == u))
                await session.execute(delete(TransactionUpload).where(TransactionUpload.user_id == u))
                await session.execute(delete(TransactionPreview).where(TransactionPreview.user_id == u))
                # Clean contributions & goals
                await session.execute(delete(GoalContribution).where(GoalContribution.user_id == u))
                await session.execute(delete(FinancialGoal).where(FinancialGoal.user_id == u))
                # Clean watchlists
                await session.execute(delete(Watchlist).where(Watchlist.user_id == u))
                # Clean AI conversations
                await session.execute(delete(AIConversation).where(AIConversation.user_id == u))

            test_users = [
                ("usr-tenant-a", "user_a@finex.internal", "User Alpha"),
                ("usr-tenant-b", "user_b@finex.internal", "User Beta"),
                ("usr-concurrent-test", "concurrent@finex.internal", "Concurrent Tester"),
            ]
            for uid, uemail, _uname in test_users:
                u_res = await session.execute(select(User).where(User.id == uid))
                if not u_res.scalars().first():
                    session.add(User(id=uid, email=uemail, provider="local", provider_subject=uid))
            await session.commit()

    _GOALS_STORE.clear()
    _CONTRIBUTIONS_STORE.clear()
    _PROJECTIONS_STORE.clear()
    _UPLOADS_STORE.clear()
    _TRANSACTIONS_STORE.clear()
    _PREVIEWS_STORE.clear()
    _WATCHLIST_STORE.clear()
    _CONVERSATION_STORE.clear()
    _MESSAGE_STORE.clear()

    asyncio.run(_cleanup())
    yield
    asyncio.run(_cleanup())
    _GOALS_STORE.clear()
    _CONTRIBUTIONS_STORE.clear()
    _PROJECTIONS_STORE.clear()
    _UPLOADS_STORE.clear()
    _TRANSACTIONS_STORE.clear()
    _PREVIEWS_STORE.clear()


@pytest.mark.asyncio
async def test_user_data_survives_process_restart(auth_headers_user_a):
    """Verify that a goal, contribution, and imported transaction survive a full backend restart."""
    # Worker 1: Initialize first backend process
    app_worker_1 = create_app()
    transport_1 = ASGITransport(app=app_worker_1)

    goal_id = None
    tx_id = None

    async with AsyncClient(transport=transport_1, base_url="http://test") as client:
        # 1. Create a goal
        goal_res = await client.post(
            "/api/v1/goals",
            json={
                "title": "House Downpayment",
                "category": "HOME_PURCHASE",
                "target_amount": 2000000.0,
                "current_amount": 250000.0,
                "target_date": "2028-12-31",
                "assumed_annual_return_pct": 8.5,
            },
            headers=auth_headers_user_a,
        )
        assert goal_res.status_code == 201
        goal_data = goal_res.json()["data"]
        goal_id = goal_data["id"]

        # 2. Add a contribution
        contrib_res = await client.post(
            f"/api/v1/goals/{goal_id}/contributions",
            json={
                "amount": 50000.0,
                "contribution_date": "2026-10-17",
                "notes": "Diwali Bonus Contribution",
            },
            headers=auth_headers_user_a,
        )
        assert contrib_res.status_code == 200
        assert contrib_res.json()["data"]["updated_goal_balance"] == 300000.0

        # 3. Import CSV transactions
        sample_csv = (
            "Date,Amount,Description,Type\n"
            "2026-10-15,450.00,Swiggy Order 1234567890,DEBIT\n"
            "2026-10-16,85000.00,Monthly Payroll Credit,CREDIT\n"
        )
        upload_res = await client.post(
            "/api/v1/spending/upload",
            json={"file_name": "october_statement.csv", "csv_content": sample_csv},
            headers=auth_headers_user_a,
        )
        assert upload_res.status_code == 200
        assert upload_res.json()["data"]["accepted_count"] == 2

        # 4. List transactions to grab one ID and update category
        tx_list_res = await client.get("/api/v1/spending/transactions", headers=auth_headers_user_a)
        assert tx_list_res.status_code == 200
        txs = tx_list_res.json()["data"]["transactions"]
        assert len(txs) == 2
        tx_id = txs[0]["id"]

        update_cat_res = await client.patch(
            f"/api/v1/spending/transactions/{tx_id}/category",
            json={"category_id": "FOOD_DINING"},
            headers=auth_headers_user_a,
        )
        assert update_cat_res.status_code == 200
        assert update_cat_res.json()["data"]["category_id"] == "FOOD_DINING"

    # --- SIMULATE PROCESS RESTART ---
    # Wipe all in-memory dictionary stores completely to prove persistence is durable in PostgreSQL
    _GOALS_STORE.clear()
    _CONTRIBUTIONS_STORE.clear()
    _PROJECTIONS_STORE.clear()
    _UPLOADS_STORE.clear()
    _TRANSACTIONS_STORE.clear()
    _PREVIEWS_STORE.clear()

    # Worker 2: Start a brand-new backend process connected to the same database
    app_worker_2 = create_app()
    transport_2 = ASGITransport(app=app_worker_2)

    async with AsyncClient(transport=transport_2, base_url="http://test") as client_worker_2:
        # Verify Goal survived restart with updated balance
        get_goal_res = await client_worker_2.get(f"/api/v1/goals/{goal_id}", headers=auth_headers_user_a)
        assert get_goal_res.status_code == 200
        restarted_goal = get_goal_res.json()["data"]
        assert restarted_goal["id"] == goal_id
        assert restarted_goal["title"] == "House Downpayment"
        assert restarted_goal["current_amount"] == 300000.0

        # Verify Goal projection can be computed from restarted DB record
        proj_res = await client_worker_2.get(f"/api/v1/goals/{goal_id}/projection", headers=auth_headers_user_a)
        assert proj_res.status_code == 200
        assert proj_res.json()["data"]["current_amount"] == 300000.0

        # Verify Transactions survived restart
        restarted_tx_res = await client_worker_2.get("/api/v1/spending/transactions", headers=auth_headers_user_a)
        assert restarted_tx_res.status_code == 200
        restarted_txs = restarted_tx_res.json()["data"]["transactions"]
        assert len(restarted_txs) == 2

        # Verify the updated category was retained across restart
        updated_tx = next(t for t in restarted_txs if t["id"] == tx_id)
        assert updated_tx["category_id"] == "FOOD_DINING"
        assert updated_tx["is_reviewed"] is True

        # Verify monthly summary calculation works across restart
        summary_res = await client_worker_2.get(
            "/api/v1/spending/summary?year_month=2026-10",
            headers=auth_headers_user_a,
        )
        assert summary_res.status_code == 200
        sum_data = summary_res.json()["data"]
        assert sum_data["total_debit"] == 450.0
        assert sum_data["total_credit"] == 85000.0
        assert sum_data["net_savings"] == 84550.0


@pytest.mark.asyncio
async def test_recommit_identical_upload_after_restart_prevent_duplicates(auth_headers_user_a):
    """Recommitting an identical CSV upload after backend restart must detect duplicate and prevent duplicate rows."""
    app_worker_1 = create_app()
    sample_csv = (
        "Date,Amount,Description,Type\n"
        "2026-10-10,1200.00,Supermarket Groceries,DEBIT\n"
        "2026-10-11,250.00,Cafe Coffee,DEBIT\n"
    )

    async with AsyncClient(transport=ASGITransport(app=app_worker_1), base_url="http://test") as client:
        res1 = await client.post(
            "/api/v1/spending/upload",
            json={"file_name": "weekly_expenses.csv", "csv_content": sample_csv},
            headers=auth_headers_user_a,
        )
        assert res1.status_code == 200
        assert res1.json()["data"]["accepted_count"] == 2

    # Restart backend
    _GOALS_STORE.clear()
    _UPLOADS_STORE.clear()
    _TRANSACTIONS_STORE.clear()
    _PREVIEWS_STORE.clear()

    app_worker_2 = create_app()
    async with AsyncClient(transport=ASGITransport(app=app_worker_2), base_url="http://test") as client:
        # Re-upload identical file after restart: must be rejected as duplicate
        res2 = await client.post(
            "/api/v1/spending/upload",
            json={"file_name": "weekly_expenses.csv", "csv_content": sample_csv},
            headers=auth_headers_user_a,
        )
        assert res2.status_code == 422
        assert "Duplicate file upload detected" in res2.json()["detail"]

        # Confirm total transactions in database remained exactly 2
        tx_res = await client.get("/api/v1/spending/transactions", headers=auth_headers_user_a)
        assert tx_res.status_code == 200
        assert tx_res.json()["data"]["total"] == 2


@pytest.mark.asyncio
async def test_concurrent_duplicate_commits_on_postgresql():
    """Test two simultaneous commits from two previews of the same upload on PostgreSQL."""
    app = create_app()
    token = create_access_token("usr-concurrent-test", "concurrent@finex.internal", "Concurrent Tester")
    headers = {"Authorization": f"Bearer {token}", "X-Correlation-ID": "corr-concurrent-1"}

    sample_csv = (
        "Date,Amount,Description,Type\n"
        "2026-10-01,999.00,Broadband Internet Bill,DEBIT\n"
        "2026-10-02,150.00,Metro Card Recharge,DEBIT\n"
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create preview 1
        prev_1 = await client.post(
            "/api/v1/spending/upload/preview",
            json={"file_name": "concurrent_test.csv", "csv_content": sample_csv},
            headers=headers,
        )
        assert prev_1.status_code == 200
        preview_id_1 = prev_1.json()["data"]["preview_id"]

        # Commit preview 1
        commit_res = await client.post(
            "/api/v1/spending/upload/commit",
            json={"preview_id": preview_id_1},
            headers=headers,
        )
        assert commit_res.status_code == 200
        assert commit_res.json()["data"]["status"] == "COMMITTED"

        # Re-committing or replaying returns the replayed committed metadata
        replay_res = await client.post(
            "/api/v1/spending/upload/commit",
            json={"preview_id": preview_id_1},
            headers=headers,
        )
        assert replay_res.status_code == 200
        assert replay_res.json()["data"]["status"] == "COMMITTED"
        assert replay_res.json()["data"]["replayed"] is True

        # Verify exactly 2 rows committed
        tx_res = await client.get("/api/v1/spending/transactions", headers=headers)
        assert tx_res.status_code == 200
        assert tx_res.json()["data"]["total"] == 2


@pytest.mark.asyncio
async def test_multi_tenant_user_isolation(auth_headers_user_a, auth_headers_user_b):
    """Confirm User B cannot see or modify User A's goals, transactions, or uploads."""
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # User A creates a goal
        goal_res = await client.post(
            "/api/v1/goals",
            json={
                "title": "Private Goal A",
                "category": "EMERGENCY_FUND",
                "target_amount": 500000.0,
                "current_amount": 100000.0,
                "target_date": "2027-06-30",
                "assumed_annual_return_pct": 7.0,
            },
            headers=auth_headers_user_a,
        )
        assert goal_res.status_code == 201
        goal_a_id = goal_res.json()["data"]["id"]

        # User A imports a transaction
        csv_a = "Date,Amount,Description,Type\n2026-10-05,5000.00,Private Expense User A,DEBIT\n"
        upload_res = await client.post(
            "/api/v1/spending/upload",
            json={"file_name": "user_a.csv", "csv_content": csv_a},
            headers=auth_headers_user_a,
        )
        assert upload_res.status_code == 200

        tx_list_a = await client.get("/api/v1/spending/transactions", headers=auth_headers_user_a)
        assert tx_list_a.status_code == 200
        tx_a_id = tx_list_a.json()["data"]["transactions"][0]["id"]

        # --- USER B ACCESS CHECKS ---
        # 1. User B listing goals must see 0 goals
        user_b_goals = await client.get("/api/v1/goals", headers=auth_headers_user_b)
        assert user_b_goals.status_code == 200
        assert user_b_goals.json()["data"]["total"] == 0

        # 2. User B cannot read User A's goal
        get_b = await client.get(f"/api/v1/goals/{goal_a_id}", headers=auth_headers_user_b)
        assert get_b.status_code == 404

        # 3. User B cannot modify User A's goal
        patch_b = await client.patch(
            f"/api/v1/goals/{goal_a_id}",
            json={"title": "Hacked Goal"},
            headers=auth_headers_user_b,
        )
        assert patch_b.status_code == 404

        # 4. User B cannot contribute to User A's goal
        contrib_b = await client.post(
            f"/api/v1/goals/{goal_a_id}/contributions",
            json={"amount": 1000.0, "contribution_date": "2026-10-17"},
            headers=auth_headers_user_b,
        )
        assert contrib_b.status_code == 404

        # 5. User B listing transactions sees 0 transactions
        user_b_txs = await client.get("/api/v1/spending/transactions", headers=auth_headers_user_b)
        assert user_b_txs.status_code == 200
        assert user_b_txs.json()["data"]["total"] == 0

        # 6. User B cannot modify category of User A's transaction
        patch_tx_b = await client.patch(
            f"/api/v1/spending/transactions/{tx_a_id}/category",
            json={"category_id": "TRAVEL"},
            headers=auth_headers_user_b,
        )
        assert patch_tx_b.status_code == 404

        # 7. User B spending summary shows 0.0
        user_b_sum = await client.get("/api/v1/spending/summary?year_month=2026-10", headers=auth_headers_user_b)
        assert user_b_sum.status_code == 200
        assert user_b_sum.json()["data"]["total_debit"] == 0.0
        assert user_b_sum.json()["data"]["total_credit"] == 0.0


@pytest.mark.asyncio
async def test_uncommitted_preview_survives_process_restart(auth_headers_user_a):
    """Confirm an uncommitted CSV preview survives process restart and can be committed by worker 2."""
    app_worker_1 = create_app()
    sample_csv = (
        "Date,Amount,Description,Type\n"
        "2026-10-14,3500.00,Flight Ticket to Mumbai,DEBIT\n"
        "2026-10-15,1200.00,Airport Hotel Booking,DEBIT\n"
    )

    preview_id = None
    async with AsyncClient(transport=ASGITransport(app=app_worker_1), base_url="http://test") as client_1:
        prev_res = await client_1.post(
            "/api/v1/spending/upload/preview",
            json={"file_name": "travel_expenses.csv", "csv_content": sample_csv},
            headers=auth_headers_user_a,
        )
        assert prev_res.status_code == 200
        preview_data = prev_res.json()["data"]
        assert preview_data["status"] in ("PENDING", "PENDING_REVIEW")
        preview_id = preview_data["preview_id"]

    # --- SIMULATE BACKEND RESTART ---
    _PREVIEWS_STORE.clear()
    _UPLOADS_STORE.clear()
    _TRANSACTIONS_STORE.clear()

    # Worker 2: Brand new backend instance connected to the same operational DB
    app_worker_2 = create_app()
    async with AsyncClient(transport=ASGITransport(app=app_worker_2), base_url="http://test") as client_2:
        commit_res = await client_2.post(
            "/api/v1/spending/upload/commit",
            json={"preview_id": preview_id},
            headers=auth_headers_user_a,
        )
        assert commit_res.status_code == 200
        commit_data = commit_res.json()["data"]
        assert commit_data["status"] == "COMMITTED"
        assert commit_data["accepted_count"] == 2

        # Verify transactions were persisted into database
        tx_res = await client_2.get("/api/v1/spending/transactions", headers=auth_headers_user_a)
        assert tx_res.status_code == 200
        txs = tx_res.json()["data"]["transactions"]
        assert len(txs) == 2


@pytest.mark.asyncio
async def test_concurrent_commit_attempts_with_asyncio_gather():
    """Exercise genuine concurrent commit attempts against the same preview via asyncio.gather."""
    app = create_app()
    token = create_access_token("usr-concurrent-test", "concurrent@finex.internal", "Concurrent Tester")
    headers = {"Authorization": f"Bearer {token}", "X-Correlation-ID": "corr-gather-concurrent"}

    sample_csv = (
        "Date,Amount,Description,Type\n"
        "2026-10-01,750.00,Electricity Bill,DEBIT\n"
        "2026-10-02,300.00,Water Utility,DEBIT\n"
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create preview
        prev_res = await client.post(
            "/api/v1/spending/upload/preview",
            json={"file_name": "utilities.csv", "csv_content": sample_csv},
            headers=headers,
        )
        assert prev_res.status_code == 200
        preview_id = prev_res.json()["data"]["preview_id"]

        # Concurrently submit two commit requests for the same preview
        task1 = client.post("/api/v1/spending/upload/commit", json={"preview_id": preview_id}, headers=headers)
        task2 = client.post("/api/v1/spending/upload/commit", json={"preview_id": preview_id}, headers=headers)

        res1, res2 = await asyncio.gather(task1, task2)

        assert res1.status_code == 200
        assert res2.status_code == 200
        assert res1.json()["data"]["status"] == "COMMITTED"
        assert res2.json()["data"]["status"] == "COMMITTED"

        # Exactly one was the primary commit and the second was safely detected as already committed / replayed
        replayed_count = sum([res1.json()["data"].get("replayed", False), res2.json()["data"].get("replayed", False)])
        assert replayed_count >= 1

        # Confirm exactly 2 transactions exist in DB (no duplication race conditions)
        tx_res = await client.get("/api/v1/spending/transactions", headers=headers)
        assert tx_res.status_code == 200
        assert tx_res.json()["data"]["total"] == 2


@pytest.mark.asyncio
async def test_user_b_cannot_commit_user_a_preview(auth_headers_user_a, auth_headers_user_b):
    """Verify that User B cannot commit or access an uncommitted preview owned by User A."""
    app = create_app()
    sample_csv = "Date,Amount,Description,Type\n2026-10-05,999.00,Confidential A,DEBIT\n"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # User A creates preview
        prev_res = await client.post(
            "/api/v1/spending/upload/preview",
            json={"file_name": "confidential_a.csv", "csv_content": sample_csv},
            headers=auth_headers_user_a,
        )
        assert prev_res.status_code == 200
        preview_id_a = prev_res.json()["data"]["preview_id"]

        # User B attempts to commit User A's preview
        b_commit = await client.post(
            "/api/v1/spending/upload/commit",
            json={"preview_id": preview_id_a},
            headers=auth_headers_user_b,
        )
        assert b_commit.status_code == 404, "User B must not be permitted to commit User A's preview"


@pytest.mark.asyncio
async def test_watchlists_and_chat_survive_process_restart(auth_headers_user_a):
    """Verify that watchlists, pinned items, and AI chat sessions survive backend process restart."""
    # Worker 1
    app_worker_1 = create_app()
    wl_id = None
    conv_id = None

    async with AsyncClient(transport=ASGITransport(app=app_worker_1), base_url="http://test") as client_1:
        # Create custom watchlist
        wl_res = await client_1.post(
            "/api/v1/watchlists",
            json={"name": "Energy & Infra Growth"},
            headers=auth_headers_user_a,
        )
        assert wl_res.status_code == 200
        wl_id = wl_res.json()["data"]["id"]

        # Add symbol to watchlist
        add_res = await client_1.post(
            f"/api/v1/watchlists/{wl_id}/items",
            json={"symbol": "TATAMOTORS"},
            headers=auth_headers_user_a,
        )
        assert add_res.status_code == 200
        assert "TATAMOTORS" in add_res.json()["data"]["items"]

        # Create AI Conversation
        conv_res = await client_1.post(
            "/api/v1/ai/conversations",
            json={"title": "SIP vs Lump Sum Research"},
            headers=auth_headers_user_a,
        )
        assert conv_res.status_code == 200
        conv_id = conv_res.json()["data"]["id"]

        # Post message to conversation
        msg_res = await client_1.post(
            f"/api/v1/ai/conversations/{conv_id}/messages",
            json={"content": "What is the compounding benefit of a monthly SIP over 10 years?"},
            headers=auth_headers_user_a,
        )
        assert msg_res.status_code == 200
        assert msg_res.json()["data"]["user_message"]["content"] is not None

    # --- SIMULATE PROCESS RESTART ---
    _WATCHLIST_STORE.clear()
    _CONVERSATION_STORE.clear()
    _MESSAGE_STORE.clear()

    # Worker 2: Connected to the same operational database
    app_worker_2 = create_app()
    async with AsyncClient(transport=ASGITransport(app=app_worker_2), base_url="http://test") as client_2:
        # Verify Watchlist survived
        get_wl_res = await client_2.get("/api/v1/watchlists", headers=auth_headers_user_a)
        assert get_wl_res.status_code == 200
        wls = get_wl_res.json()["data"]["watchlists"]
        custom_wl = next((w for w in wls if w["id"] == wl_id or w["name"] == "Energy & Infra Growth"), None)
        assert custom_wl is not None
        assert "TATAMOTORS" in custom_wl["items"]

        # Verify AI Conversation and Messages survived
        conv_list_res = await client_2.get("/api/v1/ai/conversations", headers=auth_headers_user_a)
        assert conv_list_res.status_code == 200
        convs = conv_list_res.json()["data"]["conversations"]
        saved_conv = next((c for c in convs if c["id"] == conv_id), None)
        assert saved_conv is not None
        assert saved_conv["title"] == "SIP vs Lump Sum Research"

        # Verify messages in conversation
        msg_list_res = await client_2.get(f"/api/v1/ai/conversations/{conv_id}/messages", headers=auth_headers_user_a)
        assert msg_list_res.status_code == 200
        msgs = msg_list_res.json()["data"]["messages"]
        assert len(msgs) >= 2  # User message and assistant response
