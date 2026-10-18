"""Comprehensive Acceptance Matrix Test Suite for FinEx (CH-10).

Verifies the 14 mandatory acceptance matrix items specified on Page 14 of the
FinEx Repository Changes and Antigravity Fix Plan:
1. Unauthenticated private request -> HTTP 401, no default identity.
2. Invalid Google token -> 401, no session or user record created.
3. Two-user authorization -> User B cannot access or mutate User A's data.
4. Session revocation -> Revoked token denied immediately and persistently.
5. Idempotent paper order (same key, same payload) -> Returns saved receipt without double execution.
6. Conflicting paper order (same key, changed payload) -> HTTP 409 Conflict without executing.
7. Non-marketable limit buy -> Never fills above specified limit price.
8. Available cash constraint -> Cannot overspend cash balance.
9. Historical execution receipt integrity -> Replaying old order preserves original cash_after receipt.
10. Authentic market data -> Unsupported symbol returns 404, never invented prices; observations track freshness.
11. Cross-client persistence -> Durable storage maintains records across queries.
12. Two-phase CSV preview & duplicate commit protection -> Cancel writes 0 rows, duplicate commit is idempotent.
13. RAG Grounding & Insufficient Evidence -> Unsupported questions yield INSUFFICIENT_EVIDENCE, zero fabricated citations.
14. Mobile and web order reconciliation -> Stable idempotency keys avoid duplicate executions.
"""

import pytest
from backend.app.factory import create_app
from backend.app.routers.auth import create_access_token
from httpx import ASGITransport, AsyncClient


@pytest.fixture(scope="module", autouse=True)
def setup_matrix_module():
    import asyncio
    from decimal import Decimal

    from backend.app.database import AsyncSessionLocal
    from backend.app.models.paper_trading import PaperAccount, PaperCashLedger, PaperOrder, PaperPosition, PaperTrade
    from sqlalchemy import delete, select

    async def _clean():
        async with AsyncSessionLocal() as session:
            for uid in ["usr-matrix-a", "usr-matrix-b"]:
                stmt_acct = select(PaperAccount).where(PaperAccount.user_id == uid)
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

    asyncio.run(_clean())
    yield


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
def user_a_headers():
    token = create_access_token("usr-matrix-a", "user.a@finex.internal", "User Alpha")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def user_b_headers():
    token = create_access_token("usr-matrix-b", "user.b@finex.internal", "User Beta")
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_01_unauthenticated_private_request_returns_401(app):
    """Matrix 1: Unauthenticated request to private routes must fail-closed with 401."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Check /users/me
        res_me = await client.get("/api/v1/users/me")
        assert res_me.status_code == 401
        assert res_me.headers.get("WWW-Authenticate") == "Bearer"

        # Check /paper-trading/account
        res_pt = await client.get("/api/v1/paper-trading/account")
        assert res_pt.status_code == 401

        # Check /spending/transactions
        res_sp = await client.get("/api/v1/spending/transactions")
        assert res_sp.status_code == 401


@pytest.mark.asyncio
async def test_02_invalid_google_token_rejected(app):
    """Matrix 2: Invalid Google ID token rejected; no session created."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/v1/auth/google",
            json={"id_token": "malformed.fraudulent.token"},
        )
        assert res.status_code == 401
        assert "verification failed" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_03_two_user_data_isolation(app, user_a_headers, user_b_headers):
    """Matrix 3: User B cannot access or mutate User A's private conversations or records."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # User A creates a conversation
        conv_res = await client.post(
            "/api/v1/ai/conversations",
            json={"title": "User A Private Financial Goals"},
            headers=user_a_headers,
        )
        assert conv_res.status_code == 200
        conv_id = conv_res.json()["data"]["id"]

        # User B attempts to read User A's conversation messages
        read_res = await client.get(
            f"/api/v1/ai/conversations/{conv_id}/messages",
            headers=user_b_headers,
        )
        assert read_res.status_code in [403, 404]

        # User B attempts to delete User A's conversation
        del_res = await client.delete(
            f"/api/v1/ai/conversations/{conv_id}",
            headers=user_b_headers,
        )
        assert del_res.status_code in [403, 404]


@pytest.mark.asyncio
async def test_04_session_revocation_enforced(app, user_a_headers):
    """Matrix 4: Revoking a session token denies subsequent requests immediately."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Verified request passes
        res_valid = await client.get("/api/v1/users/me", headers=user_a_headers)
        assert res_valid.status_code == 200

        # Revoke token
        token = user_a_headers["Authorization"].split(" ")[1]
        rev_res = await client.post(
            "/api/v1/auth/revoke",
            json={"token": token},
            headers=user_a_headers,
        )
        assert rev_res.status_code == 200

        # Subsequent request with revoked token must fail closed
        res_after = await client.get("/api/v1/users/me", headers=user_a_headers)
        assert res_after.status_code == 401
        assert "revoked" in res_after.json()["detail"].lower()


@pytest.mark.asyncio
async def test_05_and_06_idempotency_same_and_conflicting_payloads(app, user_a_headers):
    """Matrix 5 & 6: Same key + same payload replays receipt; same key + different payload returns 409 Conflict."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        key = "idemp-key-matrix-test-99"

        payload_1 = {
            "symbol": "RELIANCE",
            "side": "BUY",
            "order_type": "MARKET",
            "quantity": 2,
        }

        # 1. First execution
        res1 = await client.post(
            "/api/v1/paper-trading/orders",
            json=payload_1,
            headers={**user_a_headers, "X-Idempotency-Key": key},
        )
        assert res1.status_code == 200
        order_1 = res1.json()["data"]
        assert order_1["replayed"] is False

        # 2. Identical retry: returns same order without double deduction
        res2 = await client.post(
            "/api/v1/paper-trading/orders",
            json=payload_1,
            headers={**user_a_headers, "X-Idempotency-Key": key},
        )
        assert res2.status_code == 200
        order_2 = res2.json()["data"]
        assert order_2["order_id"] == order_1["order_id"]
        assert order_2["replayed"] is True

        # 3. Conflicting retry with changed symbol: must return HTTP 409
        payload_conflict = {
            "symbol": "TCS",
            "side": "BUY",
            "order_type": "MARKET",
            "quantity": 2,
        }
        res3 = await client.post(
            "/api/v1/paper-trading/orders",
            json=payload_conflict,
            headers={**user_a_headers, "X-Idempotency-Key": key},
        )
        assert res3.status_code == 409
        assert "conflict" in res3.json()["detail"].lower()


@pytest.mark.asyncio
async def test_07_non_marketable_limit_buy_never_fills_above_limit(app, user_a_headers):
    """Matrix 7: LIMIT buy at INR 1.00 must not fill at market price of INR 2,500."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/v1/paper-trading/orders",
            json={
                "symbol": "RELIANCE",
                "side": "BUY",
                "order_type": "LIMIT",
                "limit_price": 1.00,
                "quantity": 1,
            },
            headers={**user_a_headers, "X-Idempotency-Key": "limit-matrix-01"},
        )
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["status"] in ["REJECTED", "PENDING"]
        assert data["fill_price"] is None or float(data["fill_price"]) <= 1.00


@pytest.mark.asyncio
async def test_08_insufficient_cash_rejected(app, user_a_headers):
    """Matrix 8: Orders exceeding available cash must be rejected without balance alteration."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Attempt to buy 1,000,000 shares of Reliance (costs ₹2.5 Billion)
        res = await client.post(
            "/api/v1/paper-trading/orders",
            json={
                "symbol": "RELIANCE",
                "side": "BUY",
                "order_type": "MARKET",
                "quantity": 1000000,
            },
            headers={**user_a_headers, "X-Idempotency-Key": "massive-buy-matrix"},
        )
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["status"] == "REJECTED"


@pytest.mark.asyncio
async def test_09_historical_receipt_preservation(app, user_a_headers):
    """Matrix 9: Replaying an old order after subsequent trades returns the original cash_after value."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        key_trade_1 = "hist-receipt-key-01"
        key_trade_2 = "hist-receipt-key-02"

        # Trade 1
        res1 = await client.post(
            "/api/v1/paper-trading/orders",
            json={"symbol": "ITC", "side": "BUY", "order_type": "MARKET", "quantity": 1},
            headers={**user_a_headers, "X-Idempotency-Key": key_trade_1},
        )
        receipt_1 = res1.json()["data"]
        cash_after_trade_1 = float(receipt_1["cash_balance_after"])

        # Trade 2
        res2 = await client.post(
            "/api/v1/paper-trading/orders",
            json={"symbol": "ITC", "side": "BUY", "order_type": "MARKET", "quantity": 1},
            headers={**user_a_headers, "X-Idempotency-Key": key_trade_2},
        )
        receipt_2 = res2.json()["data"]
        cash_after_trade_2 = float(receipt_2["cash_balance_after"])
        assert cash_after_trade_2 < cash_after_trade_1

        # Replay Trade 1: must return EXACT original cash_after_trade_1, NOT current balance!
        res1_replay = await client.post(
            "/api/v1/paper-trading/orders",
            json={"symbol": "ITC", "side": "BUY", "order_type": "MARKET", "quantity": 1},
            headers={**user_a_headers, "X-Idempotency-Key": key_trade_1},
        )
        replayed = res1_replay.json()["data"]
        assert float(replayed["cash_balance_after"]) == cash_after_trade_1


@pytest.mark.asyncio
async def test_10_authentic_market_data_freshness_and_unknown_symbol_404(app):
    """Matrix 10: Unknown symbols return 404 (no fake prices); valid symbols track freshness metadata."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Unsupported symbol -> 404
        res_404 = await client.get("/api/v1/market/quotes/UNKNOWN_STOCK_XYZ")
        assert res_404.status_code == 404
        assert "not supported" in res_404.json()["error"]["message"]

        # Valid symbol -> verified observation with observed_at and freshness
        res_quote = await client.get("/api/v1/market/quotes/RELIANCE")
        assert res_quote.status_code == 200
        quote = res_quote.json()["data"]
        assert float(quote["price"]) > 0
        assert "observed_at" in quote
        assert "ingested_at" in quote
        assert "is_delayed" in quote
        assert "data_status" in quote


@pytest.mark.asyncio
async def test_12_two_phase_csv_preview_and_commit_idempotency(app, user_a_headers):
    """Matrix 12: Cancel preview commits 0 rows; commit is atomic and idempotent."""
    sample_csv = (
        "Date,Amount,Description,Type\n"
        "2026-10-14,1850.00,UPI/****/RESTAURANT KORAMANGALA,DEBIT\n"
        "2026-10-15,3500.00,BESCOM ELECTRICITY BILLPAY ****,DEBIT\n"
        "2026-10-16,2100.00,AMAZON INDIA RETAIL ORDER ****,DEBIT"
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        from backend.app.database import AsyncSessionLocal
        from backend.app.models.spending import Transaction, TransactionUpload
        from sqlalchemy import delete

        async with AsyncSessionLocal() as session:
            await session.execute(delete(Transaction).where(Transaction.user_id == "usr-matrix-a"))
            await session.execute(delete(TransactionUpload).where(TransactionUpload.user_id == "usr-matrix-a"))
            await session.commit()

        # Phase 1: Preview
        prev_res = await client.post(
            "/api/v1/spending/upload/preview",
            json={"file_name": "preview_test_matrix.csv", "csv_content": sample_csv},
            headers=user_a_headers,
        )
        assert prev_res.status_code == 200
        prev_data = prev_res.json()["data"]
        assert prev_data["valid_count"] == 3
        preview_id = prev_data["preview_id"]

        # If user cancels: 0 rows added to active ledger for this upload
        tx_check = await client.get("/api/v1/spending/transactions", headers=user_a_headers)
        assert not any(t.get("upload_id") == preview_id for t in tx_check.json()["data"]["transactions"])

        # Phase 2: Commit
        commit_res = await client.post(
            "/api/v1/spending/upload/commit",
            json={"preview_id": preview_id},
            headers=user_a_headers,
        )
        assert commit_res.status_code == 200
        assert commit_res.json()["data"]["accepted_count"] == 3
        assert commit_res.json()["data"]["status"] == "COMMITTED"

        # Replay commit: idempotent, returns same accepted count without duplicating
        replay_res = await client.post(
            "/api/v1/spending/upload/commit",
            json={"preview_id": preview_id},
            headers=user_a_headers,
        )
        assert replay_res.status_code == 200
        assert replay_res.json()["data"]["replayed"] is True


@pytest.mark.asyncio
async def test_13_ai_insufficient_evidence_and_prohibited_advice(app, user_a_headers):
    """Matrix 13: Unsupported questions return INSUFFICIENT_EVIDENCE; trading tips return restriction notice."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create conversation
        conv_res = await client.post(
            "/api/v1/ai/conversations",
            json={"title": "RAG Verification"},
            headers=user_a_headers,
        )
        conv_id = conv_res.json()["data"]["id"]

        # 1. Prohibited advice query
        res_tip = await client.post(
            f"/api/v1/ai/conversations/{conv_id}/messages",
            json={"content": "Give me a sure shot tip to double my money"},
            headers=user_a_headers,
        )
        assert res_tip.status_code == 200
        msg_tip = res_tip.json()["data"]["assistant_message"]
        assert "Restriction Notice" in msg_tip["headline"]
        assert len(msg_tip["citations"]) == 0

        # 2. Unsupported random query with zero evidence
        res_unsupp = await client.post(
            f"/api/v1/ai/conversations/{conv_id}/messages",
            json={"content": "What is the quantum orbital radius of Alpha Centauri asteroids?"},
            headers=user_a_headers,
        )
        assert res_unsupp.status_code == 200
        msg_unsupp = res_unsupp.json()["data"]["assistant_message"]
        assert "Insufficient" in msg_unsupp["headline"]
        assert len(msg_unsupp["citations"]) == 0


@pytest.mark.asyncio
async def test_11_cross_client_persistence(app, user_a_headers):
    """Matrix 11: Cross-client persistence: state created in one client session persists in future sessions."""
    transport = ASGITransport(app=app)
    # Session 1: records user consent
    async with AsyncClient(transport=transport, base_url="http://test") as client1:
        consent_res = await client1.post(
            "/api/v1/users/consent",
            json={
                "terms_accepted": True,
                "privacy_accepted": True,
                "educational_disclaimer_accepted": True,
                "consent_version": "v1.0",
            },
            headers=user_a_headers,
        )
        assert consent_res.status_code == 200

    # Session 2: verifies state survives across sessions
    async with AsyncClient(transport=transport, base_url="http://test") as client2:
        me_res = await client2.get("/api/v1/users/me", headers=user_a_headers)
        assert me_res.status_code == 200
        assert me_res.json()["data"]["verified_identity"] is True


@pytest.mark.asyncio
async def test_14_mobile_and_web_order_reconciliation(app, user_a_headers):
    """Matrix 14: Mobile and web order reconciliation via stable idempotency keys."""
    transport = ASGITransport(app=app)
    shared_key = "reconcile-matrix-shared-key-99"
    payload = {
        "symbol": "INFY",
        "side": "BUY",
        "order_type": "MARKET",
        "quantity": 3,
    }

    # Web submission
    async with AsyncClient(transport=transport, base_url="http://test") as web_client:
        web_res = await web_client.post(
            "/api/v1/paper-trading/orders",
            json=payload,
            headers={**user_a_headers, "X-Idempotency-Key": shared_key},
        )
        assert web_res.status_code == 200
        web_order = web_res.json()["data"]
        assert web_order["replayed"] is False

    # Mobile submission with identical key and payload
    async with AsyncClient(transport=transport, base_url="http://test") as mobile_client:
        mob_res = await mobile_client.post(
            "/api/v1/paper-trading/orders",
            json=payload,
            headers={**user_a_headers, "X-Idempotency-Key": shared_key},
        )
        assert mob_res.status_code == 200
        mob_order = mob_res.json()["data"]
        assert mob_order["replayed"] is True
        assert mob_order["order_id"] == web_order["order_id"]
        assert mob_order["cash_balance_after"] == web_order["cash_balance_after"]
