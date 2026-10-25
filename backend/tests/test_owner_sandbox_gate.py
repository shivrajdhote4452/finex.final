"""Tests for Login Identity Capture and Owner-Only Sandbox Visibility Gate.

Validates:
1. New customer login captures and stores verified name and email.
2. Existing customer backfills missing name/email without overwriting existing data with blank.
3. Owner login (shivrajdhote4452@gmail.com) has is_owner=True and full sandbox access.
4. Non-owner login has is_owner=False and is refused on sandbox endpoints with HTTP 403 Forbidden.
5. Logged out / unauthenticated requests fail closed with HTTP 401.
6. Helper is_owner fails closed on missing/empty config or invalid input, and handles case-insensitivity and whitespace.
"""

import pytest
from backend.app.config import get_settings
from backend.app.domain.user_store import user_store
from backend.app.factory import create_app
from backend.app.routers.auth import is_owner
from httpx import ASGITransport, AsyncClient


@pytest.fixture
def app():
    return create_app()


@pytest.fixture(scope="module", autouse=True)
def setup_module_db():
    import asyncio

    from backend.app.database import engine
    from backend.app.models.core import Base as CoreBase
    from backend.app.models.paper_trading import Base as PaperBase

    async def _init():
        async with engine.begin() as conn:
            await conn.run_sync(CoreBase.metadata.create_all)
            await conn.run_sync(PaperBase.metadata.create_all)

    asyncio.run(_init())
    yield


def test_is_owner_helper_truth_table(monkeypatch):
    """Verify is_owner helper is case-insensitive, trims whitespace, and fails closed."""
    monkeypatch.setenv("OWNER_EMAIL", "shivrajdhote4452@gmail.com")
    get_settings.cache_clear()

    # Positive matches
    assert is_owner("shivrajdhote4452@gmail.com") is True
    assert is_owner("  shivrajdhote4452@gmail.com  ") is True
    assert is_owner("SHIVRAJDHOTE4452@GMAIL.COM") is True
    assert is_owner("ShivrajDhote4452@Gmail.com") is True
    assert is_owner({"email": "shivrajdhote4452@gmail.com"}) is True
    assert is_owner({"email": "  SHIVRAJDHOTE4452@GMAIL.COM  "}) is True

    # Negative / Non-owner matches
    assert is_owner("other.investor@finex.internal") is False
    assert is_owner("customer@gmail.com") is False
    assert is_owner({"email": "customer@gmail.com"}) is False

    # Fail-closed cases: empty, missing, invalid
    assert is_owner("") is False
    assert is_owner("   ") is False
    assert is_owner(None) is False
    assert is_owner({}) is False
    assert is_owner({"email": None}) is False
    assert is_owner({"email": ""}) is False

    # Fail-closed when OWNER_EMAIL is unset or empty
    monkeypatch.setenv("OWNER_EMAIL", "")
    get_settings.cache_clear()
    assert is_owner("shivrajdhote4452@gmail.com") is False

    monkeypatch.setenv("OWNER_EMAIL", "   ")
    get_settings.cache_clear()
    assert is_owner("shivrajdhote4452@gmail.com") is False


@pytest.mark.asyncio
async def test_new_customer_registration_captures_name_and_email(app):
    """Case 1 & Task 1: New customer registration captures and persists name and email."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Dev-login as brand new customer
        login_res = await client.post(
            "/api/v1/auth/dev-login",
            json={
                "user_id": "usr-new-customer-999",
                "email": "priya.sharma@example.com",
                "name": "Priya Sharma",
            },
        )
        assert login_res.status_code == 200
        token_data = login_res.json()["data"]
        assert token_data["email"] == "priya.sharma@example.com"
        assert token_data["name"] == "Priya Sharma"

        token = token_data["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Check /users/me returns stored identity and is_owner=False
        me_res = await client.get("/api/v1/users/me", headers=headers)
        assert me_res.status_code == 200
        me_data = me_res.json()["data"]
        assert me_data["email"] == "priya.sharma@example.com"
        assert me_data["full_name"] == "Priya Sharma"
        assert me_data["display_name"] == "Priya"
        assert me_data["is_owner"] is False

        # Non-owner cannot call sandbox reset or deposit -> HTTP 403
        reset_res = await client.post(
            "/api/v1/paper-trading/reset",
            json={"confirm_reset": True},
            headers=headers,
        )
        assert reset_res.status_code == 403
        assert "owner" in reset_res.json()["detail"].lower()

        deposit_res = await client.post(
            "/api/v1/paper-trading/deposit",
            json={"amount": 25000.00},
            headers=headers,
        )
        assert deposit_res.status_code == 403
        assert "owner" in deposit_res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_existing_customer_backfills_missing_fields(app):
    """Task 1: Existing customer missing name or email backfills on subsequent login without overwriting."""
    # Seed user with missing/placeholder name and email
    uid = "usr-legacy-incomplete-01"
    user_store.get_or_create_user(
        provider="local_dev",
        provider_subject=f"dev-sub-{uid}",
        email="",
        name="",
        user_id=uid,
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Next login provides name and email
        login_res = await client.post(
            "/api/v1/auth/dev-login",
            json={
                "user_id": uid,
                "email": "rohit.verma@example.com",
                "name": "Rohit Verma",
            },
        )
        assert login_res.status_code == 200
        token_data = login_res.json()["data"]
        assert token_data["email"] == "rohit.verma@example.com"
        assert token_data["name"] == "Rohit Verma"

        # Check profile backfilled
        headers = {"Authorization": f"Bearer {token_data['access_token']}"}
        me_res = await client.get("/api/v1/users/me", headers=headers)
        assert me_res.status_code == 200
        me_data = me_res.json()["data"]
        assert me_data["email"] == "rohit.verma@example.com"
        assert me_data["full_name"] == "Rohit Verma"

        # Normal portfolio flow remains completely functional
        port_res = await client.get("/api/v1/portfolios/me", headers=headers)
        assert port_res.status_code == 200
        assert port_res.json()["data"]["user_id"] == uid


@pytest.mark.asyncio
async def test_owner_login_has_sandbox_access(app):
    """Case 3 & Task 2: Owner login (shivrajdhote4452@gmail.com) has full sandbox access."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Owner logs in
        login_res = await client.post(
            "/api/v1/auth/dev-login",
            json={
                "user_id": "usr-shivraj-001",
                "email": "shivrajdhote4452@gmail.com",
                "name": "Shivraj Dhote",
            },
        )
        assert login_res.status_code == 200
        token_data = login_res.json()["data"]
        assert token_data["email"] == "shivrajdhote4452@gmail.com"

        headers = {"Authorization": f"Bearer {token_data['access_token']}"}

        # Check /users/me reports is_owner=True
        me_res = await client.get("/api/v1/users/me", headers=headers)
        assert me_res.status_code == 200
        assert me_res.json()["data"]["is_owner"] is True

        # Owner CAN execute sandbox deposit -> HTTP 200
        dep_res = await client.post(
            "/api/v1/paper-trading/deposit",
            json={"amount": 50000.00},
            headers=headers,
        )
        assert dep_res.status_code == 200
        assert dep_res.json()["data"]["deposited"] == 50000.0

        # Owner CAN execute sandbox reset -> HTTP 200
        reset_res = await client.post(
            "/api/v1/paper-trading/reset",
            json={"confirm_reset": True},
            headers=headers,
        )
        assert reset_res.status_code == 200
        assert reset_res.json()["data"]["reset"] is True


@pytest.mark.asyncio
async def test_unauthenticated_requests_fail_closed(app):
    """Case 4: Unauthenticated or missing credentials return HTTP 401 Unauthorized."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res_reset = await client.post("/api/v1/paper-trading/reset", json={"confirm_reset": True})
        assert res_reset.status_code == 401

        res_deposit = await client.post("/api/v1/paper-trading/deposit", json={"amount": 25000.00})
        assert res_deposit.status_code == 401
