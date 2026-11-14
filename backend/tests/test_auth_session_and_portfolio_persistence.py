"""Automated Tests for Authentication, Session Persistence, and Paper Portfolio Sync.

Validates:
1. Google OAuth callback accepts the web client ID (71626572471-2333p55kgim64b3738oabca9l9ss9th0.apps.googleusercontent.com)
   and issues a cryptographically signed FinEx backend JWT access token.
2. Browser refresh session restoration: GET /api/v1/users/me succeeds with valid JWT.
3. Expired or forged JWT access tokens fail closed with HTTP 401.
4. Raw Google ID tokens sent directly to protected endpoints fail closed with HTTP 401 (preventing token corruption).
5. GET /api/v1/paper-trading/account succeeds with valid JWT, returning virtual cash of 100,000 and empty positions
   list without API or server error.
6. Empty portfolio structure returns HTTP 200 with empty list rather than 404/500, enabling clean UI empty-state rendering.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch
import jwt
import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.config import get_settings
from backend.app.factory import create_app
from backend.app.routers.auth import create_access_token

app = create_app()
settings = get_settings()

TEST_USER_ID = "usr-test-sess-001"
TEST_USER_EMAIL = "session.tester@finexai.tech"
TEST_USER_NAME = "Session Tester"
EXPECTED_AUDIENCE = "71626572471-2333p55kgim64b3738oabca9l9ss9th0.apps.googleusercontent.com"


@pytest.mark.asyncio
async def test_google_auth_accepts_web_client_id_and_returns_jwt():
    """Verify Google OAuth callback accepts web client ID and issues valid FinEx backend JWT."""
    mock_id_info = {
        "sub": "google-sub-session-001",
        "email": TEST_USER_EMAIL,
        "name": TEST_USER_NAME,
        "iss": "https://accounts.google.com",
        "aud": EXPECTED_AUDIENCE,
    }

    with patch("google.oauth2.id_token.verify_oauth2_token", return_value=mock_id_info) as mock_verify:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/auth/google",
                json={"id_token": "mock-valid-google-id-token"},
            )
            assert resp.status_code == 200
            data = resp.json()["data"]
            assert data["email"] == TEST_USER_EMAIL
            assert data["name"] == TEST_USER_NAME
            assert "access_token" in data
            assert data["token_type"].lower() == "bearer"

            # Check that mock_verify was called with the correct audience
            mock_verify.assert_called_once()
            called_audience = mock_verify.call_args[1].get("audience")
            assert called_audience == EXPECTED_AUDIENCE

            # Verify the issued token is a valid HS256 JWT signed with backend secret
            token = data["access_token"]
            payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=["HS256"])
            assert payload["email"] == TEST_USER_EMAIL
            assert "sub" in payload
            assert payload["exp"] > datetime.now(timezone.utc).timestamp()


@pytest.mark.asyncio
async def test_session_restoration_users_me_success():
    """Verify session restoration on page refresh: valid JWT allows fetching user profile."""
    mock_id_info = {
        "sub": "google-sub-session-002",
        "email": "refresh.tester@finexai.tech",
        "name": "Refresh Tester",
        "iss": "https://accounts.google.com",
        "aud": EXPECTED_AUDIENCE,
    }
    with patch("google.oauth2.id_token.verify_oauth2_token", return_value=mock_id_info):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            login_resp = await client.post(
                "/api/v1/auth/google",
                json={"id_token": "valid-google-id-token-for-refresh"},
            )
            assert login_resp.status_code == 200
            token = login_resp.json()["data"]["access_token"]

            headers = {"Authorization": f"Bearer {token}"}
            resp = await client.get("/api/v1/users/me", headers=headers)
            assert resp.status_code == 200
            data = resp.json()["data"]
            assert data["email"] == "refresh.tester@finexai.tech"
            assert data["full_name"] == "Refresh Tester"


@pytest.mark.asyncio
async def test_expired_or_invalid_jwt_returns_401():
    """Verify that an expired JWT token returns HTTP 401 on protected routes."""
    # Create an expired token manually
    expired_payload = {
        "sub": TEST_USER_ID,
        "email": TEST_USER_EMAIL,
        "name": TEST_USER_NAME,
        "exp": datetime.now(timezone.utc) - timedelta(hours=2),
        "iat": datetime.now(timezone.utc) - timedelta(hours=3),
    }
    expired_token = jwt.encode(expired_payload, settings.JWT_SECRET_KEY, algorithm="HS256")
    headers = {"Authorization": f"Bearer {expired_token}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/users/me", headers=headers)
        assert resp.status_code == 401
        assert "expired" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_raw_google_id_token_rejected_on_protected_endpoints():
    """Verify that a raw Google ID token (RS256 / non-backend JWT) is rejected with 401 on protected endpoints."""
    # A mock raw Google ID token header
    raw_google_id_token = "eyJhbGciOiJSUzI1NiIsImtpZCI6IjEyMzQ1In0.eyJpc3MiOiJodHRwczovL2FjY291bnRzLmdvb2dsZS5jb20iLCJzdWIiOiIxMjM0NTYifQ.mocksignature"
    headers = {"Authorization": f"Bearer {raw_google_id_token}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp_me = await client.get("/api/v1/users/me", headers=headers)
        assert resp_me.status_code == 401

        resp_paper = await client.get("/api/v1/paper-trading/account", headers=headers)
        assert resp_paper.status_code == 401


@pytest.mark.asyncio
async def test_paper_trading_account_isolated_and_seeded():
    """Verify that an authenticated user gets an initial 100,000 INR paper trading balance and valid portfolio summary."""
    token = create_access_token(
        user_id="usr-test-portfolio-seed-01",
        email="seed.portfolio@finexai.tech",
        name="Seed Portfolio Tester",
    )
    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/paper-trading/account", headers=headers)
        assert resp.status_code == 200
        envelope = resp.json()
        assert "data" in envelope
        data = envelope["data"]

        # Assert seeded cash is 100,000 INR
        assert float(data["cash_balance"]) == 100000.0
        assert float(data["total_portfolio_value"]) >= 100000.0
        assert data["currency"] == "INR"
        assert isinstance(data["positions"], list)
        assert len(data["positions"]) == 0
        assert data["account_id"].startswith("acct-")


@pytest.mark.asyncio
async def test_empty_portfolio_response_structure_vs_error():
    """Verify that empty holdings return HTTP 200 with an empty list rather than an error."""
    token = create_access_token(
        user_id="usr-test-empty-portfolio",
        email="empty.portfolio@finexai.tech",
        name="Empty Portfolio User",
    )
    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/paper-trading/account", headers=headers)
        assert resp.status_code == 200
        data = resp.json()["data"]

        # Ensure positions is a clean empty list and holdings_value is zero
        assert data["positions"] == []
        assert float(data["positions_market_value"]) == 0.0
        assert float(data["unrealized_pnl"]) == 0.0
        assert float(data["cash_balance"]) == 100000.0
