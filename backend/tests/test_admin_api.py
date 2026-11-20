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

from unittest.mock import patch

import pytest
from backend.app.config import get_settings
from backend.app.database import AsyncSessionLocal, engine
from backend.app.factory import create_app
from backend.app.models.core import Base as CoreBase
from backend.app.models.core import User
from backend.app.models.paper_trading import (
    Base as PaperBase,
)
from backend.app.models.paper_trading import (
    PaperAccount,
    PaperCashLedger,
    PaperOrder,
    PaperPosition,
)
from backend.app.routers.auth import create_access_token
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select


@pytest.fixture
def app():
    return create_app()


@pytest.fixture(scope="module", autouse=True)
def setup_module_db():
    import asyncio

    from backend.app.domain.user_store import user_store

    async def _init():
        async with engine.begin() as conn:
            await conn.run_sync(CoreBase.metadata.create_all)
            await conn.run_sync(PaperBase.metadata.create_all)
        await user_store.ensure_seed_users_db()

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


ADMIN_PATHS = [
    "/api/v1/admin/overview",
    "/api/v1/admin/users",
    "/api/v1/admin/orders",
    "/api/v1/admin/system-health",
]


# =============================================================================
# Security & Authorization Tests (Fail-Closed)
# =============================================================================


@pytest.mark.asyncio
async def test_admin_endpoints_require_authentication(app):
    """Unauthenticated requests to admin endpoints fail closed with HTTP 401."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for path in ADMIN_PATHS:
            res = await client.get(path)
            assert res.status_code == 401, f"Expected 401 for {path}, got {res.status_code}"


@pytest.mark.asyncio
async def test_admin_endpoints_refuse_non_owners(app, non_owner_headers):
    """Authenticated non-owners are refused with HTTP 403 Forbidden across all admin endpoints."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for path in ADMIN_PATHS:
            res = await client.get(path, headers=non_owner_headers)
            assert res.status_code == 403, f"Expected 403 for {path}, got {res.status_code}"
            assert "owner" in res.json().get("detail", "").lower()


@pytest.mark.asyncio
async def test_admin_endpoints_refuse_non_google_provider_sessions(app, non_google_owner_headers):
    """Non-Google sessions (even matching owner email) fail closed with HTTP 403 across all admin endpoints."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for path in ADMIN_PATHS:
            res = await client.get(path, headers=non_google_owner_headers)
            assert res.status_code == 403, f"Expected 403 for {path}, got {res.status_code}"


@pytest.mark.asyncio
async def test_admin_endpoints_refuse_missing_user_in_db(app):
    """Owner token referencing a non-existent database user is denied with HTTP 403 across all admin endpoints."""
    settings = get_settings()
    owner_email = settings.OWNER_EMAIL or "shivrajdhote4452@gmail.com"
    ghost_token = create_access_token(
        user_id="usr-ghost-missing-owner-999",
        email=owner_email,
        name="Ghost Owner",
        provider="google",
    )
    headers = {"Authorization": f"Bearer {ghost_token}"}
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for path in ADMIN_PATHS:
            res = await client.get(path, headers=headers)
            assert res.status_code == 403, f"Expected 403 for {path}, got {res.status_code}"
            assert "not found" in res.json().get("detail", "").lower()


@pytest.mark.asyncio
async def test_admin_endpoints_refuse_inactive_owner(app):
    """Inactive owner account in database is refused with HTTP 403 Forbidden across all admin endpoints."""
    from backend.app.database import AsyncSessionLocal
    from backend.app.models.core import User
    from sqlalchemy import select

    settings = get_settings()
    owner_email = settings.OWNER_EMAIL or "shivrajdhote4452@gmail.com"
    owner_uid = "usr-shivraj-001"

    # Ensure canonical owner user exists in DB and is marked inactive
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(User).where(User.id == owner_uid))
        u = res.scalars().first()
        if not u:
            u = User(
                id=owner_uid,
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
            u.email_verified = True
            u.is_verified = True
            u.google_subject = "google-sub-shivraj-primary"
        await session.commit()

    try:
        token = create_access_token(
            user_id=owner_uid,
            email=owner_email,
            name="Shivraj Dhote",
            provider="google",
        )
        headers = {"Authorization": f"Bearer {token}"}
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            for path in ADMIN_PATHS:
                res = await client.get(path, headers=headers)
                assert res.status_code == 403, f"Expected 403 for {path}, got {res.status_code}"
                detail = res.json().get("detail", "").lower()
                assert "inactive" in detail or "disabled" in detail
    finally:
        # Restore active state and canonical google_subject
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(User).where(User.id == owner_uid))
            u = res.scalars().first()
            if u:
                u.is_active = True
                u.email_verified = True
                u.is_verified = True
                u.google_subject = "google-sub-shivraj-primary"
                await session.commit()


@pytest.mark.asyncio
async def test_admin_endpoints_refuse_unverified_owner_db_identity(app):
    """Owner account in DB with unverified email/identity is refused with HTTP 403 across all admin endpoints."""
    from backend.app.database import AsyncSessionLocal
    from backend.app.models.core import User
    from sqlalchemy import select

    settings = get_settings()
    owner_email = settings.OWNER_EMAIL or "shivrajdhote4452@gmail.com"
    owner_uid = "usr-shivraj-001"

    # Set owner unverified in DB
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(User).where(User.id == owner_uid))
        u = res.scalars().first()
        if u:
            u.email_verified = False
            u.is_verified = False
            await session.commit()

    try:
        token = create_access_token(
            user_id=owner_uid,
            email=owner_email,
            name="Shivraj Dhote",
            provider="google",
        )
        headers = {"Authorization": f"Bearer {token}"}
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            for path in ADMIN_PATHS:
                res = await client.get(path, headers=headers)
                assert res.status_code == 403, f"Expected 403 for {path}, got {res.status_code}"
                assert "unverified" in res.json().get("detail", "").lower()
    finally:
        # Restore verified state
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(User).where(User.id == owner_uid))
            u = res.scalars().first()
            if u:
                u.email_verified = True
                u.is_verified = True
                await session.commit()


@pytest.mark.asyncio
async def test_admin_endpoints_refuse_mismatched_db_identity(app):
    """Token email or provider that does not match database user record is refused with HTTP 403."""
    from backend.app.database import AsyncSessionLocal
    from backend.app.models.core import User
    from sqlalchemy import select

    settings = get_settings()
    owner_email = settings.OWNER_EMAIL or "shivrajdhote4452@gmail.com"
    owner_uid = "usr-shivraj-001"

    # Case 1: Token email does not match user's actual database email
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(User).where(User.id == owner_uid))
        u = res.scalars().first()
        if u:
            u.email = "mismatched.address@finex.internal"
            await session.commit()

    try:
        token = create_access_token(
            user_id=owner_uid,
            email=owner_email,
            name="Shivraj Dhote",
            provider="google",
        )
        headers = {"Authorization": f"Bearer {token}"}
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.get("/api/v1/admin/overview", headers=headers)
            assert res.status_code == 403
            assert "match" in res.json().get("detail", "").lower()
    finally:
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(User).where(User.id == owner_uid))
            u = res.scalars().first()
            if u:
                u.email = owner_email
                await session.commit()


@pytest.mark.asyncio
async def test_admin_endpoints_refuse_when_owner_email_is_unset(app, owner_headers, monkeypatch):
    """When OWNER_EMAIL is empty or unset, all admin requests fail closed with HTTP 403."""
    monkeypatch.setenv("OWNER_EMAIL", "")
    get_settings.cache_clear()

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            for path in ADMIN_PATHS:
                res = await client.get(path, headers=owner_headers)
                assert res.status_code == 403, f"Expected 403 for {path}, got {res.status_code}"
    finally:
        monkeypatch.undo()
        get_settings.cache_clear()


@pytest.mark.asyncio
async def test_admin_endpoints_refuse_forged_expired_or_revoked_token(app):
    """Forged signature, expired token, or revoked token are rejected with HTTP 401 across all admin endpoints."""
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
        for path in ADMIN_PATHS:
            res = await client.get(path, headers={"Authorization": f"Bearer {forged_token}"})
            assert res.status_code == 401, f"Expected 401 for {path}, got {res.status_code}"

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
        for path in ADMIN_PATHS:
            res_exp = await client.get(path, headers={"Authorization": f"Bearer {expired_token}"})
            assert res_exp.status_code == 401, f"Expected 401 for {path}, got {res_exp.status_code}"

        # 3. Revoked token
        valid_token = create_access_token(
            user_id="usr-shivraj-001",
            email=owner_email,
            name="Shivraj Dhote",
            provider="google",
        )
        await user_store.revoke_token_db(valid_token)
        for path in ADMIN_PATHS:
            res_rev = await client.get(path, headers={"Authorization": f"Bearer {valid_token}"})
            assert res_rev.status_code == 401, f"Expected 401 for {path}, got {res_rev.status_code}"


@pytest.mark.asyncio
async def test_google_login_owner_email_verified_truth_table(app):
    """Google OAuth callback truth table for owner login: fails closed unless explicitly verified.

    Validates:
    - Missing email_verified claim: rejected with HTTP 403, no DB user created/linked.
    - False email_verified claim: rejected with HTTP 403, no DB user created/linked.
    - Malformed claims ('unverified', 'false', '', 123, []): rejected with HTTP 403, no DB user created/linked.
    - True email_verified claim (True, 'true'): succeeds with HTTP 200 and issues token.
    """
    from unittest.mock import patch

    from backend.app.database import AsyncSessionLocal
    from backend.app.models.core import User
    from sqlalchemy import select

    settings = get_settings()
    owner_email = settings.OWNER_EMAIL or "shivrajdhote4452@gmail.com"
    transport = ASGITransport(app=app)

    # 1. Missing email_verified claim
    sub_missing = "google-sub-missing-claim-test"
    info_missing = {
        "iss": "https://accounts.google.com",
        "sub": sub_missing,
        "email": owner_email,
        "name": "Attacker Missing Claim",
        # Notice: no 'email_verified' key
    }
    with patch("google.oauth2.id_token.verify_oauth2_token", return_value=info_missing):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.post("/api/v1/auth/google", json={"id_token": "token-missing-ver"})
            assert res.status_code == 403
            assert "verified" in res.json().get("detail", "").lower()

    # Verify no DB identity was persisted or linked for this subject
    async with AsyncSessionLocal() as session:
        res_db = await session.execute(select(User).where(User.provider_subject == sub_missing))
        assert res_db.scalars().first() is None

    # 2. Explicit False email_verified claim
    sub_false = "google-sub-false-claim-test"
    info_false = {
        "iss": "https://accounts.google.com",
        "sub": sub_false,
        "email": owner_email,
        "name": "Attacker False Claim",
        "email_verified": False,
    }
    with patch("google.oauth2.id_token.verify_oauth2_token", return_value=info_false):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.post("/api/v1/auth/google", json={"id_token": "token-false-ver"})
            assert res.status_code == 403
            assert "verified" in res.json().get("detail", "").lower()

    async with AsyncSessionLocal() as session:
        res_db = await session.execute(select(User).where(User.provider_subject == sub_false))
        assert res_db.scalars().first() is None

    # 3. Malformed email_verified claims
    malformed_variants = ["unverified", "false", "", 123, [], {"status": "ok"}]
    for idx, malformed_val in enumerate(malformed_variants):
        sub_mal = f"google-sub-malformed-{idx}"
        info_mal = {
            "iss": "https://accounts.google.com",
            "sub": sub_mal,
            "email": owner_email,
            "name": f"Attacker Malformed {idx}",
            "email_verified": malformed_val,
        }
        with patch("google.oauth2.id_token.verify_oauth2_token", return_value=info_mal):
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                res = await client.post("/api/v1/auth/google", json={"id_token": f"token-mal-{idx}"})
                assert res.status_code == 403, (
                    f"Expected 403 for malformed value {malformed_val!r}, got {res.status_code}"
                )
                assert "verified" in res.json().get("detail", "").lower()

        async with AsyncSessionLocal() as session:
            res_db = await session.execute(select(User).where(User.provider_subject == sub_mal))
            assert res_db.scalars().first() is None

    # 4. Valid True email_verified (boolean True)
    info_true = {
        "iss": "https://accounts.google.com",
        "sub": "google-sub-shivraj-primary",
        "email": owner_email,
        "name": "Shivraj Dhote",
        "email_verified": True,
    }
    with patch("google.oauth2.id_token.verify_oauth2_token", return_value=info_true):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.post("/api/v1/auth/google", json={"id_token": "token-true-ver"})
            assert res.status_code == 200
            assert res.json()["data"]["email"] == owner_email

    # 5. Valid True email_verified (string "true")
    info_str_true = {
        "iss": "https://accounts.google.com",
        "sub": "google-sub-shivraj-primary",
        "email": owner_email,
        "name": "Shivraj Dhote",
        "email_verified": "true",
    }
    with patch("google.oauth2.id_token.verify_oauth2_token", return_value=info_str_true):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.post("/api/v1/auth/google", json={"id_token": "token-str-true-ver"})
            assert res.status_code == 200


@pytest.mark.asyncio
async def test_authorized_owner_accesses_all_admin_endpoints(app, owner_headers):
    """Authorized owner with verified Google identity accesses all admin endpoints successfully."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for path in ADMIN_PATHS:
            res = await client.get(path, headers=owner_headers)
            assert res.status_code == 200, f"Expected 200 for {path}, got {res.status_code}: {res.text}"
            assert res.json()["success"] is True


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


# =============================================================================
# Legitimate Google and Email Login Regression Tests
# =============================================================================


@pytest.mark.asyncio
async def test_legitimate_google_and_email_login_flows(app):
    """Verify that legitimate Google (customer + owner) and email/password flows succeed."""
    import uuid
    from unittest.mock import patch

    settings = get_settings()
    owner_email = settings.OWNER_EMAIL or "shivrajdhote4452@gmail.com"
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Customer Google login with verified email
        customer_id_info = {
            "iss": "https://accounts.google.com",
            "sub": "google-sub-customer-valid-001",
            "email": "customer.valid@example.com",
            "name": "Valid Customer",
            "email_verified": True,
        }
        with patch("google.oauth2.id_token.verify_oauth2_token", return_value=customer_id_info):
            res_cust = await client.post("/api/v1/auth/google", json={"id_token": "token-valid-customer"})
            assert res_cust.status_code == 200
            cust_data = res_cust.json()["data"]
            assert cust_data["email"] == "customer.valid@example.com"
            assert "access_token" in cust_data

        # 2. Owner Google login with verified email
        owner_id_info = {
            "iss": "https://accounts.google.com",
            "sub": "google-sub-shivraj-primary",
            "email": owner_email,
            "name": "Shivraj Dhote",
            "email_verified": True,
        }
        with patch("google.oauth2.id_token.verify_oauth2_token", return_value=owner_id_info):
            res_owner = await client.post("/api/v1/auth/google", json={"id_token": "token-valid-owner"})
            assert res_owner.status_code == 200, f"res_owner status={res_owner.status_code}, body={res_owner.text}"
            owner_data = res_owner.json()["data"]
            assert owner_data["email"] == owner_email
            assert "access_token" in owner_data

        # 3. Email/Password signup and verified login
        test_email = f"legit_investor_{uuid.uuid4().hex[:8]}@finex.internal"
        signup_res = await client.post(
            "/api/v1/auth/signup",
            json={
                "email": test_email,
                "password": "SecurePassword123!",
                "name": "Legit Investor",
            },
        )
        assert signup_res.status_code == 200
        assert signup_res.json()["data"]["sent"] is True

        # Consume verification token in test mode
        from backend.app.database import AsyncSessionLocal
        from backend.app.models.core import User
        from sqlalchemy import select

        async with AsyncSessionLocal() as session:
            res_u = await session.execute(select(User).where(User.email == test_email))
            u = res_u.scalars().first()
            assert u is not None
            u.email_verified = True
            u.is_verified = True
            await session.commit()

        login_res = await client.post(
            "/api/v1/auth/login",
            json={
                "email": test_email,
                "password": "SecurePassword123!",
            },
        )
        assert login_res.status_code == 200
        assert "access_token" in login_res.json()["data"]


@pytest.mark.asyncio
async def test_admin_google_login_truth_table_and_enforcement(app):
    """Verifies POST /api/v1/auth/admin-google strictly authorizes only the verified owner."""
    settings = get_settings()
    owner_email = (settings.OWNER_EMAIL or "shivrajdhote4452@gmail.com").strip().lower()
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Non-owner Google login must fail closed with 403 Forbidden
        with patch("google.oauth2.id_token.verify_oauth2_token") as mock_verify:
            mock_verify.return_value = {
                "iss": "https://accounts.google.com",
                "sub": "non-owner-google-sub-999",
                "email": "intruder@gmail.com",
                "name": "Intruder User",
                "email_verified": True,
            }
            res_intruder = await client.post(
                "/api/v1/auth/admin-google",
                json={"id_token": "mock-intruder-id-token"},
            )
            assert res_intruder.status_code == 403
            assert "restricted to the platform owner" in res_intruder.json()["detail"]

        # 2. Owner with unverified email must fail closed with 403 Forbidden
        with patch("google.oauth2.id_token.verify_oauth2_token") as mock_verify:
            mock_verify.return_value = {
                "iss": "https://accounts.google.com",
                "sub": "owner-google-sub-unverified",
                "email": owner_email,
                "name": "Shivraj Dhote",
                "email_verified": False,
            }
            res_unverified = await client.post(
                "/api/v1/auth/admin-google",
                json={"id_token": "mock-unverified-id-token"},
            )
            assert res_unverified.status_code == 403
            assert "Owner access requires a verified Google account" in res_unverified.json()["detail"]

        # 3. Missing owner account in DB fails closed with 403 without creating a user
        with patch.object(settings, "OWNER_EMAIL", "nonexistent_owner@finex.internal"):
            with patch("google.oauth2.id_token.verify_oauth2_token") as mock_verify:
                mock_verify.return_value = {
                    "iss": "https://accounts.google.com",
                    "sub": "nonexistent-google-sub-123",
                    "email": "nonexistent_owner@finex.internal",
                    "name": "Missing Owner",
                    "email_verified": True,
                }
                res_missing = await client.post(
                    "/api/v1/auth/admin-google",
                    json={"id_token": "mock-missing-owner-token"},
                )
                assert res_missing.status_code == 403
                assert "not found in database" in res_missing.json()["detail"]

                # Verify NO user was inserted into DB for nonexistent_owner@finex.internal
                async with AsyncSessionLocal() as session:
                    res_chk = await session.execute(
                        select(User).where(User.email == "nonexistent_owner@finex.internal")
                    )
                    assert res_chk.scalar_one_or_none() is None

        # 4. Mismatched Google subject fails closed with 403 without modifying account
        async with AsyncSessionLocal() as session:
            res_u = await session.execute(select(User).where(User.email == owner_email))
            owner_u = res_u.scalar_one_or_none()
            assert owner_u is not None
            # Set a persistent real Google subject
            owner_u.google_subject = "real-persistent-owner-google-sub-123"
            await session.commit()

        with patch("google.oauth2.id_token.verify_oauth2_token") as mock_verify:
            mock_verify.return_value = {
                "iss": "https://accounts.google.com",
                "sub": "attacker-mismatched-google-sub-999",
                "email": owner_email,
                "name": "Shivraj Dhote",
                "email_verified": True,
            }
            res_mismatch = await client.post(
                "/api/v1/auth/admin-google",
                json={"id_token": "mock-mismatched-token"},
            )
            assert res_mismatch.status_code == 403
            assert "Google subject mismatch" in res_mismatch.json()["detail"]

            # Verify google_subject in DB was NOT updated or relinked
            async with AsyncSessionLocal() as session:
                res_chk = await session.execute(select(User).where(User.email == owner_email))
                chk_u = res_chk.scalar_one_or_none()
                assert chk_u.google_subject == "real-persistent-owner-google-sub-123"

        # 5. Inactive owner in DB fails closed with 403
        async with AsyncSessionLocal() as session:
            res_u = await session.execute(select(User).where(User.email == owner_email))
            owner_u = res_u.scalar_one_or_none()
            owner_u.is_active = False
            await session.commit()

        with patch("google.oauth2.id_token.verify_oauth2_token") as mock_verify:
            mock_verify.return_value = {
                "iss": "https://accounts.google.com",
                "sub": "real-persistent-owner-google-sub-123",
                "email": owner_email,
                "name": "Shivraj Dhote",
                "email_verified": True,
            }
            res_inactive = await client.post(
                "/api/v1/auth/admin-google",
                json={"id_token": "mock-owner-token"},
            )
            assert res_inactive.status_code == 403
            assert "disabled" in res_inactive.json()["detail"]

        # 6. Unverified owner in DB fails closed with 403
        async with AsyncSessionLocal() as session:
            res_u = await session.execute(select(User).where(User.email == owner_email))
            owner_u = res_u.scalar_one_or_none()
            owner_u.is_active = True
            owner_u.is_verified = False
            owner_u.email_verified = False
            await session.commit()

        with patch("google.oauth2.id_token.verify_oauth2_token") as mock_verify:
            mock_verify.return_value = {
                "iss": "https://accounts.google.com",
                "sub": "real-persistent-owner-google-sub-123",
                "email": owner_email,
                "name": "Shivraj Dhote",
                "email_verified": True,
            }
            res_unver_db = await client.post(
                "/api/v1/auth/admin-google",
                json={"id_token": "mock-owner-token"},
            )
            assert res_unver_db.status_code == 403
            assert "unverified" in res_unver_db.json()["detail"]

        # Restore verified active owner state for authorized test
        async with AsyncSessionLocal() as session:
            res_u = await session.execute(select(User).where(User.email == owner_email))
            owner_u = res_u.scalar_one_or_none()
            owner_u.is_active = True
            owner_u.is_verified = True
            owner_u.email_verified = True
            owner_u.google_subject = "real-persistent-owner-google-sub-123"
            await session.commit()

        # 7. Legitimate verified owner Google login succeeds with 200 OK
        with patch("google.oauth2.id_token.verify_oauth2_token") as mock_verify:
            mock_verify.return_value = {
                "iss": "https://accounts.google.com",
                "sub": "real-persistent-owner-google-sub-123",
                "email": owner_email,
                "name": "Shivraj Dhote",
                "email_verified": True,
            }
            res_owner = await client.post(
                "/api/v1/auth/admin-google",
                json={"id_token": "mock-authorized-id-token"},
            )
            assert res_owner.status_code == 200, f"res_owner status={res_owner.status_code}, body={res_owner.text}"
            data = res_owner.json()["data"]
            assert data["email"] == owner_email
            assert "access_token" in data


@pytest.mark.asyncio
async def test_admin_me_endpoint(app, owner_headers):
    """Verifies GET /api/v1/admin/me returns owner details and rejects non-owners."""
    transport = ASGITransport(app=app)
    settings = get_settings()
    owner_email = (settings.OWNER_EMAIL or "shivrajdhote4452@gmail.com").strip().lower()

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Unauthenticated -> 401
        res_unauth = await client.get("/api/v1/admin/me")
        assert res_unauth.status_code == 401

        # 2. Non-owner -> 403
        non_owner_token = create_access_token(
            user_id="usr-regular-001",
            email="regular@finex.internal",
            name="Regular User",
            provider="google",
        )
        res_non_owner = await client.get(
            "/api/v1/admin/me",
            headers={"Authorization": f"Bearer {non_owner_token}"},
        )
        assert res_non_owner.status_code == 403

        # 3. Authorized Owner -> 200 OK
        res_owner = await client.get("/api/v1/admin/me", headers=owner_headers)
        assert res_owner.status_code == 200
        data = res_owner.json()["data"]
        assert data["email"] == owner_email
        assert data["role"] == "owner"
        assert data["is_active"] is True
        assert data["email_verified"] is True


@pytest.mark.asyncio
async def test_admin_login_logout_preserves_owner_portfolio_and_investor_session(app):
    """Verifies admin login/logout strictly preserves owner portfolio, orders, ledger, and investor session."""
    import uuid

    settings = get_settings()
    owner_email = (settings.OWNER_EMAIL or "shivrajdhote4452@gmail.com").strip().lower()
    owner_uid = "usr-shivraj-001"
    transport = ASGITransport(app=app)

    # 1. Setup known portfolio, order, and ledger in isolated test database
    async with AsyncSessionLocal() as session:
        # Ensure user exists
        res_u = await session.execute(select(User).where(User.id == owner_uid))
        u = res_u.scalar_one_or_none()
        if not u:
            u = User(
                id=owner_uid,
                email=owner_email,
                name="Shivraj Dhote",
                provider="google",
                provider_subject="owner-google-sub-authorized",
                google_subject="owner-google-sub-authorized",
                is_active=True,
                is_verified=True,
                email_verified=True,
            )
            session.add(u)
            await session.flush()
        else:
            u.is_active = True
            u.is_verified = True
            u.email_verified = True
            u.google_subject = "owner-google-sub-authorized"
            await session.flush()

        # Ensure paper account exists with known cash balance
        res_acc = await session.execute(select(PaperAccount).where(PaperAccount.user_id == owner_uid))
        acc = res_acc.scalar_one_or_none()
        if not acc:
            acc = PaperAccount(
                id=f"acc-{uuid.uuid4().hex[:12]}",
                user_id=owner_uid,
                account_number="ACC-OWNER-TEST",
                current_cash=85000.0,
                currency="INR",
            )
            session.add(acc)
            await session.flush()
        else:
            acc.current_cash = 85000.0
            await session.flush()

        # Clean old test positions, orders, ledger for deterministic assertion
        await session.execute(delete(PaperPosition).where(PaperPosition.account_id == acc.id))
        await session.execute(delete(PaperOrder).where(PaperOrder.account_id == acc.id))
        await session.execute(delete(PaperCashLedger).where(PaperCashLedger.account_id == acc.id))
        await session.commit()

        # Seed 2 known holdings
        pos1 = PaperPosition(
            id=f"pos-{uuid.uuid4().hex[:12]}",
            account_id=acc.id,
            symbol="RELIANCE",
            quantity=10,
            average_buy_price=2450.0,
            total_cost_basis=24500.0,
        )
        pos2 = PaperPosition(
            id=f"pos-{uuid.uuid4().hex[:12]}",
            account_id=acc.id,
            symbol="TCS",
            quantity=5,
            average_buy_price=3500.0,
            total_cost_basis=17500.0,
        )
        session.add(pos1)
        session.add(pos2)

        # Seed 1 order
        ord1 = PaperOrder(
            id=f"ord-{uuid.uuid4().hex[:12]}",
            account_id=acc.id,
            user_id=owner_uid,
            symbol="RELIANCE",
            side="BUY",
            order_type="MARKET",
            quantity=10,
            status="FILLED",
            fill_price=2450.0,
            idempotency_key=f"idemp-{uuid.uuid4().hex[:12]}",
        )
        session.add(ord1)

        # Seed 1 ledger entry
        led1 = PaperCashLedger(
            id=f"led-{uuid.uuid4().hex[:12]}",
            account_id=acc.id,
            entry_type="BUY",
            amount=-24500.0,
            balance_after=85000.0,
            description="Buy 10 RELIANCE shares",
        )
        session.add(led1)
        await session.commit()

    # 2. Issue owner investor access token
    investor_token = create_access_token(
        user_id=owner_uid,
        email=owner_email,
        name="Shivraj Dhote",
        provider="google",
    )

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Verify investor token successfully reads portfolio before admin login
        inv_res = await client.get(
            "/api/v1/paper-trading/account",
            headers={"Authorization": f"Bearer {investor_token}"},
        )
        assert inv_res.status_code == 200
        inv_data = inv_res.json()["data"]
        assert float(inv_data["cash_balance"]) == 85000.0

        # Snapshot exact database state before admin operations
        async with AsyncSessionLocal() as session:
            res_u_before = await session.execute(select(User).where(User.id == owner_uid))
            u_before = res_u_before.scalar_one()
            snapshot_user = {
                "id": u_before.id,
                "email": u_before.email,
                "provider": u_before.provider,
                "provider_subject": u_before.provider_subject,
                "password_hash": u_before.password_hash,
                "google_subject": u_before.google_subject,
                "is_active": u_before.is_active,
                "email_verified": u_before.email_verified,
            }

            res_acc_before = await session.execute(select(PaperAccount).where(PaperAccount.user_id == owner_uid))
            acc_before = res_acc_before.scalar_one()
            snapshot_balance = float(acc_before.current_cash)

            res_pos_before = await session.execute(
                select(PaperPosition).where(PaperPosition.account_id == acc_before.id).order_by(PaperPosition.symbol)
            )
            snapshot_positions = [
                {"symbol": p.symbol, "qty": p.quantity, "avg_price": float(p.average_buy_price)}
                for p in res_pos_before.scalars().all()
            ]

            res_ord_before = await session.execute(select(PaperOrder).where(PaperOrder.account_id == acc_before.id))
            snapshot_orders = [(o.id, o.symbol, o.status, o.quantity) for o in res_ord_before.scalars().all()]

            res_led_before = await session.execute(
                select(PaperCashLedger).where(PaperCashLedger.account_id == acc_before.id)
            )
            snapshot_ledger = [(led.id, led.entry_type, float(led.amount)) for led in res_led_before.scalars().all()]

        # 3. Perform Admin Google Login
        with patch("google.oauth2.id_token.verify_oauth2_token") as mock_verify:
            mock_verify.return_value = {
                "iss": "https://accounts.google.com",
                "sub": "owner-google-sub-authorized",
                "email": owner_email,
                "name": "Shivraj Dhote",
                "email_verified": True,
            }
            res_admin_login = await client.post(
                "/api/v1/auth/admin-google",
                json={"id_token": "mock-authorized-id-token"},
            )
            assert res_admin_login.status_code == 200
            admin_token = res_admin_login.json()["data"]["access_token"]

        # 4. Perform Read-Only Admin Operations using admin token
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        res_me = await client.get("/api/v1/admin/me", headers=admin_headers)
        assert res_me.status_code == 200

        res_overview = await client.get("/api/v1/admin/overview", headers=admin_headers)
        assert res_overview.status_code == 200

        res_users = await client.get("/api/v1/admin/users", headers=admin_headers)
        assert res_users.status_code == 200

        res_orders = await client.get("/api/v1/admin/orders", headers=admin_headers)
        assert res_orders.status_code == 200

        # 5. Perform Admin Logout (Revoke admin token)
        res_logout = await client.post(
            "/api/v1/auth/revoke",
            json={"token": admin_token},
            headers=admin_headers,
        )
        assert res_logout.status_code == 200

        # Verify admin token is revoked
        res_admin_check = await client.get("/api/v1/admin/me", headers=admin_headers)
        assert res_admin_check.status_code == 401

        # 6. Verify Owner Investor Session Remains Valid and Operational
        res_inv_after = await client.get(
            "/api/v1/paper-trading/account",
            headers={"Authorization": f"Bearer {investor_token}"},
        )
        assert res_inv_after.status_code == 200
        inv_after_data = res_inv_after.json()["data"]
        assert float(inv_after_data["cash_balance"]) == snapshot_balance

        # 7. Verify Database State Integrity: 100% Unchanged
        async with AsyncSessionLocal() as session:
            res_u_after = await session.execute(select(User).where(User.id == owner_uid))
            u_after = res_u_after.scalar_one()
            assert u_after.id == snapshot_user["id"]
            assert u_after.email == snapshot_user["email"]
            assert u_after.provider == snapshot_user["provider"]
            assert u_after.provider_subject == snapshot_user["provider_subject"]
            assert u_after.password_hash == snapshot_user["password_hash"]
            assert u_after.google_subject == snapshot_user["google_subject"]
            assert u_after.is_active == snapshot_user["is_active"]
            assert u_after.email_verified == snapshot_user["email_verified"]

            res_acc_after = await session.execute(select(PaperAccount).where(PaperAccount.user_id == owner_uid))
            acc_after = res_acc_after.scalar_one()
            assert float(acc_after.current_cash) == snapshot_balance

            res_pos_after = await session.execute(
                select(PaperPosition).where(PaperPosition.account_id == acc_after.id).order_by(PaperPosition.symbol)
            )
            positions_after = [
                {"symbol": p.symbol, "qty": p.quantity, "avg_price": float(p.average_buy_price)}
                for p in res_pos_after.scalars().all()
            ]
            assert positions_after == snapshot_positions

            res_ord_after = await session.execute(select(PaperOrder).where(PaperOrder.account_id == acc_after.id))
            orders_after = [(o.id, o.symbol, o.status, o.quantity) for o in res_ord_after.scalars().all()]
            assert orders_after == snapshot_orders

            res_led_after = await session.execute(
                select(PaperCashLedger).where(PaperCashLedger.account_id == acc_after.id)
            )
            ledger_after = [(led.id, led.entry_type, float(led.amount)) for led in res_led_after.scalars().all()]
            assert ledger_after == snapshot_ledger
