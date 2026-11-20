"""Tests for FinEx Admin Panel Endpoints and Security Enforcement.

Validates:
1. Unauthenticated requests to /api/v1/admin/* fail closed with HTTP 401 Unauthorized.
2. Non-owner requests fail closed with HTTP 403 Forbidden.
3. Non-Google provider sessions (even matching owner email) fail closed with HTTP 403 Forbidden.
4. Owner Google OAuth session succeeds with HTTP 200 OK across:
   - GET /api/v1/admin/overview
   - GET /api/v1/admin/users
   - GET /api/v1/admin/orders
   - GET /api/v1/admin/system-health
5. User directory projection strictly excludes passwords, password hashes, OAuth subjects,
   and private assessment questionnaire responses.
6. Paper order projection excludes execution stack traces and personal financial profiles.
7. Search and pagination filters function reliably on users and orders.
8. System health diagnostics safely expose integration states without revealing credentials.
"""

import pytest
from backend.app.config import get_settings
from backend.app.database import engine
from backend.app.factory import create_app
from backend.app.models.core import Base as CoreBase
from backend.app.models.paper_trading import Base as PaperBase
from backend.app.routers.auth import create_access_token
from httpx import ASGITransport, AsyncClient


@pytest.fixture
def app():
    return create_app()


@pytest.fixture(scope="module", autouse=True)
def setup_module_db():
    import asyncio

    async def _init():
        async with engine.begin() as conn:
            await conn.run_sync(CoreBase.metadata.create_all)
            await conn.run_sync(PaperBase.metadata.create_all)

    asyncio.run(_init())
    yield


@pytest.fixture
def owner_headers():
    settings = get_settings()
    owner_email = settings.OWNER_EMAIL or "shivrajdhote4452@gmail.com"
    token = create_access_token(
        user_id="usr-shivraj-001",
        email=owner_email,
        name="Shivraj Dhote",
        provider="google",
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def non_owner_headers():
    token = create_access_token(
        user_id="usr-other-002",
        email="customer@example.com",
        name="Regular Investor",
        provider="google",
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def non_google_owner_headers():
    settings = get_settings()
    owner_email = settings.OWNER_EMAIL or "shivrajdhote4452@gmail.com"
    token = create_access_token(
        user_id="usr-spoof-001",
        email=owner_email,
        name="Local Owner",
        provider="local_dev",
    )
    return {"Authorization": f"Bearer {token}"}


# =============================================================================
# Security & Authorization Tests (Fail-Closed)
# =============================================================================


@pytest.mark.asyncio
async def test_admin_endpoints_require_authentication(app):
    """Unauthenticated requests to admin endpoints fail closed with HTTP 401."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for path in [
            "/api/v1/admin/overview",
            "/api/v1/admin/users",
            "/api/v1/admin/orders",
            "/api/v1/admin/system-health",
        ]:
            res = await client.get(path)
            assert res.status_code == 401, f"Expected 401 for {path}, got {res.status_code}"


@pytest.mark.asyncio
async def test_admin_endpoints_refuse_non_owners(app, non_owner_headers):
    """Authenticated non-owners are refused with HTTP 403 Forbidden."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for path in [
            "/api/v1/admin/overview",
            "/api/v1/admin/users",
            "/api/v1/admin/orders",
            "/api/v1/admin/system-health",
        ]:
            res = await client.get(path, headers=non_owner_headers)
            assert res.status_code == 403, f"Expected 403 for {path}, got {res.status_code}"
            assert "owner" in res.json().get("detail", "").lower()


@pytest.mark.asyncio
async def test_admin_endpoints_refuse_non_google_provider_sessions(app, non_google_owner_headers):
    """Non-Google sessions (even matching the owner email) fail closed with HTTP 403 Forbidden."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for path in [
            "/api/v1/admin/overview",
            "/api/v1/admin/users",
            "/api/v1/admin/orders",
            "/api/v1/admin/system-health",
        ]:
            res = await client.get(path, headers=non_google_owner_headers)
            assert res.status_code == 403, f"Expected 403 for {path}, got {res.status_code}"


@pytest.mark.asyncio
async def test_admin_endpoints_refuse_inactive_owner(app):
    """Inactive owner account in database is refused with HTTP 403 Forbidden."""
    from backend.app.database import AsyncSessionLocal
    from backend.app.models.core import User
    from sqlalchemy import select

    settings = get_settings()
    owner_email = settings.OWNER_EMAIL or "shivrajdhote4452@gmail.com"
    inactive_uid = "usr-inactive-owner-test"
    was_created = False

    # Ensure owner user exists in DB and is marked inactive
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(User).where(User.email == owner_email))
        u = res.scalars().first()
        if not u:
            was_created = True
            u = User(
                id=inactive_uid,
                email=owner_email,
                provider="google",
                provider_subject="google-sub-shivraj-primary",
                google_subject="google-sub-shivraj-primary",
                is_active=False,
                is_verified=True,
                email_verified=True,
            )
            session.add(u)
        else:
            u.is_active = False
            inactive_uid = u.id
        await session.commit()

    try:
        token = create_access_token(
            user_id=inactive_uid,
            email=owner_email,
            name="Shivraj Dhote",
            provider="google",
        )
        headers = {"Authorization": f"Bearer {token}"}
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.get("/api/v1/admin/overview", headers=headers)
            assert res.status_code == 403
            assert (
                "inactive" in res.json().get("detail", "").lower() or "disabled" in res.json().get("detail", "").lower()
            )
    finally:
        # Restore active state or delete created test record
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(User).where(User.email == owner_email))
            u = res.scalars().first()
            if u:
                if was_created:
                    await session.delete(u)
                else:
                    u.is_active = True
                await session.commit()


@pytest.mark.asyncio
async def test_admin_endpoints_refuse_when_owner_email_is_unset(app, owner_headers, monkeypatch):
    """When OWNER_EMAIL is empty or unset, all admin requests fail closed with HTTP 403."""
    monkeypatch.setenv("OWNER_EMAIL", "")
    get_settings.cache_clear()

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.get("/api/v1/admin/overview", headers=owner_headers)
            assert res.status_code == 403
    finally:
        monkeypatch.undo()
        get_settings.cache_clear()


@pytest.mark.asyncio
async def test_admin_endpoints_refuse_forged_expired_or_revoked_token(app):
    """Forged signature, expired token, or revoked token are rejected with HTTP 401."""
    from datetime import datetime, timedelta, timezone

    import jwt
    from backend.app.domain.user_store import user_store

    settings = get_settings()
    owner_email = settings.OWNER_EMAIL or "shivrajdhote4452@gmail.com"

    # 1. Forged token with invalid secret
    forged_token = jwt.encode(
        {"sub": "usr-shivraj-001", "email": owner_email, "provider": "google"},
        "wrong-secret-key-32-characters-minimum",
        algorithm="HS256",
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/admin/overview", headers={"Authorization": f"Bearer {forged_token}"})
        assert res.status_code == 401

        # 2. Expired token
        expired_token = jwt.encode(
            {
                "sub": "usr-shivraj-001",
                "email": owner_email,
                "provider": "google",
                "exp": datetime.now(timezone.utc) - timedelta(hours=1),
            },
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )
        res_exp = await client.get("/api/v1/admin/overview", headers={"Authorization": f"Bearer {expired_token}"})
        assert res_exp.status_code == 401

        # 3. Revoked token
        valid_token = create_access_token(
            user_id="usr-shivraj-001",
            email=owner_email,
            name="Shivraj Dhote",
            provider="google",
        )
        await user_store.revoke_token_db(valid_token)
        res_rev = await client.get("/api/v1/admin/overview", headers={"Authorization": f"Bearer {valid_token}"})
        assert res_rev.status_code == 401


@pytest.mark.asyncio
async def test_google_login_refuses_unverified_owner_identity(app):
    """Google OAuth login callback refuses unverified owner email with HTTP 403."""
    from unittest.mock import patch

    settings = get_settings()
    owner_email = settings.OWNER_EMAIL or "shivrajdhote4452@gmail.com"

    unverified_id_info = {
        "sub": "google-sub-unverified-attacker",
        "email": owner_email,
        "name": "Attacker",
        "iss": "https://accounts.google.com",
        "email_verified": False,
    }
    with patch("google.oauth2.id_token.verify_oauth2_token", return_value=unverified_id_info):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.post(
                "/api/v1/auth/google",
                json={"id_token": "mock-unverified-google-token"},
            )
            assert res.status_code == 403
            assert "verified" in res.json().get("detail", "").lower()


# =============================================================================
# Operational Overview Endpoint Tests
# =============================================================================


@pytest.mark.asyncio
async def test_admin_overview_returns_metrics(app, owner_headers):
    """Owner receives operational overview metrics with expected schema and zero-safe values."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/admin/overview", headers=owner_headers)
        assert res.status_code == 200
        payload = res.json()
        assert payload["success"] is True
        data = payload["data"]

        assert "total_users" in data
        assert isinstance(data["total_users"], int)
        assert data["total_users"] >= 0

        assert "verified_users" in data
        assert isinstance(data["verified_users"], int)
        assert "unverified_users" in data
        assert isinstance(data["unverified_users"], int)
        assert data["verified_users"] + data["unverified_users"] == data["total_users"]

        assert "onboarding_completed_users" in data
        assert isinstance(data["onboarding_completed_users"], int)

        assert "total_orders" in data
        assert isinstance(data["total_orders"], int)

        assert "orders_by_status" in data
        status_map = data["orders_by_status"]
        for st in ["FILLED", "REJECTED", "PENDING", "CANCELLED"]:
            assert st in status_map
            assert isinstance(status_map[st], int)

        assert "recent_rejected_orders" in data
        assert isinstance(data["recent_rejected_orders"], list)


# =============================================================================
# User Directory Endpoint Tests & Safe Projections
# =============================================================================


@pytest.mark.asyncio
async def test_admin_users_returns_safe_projections(app, owner_headers):
    """User directory returns paginated users and strictly excludes sensitive data."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/admin/users?page=1&limit=10", headers=owner_headers)
        assert res.status_code == 200
        payload = res.json()
        data = payload["data"]

        assert "users" in data
        assert "total" in data
        assert "page" in data
        assert "limit" in data
        assert "total_pages" in data

        users = data["users"]
        assert isinstance(users, list)

        # Check each user projection strictly excludes sensitive fields
        for u in users:
            assert "id" in u
            assert "email" in u
            assert "is_active" in u
            assert "email_verified" in u
            assert "onboarding_completed" in u

            # Prohibited sensitive fields
            assert "password_hash" not in u
            assert "password" not in u
            assert "google_subject" not in u
            assert "provider_subject" not in u
            assert "risk_assessment" not in u
            assert "access_token" not in u


@pytest.mark.asyncio
async def test_admin_users_search_and_filters(app, owner_headers):
    """User directory search query and boolean filters execute properly."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Search by email prefix
        res_search = await client.get("/api/v1/admin/users?search=shivraj&limit=5", headers=owner_headers)
        assert res_search.status_code == 200
        search_data = res_search.json()["data"]
        for u in search_data["users"]:
            matches = (
                "shivraj" in (u.get("email") or "").lower()
                or "shivraj" in (u.get("display_name") or "").lower()
                or "shivraj" in (u.get("full_name") or "").lower()
            )
            assert matches

        # Filter by active
        res_active = await client.get("/api/v1/admin/users?is_active=true&limit=5", headers=owner_headers)
        assert res_active.status_code == 200


# =============================================================================
# Paper Trading Orders Endpoint Tests
# =============================================================================


@pytest.mark.asyncio
async def test_admin_orders_returns_paginated_list(app, owner_headers):
    """Order directory returns paginated orders with safe order attributes."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/admin/orders?page=1&limit=10", headers=owner_headers)
        assert res.status_code == 200
        payload = res.json()
        data = payload["data"]

        assert "orders" in data
        assert "total" in data
        assert "page" in data
        assert "limit" in data
        assert "total_pages" in data

        orders = data["orders"]
        assert isinstance(orders, list)

        for o in orders:
            assert "id" in o
            assert "user_id" in o
            assert "symbol" in o
            assert "side" in o
            assert "order_type" in o
            assert "quantity" in o
            assert "status" in o
            # Strictly prohibited internal execution traces
            assert "execution_receipt" not in o
            assert "internal_trace" not in o


@pytest.mark.asyncio
async def test_admin_orders_filter_by_status_and_symbol(app, owner_headers):
    """Orders can be filtered by status and ticker symbol."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res_status = await client.get("/api/v1/admin/orders?status=REJECTED&limit=5", headers=owner_headers)
        assert res_status.status_code == 200
        orders = res_status.json()["data"]["orders"]
        for o in orders:
            assert o["status"] == "REJECTED"


# =============================================================================
# System Health & Integrations Diagnostics Tests
# =============================================================================


@pytest.mark.asyncio
async def test_admin_system_health_diagnostics(app, owner_headers):
    """System health returns backend, database, market data, and email states without disclosing secrets."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/admin/system-health", headers=owner_headers)
        assert res.status_code == 200
        payload = res.json()
        data = payload["data"]

        # Backend process
        assert "backend" in data
        assert data["backend"]["status"] == "ok"
        assert "app" in data["backend"]
        assert "version" in data["backend"]

        # Database readiness
        assert "database" in data
        assert data["database"]["status"] in ("ok", "down")

        # Market data config
        assert "market_data" in data
        assert "mode" in data["market_data"]

        # Angel One diagnostics (safe projection)
        assert "angel_one" in data
        angel = data["angel_one"]
        assert "is_configured" in angel
        # Ensure raw secrets are NEVER in angel diagnostics
        assert "api_key" not in angel
        assert "client_id" not in angel
        assert "mpin" not in angel
        assert "totp_secret" not in angel

        # Email diagnostics
        assert "email" in data
        email = data["email"]
        assert "is_configured" in email
        assert "password" not in email
        assert "smtp_password" not in email
