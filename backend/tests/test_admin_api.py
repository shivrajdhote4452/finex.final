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

import uuid
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from backend.app.config import get_settings
from backend.app.database import AsyncSessionLocal, engine
from backend.app.factory import create_app
from backend.app.models.core import Base as CoreBase
from backend.app.models.core import User, UserProfile
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


@pytest.mark.asyncio
async def test_admin_overview_metrics_zero_orders_and_rejections(app, owner_headers):
    """When no paper orders exist, total_orders is 0 and recent_rejected_orders is empty."""
    from backend.app.database import AsyncSessionLocal
    from backend.app.models.paper_trading import PaperOrder
    from sqlalchemy import delete

    # Clear paper orders in test database to verify pure zero-order state
    async with AsyncSessionLocal() as session:
        await session.execute(delete(PaperOrder))
        await session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/admin/overview", headers=owner_headers)
        assert res.status_code == 200
        data = res.json()["data"]

        assert data["total_orders"] == 0
        assert data["orders_by_status"]["FILLED"] == 0
        assert data["orders_by_status"]["REJECTED"] == 0
        assert len(data["recent_rejected_orders"]) == 0


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
        # Verification caveat must clearly document that configuration != live data working
        assert "verification_note" in angel
        assert "live market data" in angel["verification_note"].lower()
        # Ensure raw secrets are NEVER in angel diagnostics
        assert "api_key" not in angel
        assert "client_id" not in angel
        assert "mpin" not in angel
        assert "totp_secret" not in angel

        # Email diagnostics
        assert "email" in data
        email = data["email"]
        assert "is_configured" in email
        # Verification caveat must clearly document that configuration != email delivery working
        assert "verification_note" in email
        assert "email delivery" in email["verification_note"].lower()
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

        # 4. Missing Google subject on DB owner fails closed with 403
        async with AsyncSessionLocal() as session:
            res_u = await session.execute(select(User).where(User.email == owner_email))
            owner_u = res_u.scalar_one_or_none()
            assert owner_u is not None
            owner_u.google_subject = None
            owner_u.provider = "email"
            owner_u.provider_subject = "owner-email-provider-sub-123"
            await session.commit()

        with patch("google.oauth2.id_token.verify_oauth2_token") as mock_verify:
            mock_verify.return_value = {
                "iss": "https://accounts.google.com",
                "sub": "real-persistent-owner-google-sub-123",
                "email": owner_email,
                "name": "Shivraj Dhote",
                "email_verified": True,
            }
            res_missing_sub = await client.post(
                "/api/v1/auth/admin-google",
                json={"id_token": "mock-real-token"},
            )
            assert res_missing_sub.status_code == 403
            assert "not bound to a Google identity" in res_missing_sub.json()["detail"]

            # Verify google_subject in DB was NOT set or relinked
            async with AsyncSessionLocal() as session:
                res_chk = await session.execute(select(User).where(User.email == owner_email))
                chk_u = res_chk.scalar_one_or_none()
                assert chk_u.google_subject is None

        # 5. Placeholder Google subject on DB owner fails closed with 403
        async with AsyncSessionLocal() as session:
            res_u = await session.execute(select(User).where(User.email == owner_email))
            owner_u = res_u.scalar_one_or_none()
            owner_u.google_subject = "placeholder-google-sub-shivraj"
            owner_u.provider = "google"
            owner_u.provider_subject = "placeholder-google-sub-shivraj"
            await session.commit()

        with patch("google.oauth2.id_token.verify_oauth2_token") as mock_verify:
            mock_verify.return_value = {
                "iss": "https://accounts.google.com",
                "sub": "real-persistent-owner-google-sub-123",
                "email": owner_email,
                "name": "Shivraj Dhote",
                "email_verified": True,
            }
            res_placeholder = await client.post(
                "/api/v1/auth/admin-google",
                json={"id_token": "mock-real-token"},
            )
            assert res_placeholder.status_code == 403
            assert "placeholder Google identity" in res_placeholder.json()["detail"]

            # Verify google_subject in DB was NOT overwritten or relinked
            async with AsyncSessionLocal() as session:
                res_chk = await session.execute(select(User).where(User.email == owner_email))
                chk_u = res_chk.scalar_one_or_none()
                assert chk_u.google_subject == "placeholder-google-sub-shivraj"

        # 6. Mismatched Google subject fails closed with 403 without modifying account
        async with AsyncSessionLocal() as session:
            res_u = await session.execute(select(User).where(User.email == owner_email))
            owner_u = res_u.scalar_one_or_none()
            assert owner_u is not None
            # Set a persistent real Google subject
            owner_u.google_subject = "real-persistent-owner-google-sub-123"
            owner_u.provider_subject = "real-persistent-owner-google-sub-123"
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

        # 7. Inactive owner in DB fails closed with 403
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

        # 8. Unverified owner in DB fails closed with 403
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

        # 9. Legitimate verified owner with matching real Google subject succeeds with 200 OK
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
            admin_token = data["access_token"]

            # 10. Access ALL admin endpoints using the issued admin token
            admin_headers = {"Authorization": f"Bearer {admin_token}"}

            # /admin/me
            res_me = await client.get("/api/v1/admin/me", headers=admin_headers)
            assert res_me.status_code == 200
            assert res_me.json()["data"]["email"] == owner_email
            assert res_me.json()["data"]["role"] == "owner"

            # /admin/overview
            res_ov = await client.get("/api/v1/admin/overview", headers=admin_headers)
            assert res_ov.status_code == 200
            assert "total_users" in res_ov.json()["data"]

            # /admin/users
            res_usr = await client.get("/api/v1/admin/users", headers=admin_headers)
            assert res_usr.status_code == 200
            assert "users" in res_usr.json()["data"]

            # /admin/orders
            res_ord = await client.get("/api/v1/admin/orders", headers=admin_headers)
            assert res_ord.status_code == 200
            assert "orders" in res_ord.json()["data"]

            # /admin/system-health
            res_hlth = await client.get("/api/v1/admin/system-health", headers=admin_headers)
            assert res_hlth.status_code == 200
            assert "database" in res_hlth.json()["data"]


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


# =============================================================================
# Enhanced User Directory Search, Date Range, Sorting, Validation & Privacy Tests
# =============================================================================


@pytest.mark.asyncio
async def test_admin_users_date_range_combined_filters_and_sort_order(app, owner_headers):
    """Verify user directory supports registration date bounds, status filters, sorting, and bounded pagination."""
    tag = uuid.uuid4().hex[:10]
    uid_oldest = f"usr-test-oldest-{tag}"
    uid_mid = f"usr-test-mid-{tag}"
    uid_latest = f"usr-test-latest-{tag}"
    created_ids = [uid_oldest, uid_mid, uid_latest]

    async with AsyncSessionLocal() as session:
        session.add_all(
            [
                User(
                    id=uid_oldest,
                    email=f"alpha.{tag}@example.com",
                    provider="email",
                    provider_subject=f"sub-oldest-{tag}",
                    password_hash="hashed-secret-oldest",
                    is_active=False,
                    email_verified=False,
                    is_verified=False,
                    created_at=datetime(2026, 11, 20, 9, 0, 0, tzinfo=timezone.utc),
                ),
                User(
                    id=uid_mid,
                    email=f"beta.{tag}@example.com",
                    provider="google",
                    provider_subject=f"sub-mid-{tag}",
                    google_subject=f"gsub-mid-{tag}",
                    is_active=True,
                    email_verified=True,
                    is_verified=True,
                    created_at=datetime(2026, 11, 22, 14, 30, 0, tzinfo=timezone.utc),
                ),
                User(
                    id=uid_latest,
                    email=f"gamma.{tag}@example.com",
                    provider="email",
                    provider_subject=f"sub-latest-{tag}",
                    password_hash="hashed-secret-latest",
                    is_active=True,
                    email_verified=False,
                    is_verified=False,
                    created_at=datetime(2026, 11, 24, 20, 15, 0, tzinfo=timezone.utc),
                ),
            ]
        )
        await session.flush()
        session.add_all(
            [
                UserProfile(
                    id=f"prof-oldest-{tag}",
                    user_id=uid_oldest,
                    full_name=f"Alpha Investor {tag}",
                    display_name="Alpha",
                    onboarding_completed=False,
                ),
                UserProfile(
                    id=f"prof-mid-{tag}",
                    user_id=uid_mid,
                    full_name=f"Beta Trader {tag}",
                    display_name="Beta",
                    onboarding_completed=True,
                    risk_band="MODERATE",
                    risk_assessment={"q1": "private-answer-never-expose"},
                ),
                UserProfile(
                    id=f"prof-latest-{tag}",
                    user_id=uid_latest,
                    full_name=f"Gamma Member {tag}",
                    display_name="Gamma",
                    onboarding_completed=False,
                ),
            ]
        )
        await session.commit()

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Default order is newest registered first (desc)
            res_desc = await client.get(f"/api/v1/admin/users?search={tag}", headers=owner_headers)
            assert res_desc.status_code == 200
            desc_emails = [u["email"] for u in res_desc.json()["data"]["users"]]
            assert desc_emails == [
                f"gamma.{tag}@example.com",
                f"beta.{tag}@example.com",
                f"alpha.{tag}@example.com",
            ]

            # Explicit ascending sort returns oldest registered first
            res_asc = await client.get(f"/api/v1/admin/users?search={tag}&sort_order=asc", headers=owner_headers)
            assert res_asc.status_code == 200
            asc_emails = [u["email"] for u in res_asc.json()["data"]["users"]]
            assert asc_emails == [
                f"alpha.{tag}@example.com",
                f"beta.{tag}@example.com",
                f"gamma.{tag}@example.com",
            ]

            # YYYY-MM-DD date window excludes 2026-11-20
            res_range = await client.get(
                f"/api/v1/admin/users?search={tag}&date_from=2026-11-22&date_to=2026-11-24",
                headers=owner_headers,
            )
            assert res_range.status_code == 200
            range_emails = [u["email"] for u in res_range.json()["data"]["users"]]
            assert range_emails == [f"gamma.{tag}@example.com", f"beta.{tag}@example.com"]

            # ISO-8601 date_from excludes 14:30Z mid user
            res_iso = await client.get(
                f"/api/v1/admin/users?search={tag}&date_from=2026-11-22T15:00:00Z",
                headers=owner_headers,
            )
            assert res_iso.status_code == 200
            assert [u["email"] for u in res_iso.json()["data"]["users"]] == [f"gamma.{tag}@example.com"]

            # Date to includes full end-of-day UTC
            res_to = await client.get(
                f"/api/v1/admin/users?search={tag}&date_to=2026-11-22",
                headers=owner_headers,
            )
            assert res_to.status_code == 200
            assert [u["email"] for u in res_to.json()["data"]["users"]] == [
                f"beta.{tag}@example.com",
                f"alpha.{tag}@example.com",
            ]

            # Combined filters (active, verified, onboarded, search by name, date range)
            res_combo = await client.get(
                f"/api/v1/admin/users?search=Beta%20Trader%20{tag}&is_active=true&email_verified=true"
                "&onboarding_completed=true&date_from=2026-11-21&date_to=2026-11-23",
                headers=owner_headers,
            )
            assert res_combo.status_code == 200
            combo_users = res_combo.json()["data"]["users"]
            assert len(combo_users) == 1
            assert combo_users[0]["email"] == f"beta.{tag}@example.com"

            # Inactive status filter
            res_inactive = await client.get(f"/api/v1/admin/users?search={tag}&is_active=false", headers=owner_headers)
            assert res_inactive.status_code == 200
            assert [u["email"] for u in res_inactive.json()["data"]["users"]] == [f"alpha.{tag}@example.com"]

            # Bounded pagination: limit=2 across page=1 and page=2
            res_p1 = await client.get(f"/api/v1/admin/users?search={tag}&limit=2&page=1", headers=owner_headers)
            res_p2 = await client.get(f"/api/v1/admin/users?search={tag}&limit=2&page=2", headers=owner_headers)
            p1 = res_p1.json()["data"]
            p2 = res_p2.json()["data"]
            assert p1["total"] == 3
            assert p1["total_pages"] == 2
            assert [u["email"] for u in p1["users"]] == [f"gamma.{tag}@example.com", f"beta.{tag}@example.com"]
            assert [u["email"] for u in p2["users"]] == [f"alpha.{tag}@example.com"]
    finally:
        async with AsyncSessionLocal() as session:
            await session.execute(delete(User).where(User.id.in_(created_ids)))
            await session.commit()


@pytest.mark.asyncio
async def test_admin_users_search_wildcard_escape_outerjoin_and_privacy(app, owner_headers):
    """Verify LIKE escaping, users without UserProfile rows, and strict exclusion of sensitive/ID search leaks."""
    tag = uuid.uuid4().hex[:10]
    uid_literal = f"usr-secretid-only-{tag}"
    uid_wildcard = f"usr-no-profile-{tag}"
    created_ids = [uid_literal, uid_wildcard]

    async with AsyncSessionLocal() as session:
        session.add_all(
            [
                User(
                    id=uid_literal,
                    email=f"literal.{tag}@example.com",
                    provider="google",
                    provider_subject=f"sub-hidden-{tag}",
                    google_subject=f"google-hidden-{tag}",
                    password_hash=f"hash-hidden-{tag}",
                    is_active=True,
                    email_verified=True,
                    is_verified=True,
                ),
                User(
                    id=uid_wildcard,
                    email=f"no.profile.100abcX@{tag}.example.com",
                    provider="email",
                    provider_subject=f"sub-other-{tag}",
                    is_active=True,
                    email_verified=False,
                    is_verified=False,
                ),
            ]
        )
        await session.flush()
        session.add(
            UserProfile(
                id=f"prof-lit-{tag}",
                user_id=uid_literal,
                full_name=f"Investor 100%_match {tag}",
                display_name=f"Handle_{tag}",
                onboarding_completed=True,
                risk_assessment={"secret_note": f"assessment-secret-{tag}"},
            )
        )
        await session.commit()

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # SQL wildcards (% and _) must be escaped and match literal characters only
            res_lit = await client.get("/api/v1/admin/users?search=100%25_match", headers=owner_headers)
            assert res_lit.status_code == 200
            lit_emails = [u["email"] for u in res_lit.json()["data"]["users"]]
            assert f"literal.{tag}@example.com" in lit_emails
            assert f"no.profile.100abcX@{tag}.example.com" not in lit_emails

            # User without UserProfile row still appears via email search & outerjoin
            res_noprof = await client.get("/api/v1/admin/users?search=no.profile.100abcX", headers=owner_headers)
            assert res_noprof.status_code == 200
            noprof_users = res_noprof.json()["data"]["users"]
            assert len(noprof_users) == 1
            assert noprof_users[0]["onboarding_completed"] is False

            # Search must NOT match internal User.id, OAuth subjects, password_hash, or private risk_assessment
            for private_probe in [
                uid_literal,
                f"sub-hidden-{tag}",
                f"google-hidden-{tag}",
                f"hash-hidden-{tag}",
                f"assessment-secret-{tag}",
            ]:
                res_priv = await client.get(f"/api/v1/admin/users?search={private_probe}", headers=owner_headers)
                assert res_priv.status_code == 200
                priv_data = res_priv.json()["data"]
                assert priv_data["total"] == 0, f"Private probe '{private_probe}' unexpectedly matched user records"

            # Verify returned payload keys remain strictly safe
            res_safe = await client.get(f"/api/v1/admin/users?search=Handle_{tag}", headers=owner_headers)
            assert res_safe.status_code == 200
            users = res_safe.json()["data"]["users"]
            assert len(users) == 1
            user_obj = users[0]
            for forbidden_key in ("password_hash", "password", "google_subject", "provider_subject", "risk_assessment"):
                assert forbidden_key not in user_obj
    finally:
        async with AsyncSessionLocal() as session:
            await session.execute(delete(User).where(User.id.in_(created_ids)))
            await session.commit()


@pytest.mark.asyncio
async def test_admin_users_filter_input_validation_and_bounds(app, owner_headers):
    """Verify invalid dates, inverted ranges, invalid sort_order, and out-of-bounds pagination fail with 422."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        invalid_queries = [
            "date_from=not-a-date",
            "date_to=2026-02-30",
            "date_from=2026-11-25&date_to=2026-11-20",
            "sort_order=random",
            "page=0",
            "page=10001",
            "limit=0",
            "limit=101",
            f"search={'a' * 121}",
        ]
        for qs in invalid_queries:
            res = await client.get(f"/api/v1/admin/users?{qs}", headers=owner_headers)
            assert res.status_code == 422, f"Expected 422 for query '{qs}', got {res.status_code}: {res.text}"


@pytest.mark.asyncio
async def test_admin_users_auth_and_readonly_enforced_with_filters(
    app, owner_headers, non_owner_headers, non_google_owner_headers
):
    """Verify server-side owner authorization and read-only scope stay enforced when user filters are passed."""
    transport = ASGITransport(app=app)
    qs = "date_from=2026-11-01&date_to=2026-11-25&sort_order=asc&is_active=true&search=test"
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        assert (await client.get(f"/api/v1/admin/users?{qs}")).status_code == 401
        assert (await client.get(f"/api/v1/admin/users?{qs}", headers=non_owner_headers)).status_code == 403
        assert (await client.get(f"/api/v1/admin/users?{qs}", headers=non_google_owner_headers)).status_code == 403
        assert (await client.post(f"/api/v1/admin/users?{qs}", headers=owner_headers)).status_code == 405
        assert (await client.patch(f"/api/v1/admin/users?{qs}", headers=owner_headers)).status_code == 405
        assert (await client.delete(f"/api/v1/admin/users?{qs}", headers=owner_headers)).status_code == 405


# =============================================================================
# Enhanced Paper Trading Overview, Orders Filtering, Sorting & Privacy Tests
# =============================================================================


@pytest.mark.asyncio
async def test_admin_orders_date_range_filters_sorting_and_pagination(app, owner_headers):
    """Verify /orders and /overview support status counts, date range filters, sorting, and bounded pagination."""
    tag = uuid.uuid4().hex[:8]
    uid = f"usr-ord-test-{tag}"
    acct_id = f"acc-ord-test-{tag}"
    ord_oldest = f"ord-{tag}-oldest"
    ord_mid = f"ord-{tag}-mid"
    ord_rej = f"ord-{tag}-rej"
    ord_latest = f"ord-{tag}-latest"

    async with AsyncSessionLocal() as session:
        session.add(
            User(
                id=uid,
                email=f"orders.tester.{tag}@example.com",
                provider="email",
                provider_subject=f"sub-ord-{tag}",
                is_active=True,
                email_verified=True,
                is_verified=True,
            )
        )
        await session.flush()
        session.add(
            PaperAccount(
                id=acct_id,
                user_id=uid,
                account_number=f"ACC-{tag.upper()}",
                initial_balance=100000.00,
                current_cash=92000.00,
                status="ACTIVE",
            )
        )
        await session.flush()
        session.add_all(
            [
                PaperOrder(
                    id=ord_oldest,
                    account_id=acct_id,
                    user_id=uid,
                    symbol="TCS",
                    side="BUY",
                    order_type="LIMIT",
                    quantity=5,
                    limit_price=3400.00,
                    status="CANCELLED",
                    rejection_reason=None,
                    idempotency_key=f"idemp-1-{tag}",
                    created_at=datetime(2026, 11, 20, 9, 0, 0, tzinfo=timezone.utc),
                ),
                PaperOrder(
                    id=ord_mid,
                    account_id=acct_id,
                    user_id=uid,
                    symbol="INFY",
                    side="SELL",
                    order_type="MARKET",
                    quantity=2,
                    status="PENDING",
                    rejection_reason=None,
                    idempotency_key=f"idemp-2-{tag}",
                    created_at=datetime(2026, 11, 22, 14, 30, 0, tzinfo=timezone.utc),
                ),
                PaperOrder(
                    id=ord_rej,
                    account_id=acct_id,
                    user_id=uid,
                    symbol="RELIANCE",
                    side="BUY",
                    order_type="MARKET",
                    quantity=10,
                    status="REJECTED",
                    rejection_reason=None,
                    idempotency_key=f"idemp-3-{tag}",
                    created_at=datetime(2026, 11, 23, 18, 0, 0, tzinfo=timezone.utc),
                ),
                PaperOrder(
                    id=ord_latest,
                    account_id=acct_id,
                    user_id=uid,
                    symbol="RELIANCE",
                    side="BUY",
                    order_type="MARKET",
                    quantity=3,
                    fill_price=2450.50,
                    status="FILLED",
                    rejection_reason=None,
                    idempotency_key=f"idemp-4-{tag}",
                    created_at=datetime(2026, 11, 24, 21, 0, 0, tzinfo=timezone.utc),
                ),
            ]
        )
        await session.commit()

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Default ordering is newest first (desc) and returns status breakdown
            res_desc = await client.get(f"/api/v1/admin/orders?search={tag}", headers=owner_headers)
            assert res_desc.status_code == 200
            desc_data = res_desc.json()["data"]
            assert [o["id"] for o in desc_data["orders"]] == [ord_latest, ord_rej, ord_mid, ord_oldest]
            assert desc_data["overall_total"] >= 4
            assert desc_data["status_counts"]["FILLED"] >= 1
            assert desc_data["status_counts"]["REJECTED"] >= 1
            assert desc_data["status_counts"]["PENDING"] >= 1
            assert desc_data["status_counts"]["CANCELLED"] >= 1

            # Explicit ascending order returns oldest first
            res_asc = await client.get(f"/api/v1/admin/orders?search={tag}&sort_order=asc", headers=owner_headers)
            assert res_asc.status_code == 200
            assert [o["id"] for o in res_asc.json()["data"]["orders"]] == [ord_oldest, ord_mid, ord_rej, ord_latest]

            # Date window YYYY-MM-DD (2026-11-22..2026-11-23 UTC)
            res_range = await client.get(
                f"/api/v1/admin/orders?search={tag}&date_from=2026-11-22&date_to=2026-11-23",
                headers=owner_headers,
            )
            assert res_range.status_code == 200
            assert [o["id"] for o in res_range.json()["data"]["orders"]] == [ord_rej, ord_mid]

            # ISO-8601 timestamp cutoff excludes 2026-11-23T18:00Z
            res_iso = await client.get(
                f"/api/v1/admin/orders?search={tag}&date_from=2026-11-23T20:00:00Z",
                headers=owner_headers,
            )
            assert res_iso.status_code == 200
            assert [o["id"] for o in res_iso.json()["data"]["orders"]] == [ord_latest]

            # Combined filter: symbol, status, side, search, date range + missing reason fallback
            res_combo = await client.get(
                f"/api/v1/admin/orders?search={tag}&symbol=reliance&status=rejected&side=buy"
                "&date_from=2026-11-20&date_to=2026-11-25",
                headers=owner_headers,
            )
            assert res_combo.status_code == 200
            combo_orders = res_combo.json()["data"]["orders"]
            assert len(combo_orders) == 1
            assert combo_orders[0]["id"] == ord_rej
            assert combo_orders[0]["rejection_reason"] == "Failure reason unavailable"

            # Bounded pagination across pages (limit=2)
            res_p1 = await client.get(f"/api/v1/admin/orders?search={tag}&limit=2&page=1", headers=owner_headers)
            res_p2 = await client.get(f"/api/v1/admin/orders?search={tag}&limit=2&page=2", headers=owner_headers)
            p1 = res_p1.json()["data"]
            p2 = res_p2.json()["data"]
            assert p1["total"] == 4
            assert p1["total_pages"] == 2
            assert [o["id"] for o in p1["orders"]] == [ord_latest, ord_rej]
            assert [o["id"] for o in p2["orders"]] == [ord_mid, ord_oldest]

            # Overview reflects recent orders across recorded statuses + status breakdown
            res_ov = await client.get("/api/v1/admin/overview", headers=owner_headers)
            assert res_ov.status_code == 200
            ov = res_ov.json()["data"]
            assert ov["total_orders"] >= 4
            assert isinstance(ov["recent_orders"], list)
            assert len(ov["recent_orders"]) >= 1
    finally:
        async with AsyncSessionLocal() as session:
            await session.execute(delete(User).where(User.id == uid))
            await session.commit()


@pytest.mark.asyncio
async def test_admin_orders_privacy_balance_redaction_and_search_scope(app, owner_headers):
    """Verify private cash/holding counts/tracebacks are sanitized, user_email omitted, and search excludes PII/reasons."""
    tag = uuid.uuid4().hex[:8]
    uid = f"usr-priv-ord-{tag}"
    acct_id = f"acc-priv-ord-{tag}"
    private_email = f"priv.balance.{tag}@example.com"
    ord_cash = f"ord-{tag}-cash"
    ord_hold = f"ord-{tag}-hold"
    ord_trace = f"ord-{tag}-trace"
    ord_wild = f"ord-{tag}-100%_match"
    ord_sim = f"ord-{tag}-100abcXmatch"

    async with AsyncSessionLocal() as session:
        session.add(
            User(
                id=uid,
                email=private_email,
                provider="email",
                provider_subject=f"sub-priv-ord-{tag}",
                is_active=True,
                email_verified=True,
                is_verified=True,
            )
        )
        await session.flush()
        session.add(
            PaperAccount(
                id=acct_id,
                user_id=uid,
                account_number=f"ACC-P-{tag.upper()}",
                initial_balance=100000.00,
                current_cash=98765.43,
                status="ACTIVE",
            )
        )
        await session.flush()
        session.add_all(
            [
                PaperOrder(
                    id=ord_cash,
                    account_id=acct_id,
                    user_id=uid,
                    symbol="HDFCBANK",
                    side="BUY",
                    order_type="MARKET",
                    quantity=10,
                    status="REJECTED",
                    rejection_reason="Insufficient virtual cash. Required: ₹150,000.00, Available: ₹98,765.43.",
                    idempotency_key=f"idemp-c-{tag}",
                    execution_receipt={"raw_internal_secret": "never-expose"},
                ),
                PaperOrder(
                    id=ord_hold,
                    account_id=acct_id,
                    user_id=uid,
                    symbol="INFY",
                    side="SELL",
                    order_type="MARKET",
                    quantity=20,
                    status="REJECTED",
                    rejection_reason="Insufficient holding quantity. Attempted to sell 20 shares, but you hold 5 shares of INFY.",
                    idempotency_key=f"idemp-h-{tag}",
                ),
                PaperOrder(
                    id=ord_trace,
                    account_id=acct_id,
                    user_id=uid,
                    symbol="WIPRO",
                    side="BUY",
                    order_type="MARKET",
                    quantity=1,
                    status="REJECTED",
                    rejection_reason='Traceback (most recent call last): File "/app/secret.py", line 10',
                    idempotency_key=f"idemp-t-{tag}",
                ),
                PaperOrder(
                    id=ord_wild,
                    account_id=acct_id,
                    user_id=uid,
                    symbol="SBIN",
                    side="BUY",
                    order_type="MARKET",
                    quantity=1,
                    status="FILLED",
                    fill_price=800.0,
                    idempotency_key=f"idemp-w-{tag}",
                ),
                PaperOrder(
                    id=ord_sim,
                    account_id=acct_id,
                    user_id=uid,
                    symbol="LT",
                    side="BUY",
                    order_type="MARKET",
                    quantity=1,
                    status="FILLED",
                    fill_price=3500.0,
                    idempotency_key=f"idemp-s-{tag}",
                ),
            ]
        )
        await session.commit()

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.get(f"/api/v1/admin/orders?search={tag}", headers=owner_headers)
            assert res.status_code == 200
            by_id = {o["id"]: o for o in res.json()["data"]["orders"]}

            # User email PII and private balances / holding counts / tracebacks must not be leaked
            for order in by_id.values():
                assert order["user_email"] is None
                assert "execution_receipt" not in order
                assert "idempotency_key" not in order

            assert by_id[ord_cash]["rejection_reason"] == "Insufficient virtual cash balance for requested order."
            assert "98,765" not in by_id[ord_cash]["rejection_reason"]
            assert by_id[ord_hold]["rejection_reason"] == "Insufficient holding quantity for requested sell order."
            assert "hold 5" not in by_id[ord_hold]["rejection_reason"]
            assert by_id[ord_trace]["rejection_reason"] == "Failure details withheld for safety"
            assert "secret.py" not in by_id[ord_trace]["rejection_reason"]

            # Overview recent_rejected_orders must apply identical balance/trace redaction
            res_ov = await client.get("/api/v1/admin/overview", headers=owner_headers)
            assert res_ov.status_code == 200
            ov_rej = {o["id"]: o for o in res_ov.json()["data"]["recent_rejected_orders"]}
            if ord_cash in ov_rej:
                assert "98,765" not in (ov_rej[ord_cash]["rejection_reason"] or "")
                assert ov_rej[ord_cash]["user_email"] is None

            # Wildcard escaping in order ID search
            res_wild = await client.get("/api/v1/admin/orders?search=100%25_match", headers=owner_headers)
            assert res_wild.status_code == 200
            wild_ids = [o["id"] for o in res_wild.json()["data"]["orders"]]
            assert ord_wild in wild_ids
            assert ord_sim not in wild_ids

            # Search must NOT match user email or private rejection_reason balance strings
            for probe in (private_email, "98,765.43", "secret.py"):
                res_probe = await client.get(f"/api/v1/admin/orders?search={probe}", headers=owner_headers)
                assert res_probe.status_code == 200
                assert res_probe.json()["data"]["total"] == 0
    finally:
        async with AsyncSessionLocal() as session:
            await session.execute(delete(User).where(User.id == uid))
            await session.commit()


@pytest.mark.asyncio
async def test_admin_orders_filter_validation_and_bounds(app, owner_headers):
    """Verify invalid dates, invalid status/side/symbol filters, sort_order, and pagination bounds fail with 422."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        invalid_queries = [
            "date_from=invalid-date",
            "date_to=2026-02-30",
            "date_from=2026-11-25&date_to=2026-11-20",
            "status=ACCEPTED",
            "status=UNKNOWN_STATUS",
            "side=SHORT",
            "symbol=TCS%3BDROP",
            "sort_order=random",
            "page=0",
            "page=1001",
            "limit=0",
            "limit=101",
            f"search={'x' * 81}",
        ]
        for qs in invalid_queries:
            res = await client.get(f"/api/v1/admin/orders?{qs}", headers=owner_headers)
            assert res.status_code == 422, f"Expected 422 for query '{qs}', got {res.status_code}: {res.text}"


@pytest.mark.asyncio
async def test_admin_orders_auth_and_readonly_enforced_with_filters(
    app, owner_headers, non_owner_headers, non_google_owner_headers
):
    """Verify owner-only auth and read-only HTTP methods stay strictly enforced on /orders and /overview."""
    transport = ASGITransport(app=app)
    qs = "date_from=2026-11-01&date_to=2026-11-25&sort_order=asc&status=FILLED&side=BUY&search=RELIANCE"
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        assert (await client.get(f"/api/v1/admin/orders?{qs}")).status_code == 401
        assert (await client.get(f"/api/v1/admin/orders?{qs}", headers=non_owner_headers)).status_code == 403
        assert (await client.get(f"/api/v1/admin/orders?{qs}", headers=non_google_owner_headers)).status_code == 403
        for method in ("post", "put", "patch", "delete"):
            res = await getattr(client, method)(f"/api/v1/admin/orders?{qs}", headers=owner_headers)
            assert res.status_code == 405
            res_ov = await getattr(client, method)("/api/v1/admin/overview", headers=owner_headers)
            assert res_ov.status_code == 405
