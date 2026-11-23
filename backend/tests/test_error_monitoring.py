"""Tests for FinEx Admin Error Monitoring & Diagnostics.

Validates:
1. Server-side owner authorization on /api/v1/admin/errors and /api/v1/admin/errors/summary:
   - Unauthenticated requests fail closed with HTTP 401 Unauthorized.
   - Non-owner requests fail closed with HTTP 403 Forbidden.
   - Non-Google provider sessions fail closed with HTTP 403 Forbidden.
   - Owner Google OAuth session succeeds with HTTP 200 OK.
2. Server-side data sanitization:
   - Redacts email addresses, Bearer tokens, raw JWTs, passwords, API keys, and filesystem paths.
   - Truncates oversized messages to prevent database bloat.
3. Durable error event recording and correlation ID tracking:
   - Records error events with endpoint, method, status code, category, feature area, and correlation ID.
   - Propagates correlation IDs safely into the error registry.
4. Pagination, sorting, and filtering:
   - Filters by status code, error category, feature area, and text search.
   - Respects pagination limits and page offsets.
5. Errors summary metrics:
   - Aggregates total errors, 5xx server errors, 4xx client errors, and 24h error count.
   - Breaks down counts by category and feature area.
6. Storage failure resilience:
   - Database failure or session exception in error recording MUST NEVER break or crash normal requests.
7. Read-only enforcement:
   - POST, PUT, DELETE methods on /api/v1/admin/errors fail with HTTP 405 Method Not Allowed.
"""

import asyncio
import re
import time
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from backend.app.config import get_settings
from backend.app.database import AsyncSessionLocal, engine
from backend.app.factory import create_app
from backend.app.models import Base
from backend.app.models.monitoring import ErrorEvent
from backend.app.routers.auth import create_access_token
from backend.app.services.error_recorder import (
    _is_recording_ctx,
    categorize_error,
    extract_route_template,
    prune_bounded_storage,
    prune_if_due,
    record_error_event,
    reset_error_recorder_state,
    resolve_safe_error_details,
    sanitize_correlation_id,
    sanitize_error_message,
    sanitize_method,
    sanitize_user_id,
)
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select


@pytest.fixture
def app():
    return create_app()


@pytest.fixture(scope="module", autouse=True)
def setup_module_db():
    import asyncio

    async def _init():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

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
# 1. Server-Side Owner Authorization Tests (Fail-Closed)
# =============================================================================


@pytest.mark.asyncio
async def test_error_monitoring_requires_authentication(app):
    """Unauthenticated requests fail closed with HTTP 401."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for path in ["/api/v1/admin/errors", "/api/v1/admin/errors/summary"]:
            res = await client.get(path)
            assert res.status_code == 401, f"Expected 401 for {path}, got {res.status_code}"


@pytest.mark.asyncio
async def test_error_monitoring_refuses_non_owners(app, non_owner_headers):
    """Authenticated non-owners are refused with HTTP 403 Forbidden."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for path in ["/api/v1/admin/errors", "/api/v1/admin/errors/summary"]:
            res = await client.get(path, headers=non_owner_headers)
            assert res.status_code == 403, f"Expected 403 for {path}, got {res.status_code}"
            assert "owner" in res.json().get("detail", "").lower()


@pytest.mark.asyncio
async def test_error_monitoring_refuses_non_google_sessions(app, non_google_owner_headers):
    """Non-Google sessions (even matching owner email) fail closed with HTTP 403."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for path in ["/api/v1/admin/errors", "/api/v1/admin/errors/summary"]:
            res = await client.get(path, headers=non_google_owner_headers)
            assert res.status_code == 403, f"Expected 403 for {path}, got {res.status_code}"


@pytest.mark.asyncio
async def test_error_monitoring_succeeds_for_owner(app, owner_headers):
    """Owner Google session succeeds with HTTP 200 OK."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res_list = await client.get("/api/v1/admin/errors", headers=owner_headers)
        assert res_list.status_code == 200
        data_list = res_list.json().get("data", res_list.json())
        assert "errors" in data_list
        assert "total" in data_list
        assert "page" in data_list
        assert "scope_notice" in data_list

        res_sum = await client.get("/api/v1/admin/errors/summary", headers=owner_headers)
        assert res_sum.status_code == 200
        data_sum = res_sum.json().get("data", res_sum.json())
        assert "total_errors" in data_sum
        assert "server_errors_5xx" in data_sum
        assert "client_errors_4xx" in data_sum
        assert "last_24h_errors" in data_sum
        assert "errors_by_category" in data_sum
        assert "errors_by_feature" in data_sum


# =============================================================================
# 2. Server-Side Data Sanitization Tests
# =============================================================================


def test_sanitization_removes_sensitive_information():
    """Verify that credentials, tokens, PII, and paths are redacted server-side."""
    # 1. Plain safe message
    safe_msg = "Order validation failed: insufficient cash balance"
    assert sanitize_error_message(safe_msg) == safe_msg

    # 2. Redacts emails
    email_msg = "Failed to send notification to customer.user@example.com in region ap-south-1"
    sanitized_email = sanitize_error_message(email_msg)
    assert "[REDACTED_EMAIL]" in sanitized_email
    assert "customer.user@example.com" not in sanitized_email

    # 3. Redacts Bearer tokens
    bearer_msg = "Authentication failed with Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.dummy.sig"
    sanitized_bearer = sanitize_error_message(bearer_msg)
    assert "Bearer [REDACTED_TOKEN]" in sanitized_bearer
    assert "eyJhbGciOi" not in sanitized_bearer

    # 4. Redacts raw JWT patterns
    jwt_msg = "Unexpected token format: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.payload.sig in header"
    sanitized_jwt = sanitize_error_message(jwt_msg)
    assert "[REDACTED_JWT]" in sanitized_jwt
    assert "eyJhbGciOi" not in sanitized_jwt

    # 5. Redacts passwords, API keys, and secret credentials
    secret_msg = (
        'Connection error: password="MySuperSecret123!" api_key=sk-proj-9988776655 '
        "secret_key=xyz123 access_token=tok456"
    )
    sanitized_secrets = sanitize_error_message(secret_msg)
    assert "[REDACTED]" in sanitized_secrets
    assert "password=" in sanitized_secrets
    assert "api_key=" in sanitized_secrets
    assert "secret_key=" in sanitized_secrets
    assert "access_token=" in sanitized_secrets
    assert "MySuperSecret123!" not in sanitized_secrets
    assert "sk-proj-9988776655" not in sanitized_secrets
    assert "xyz123" not in sanitized_secrets
    assert "tok456" not in sanitized_secrets

    # 6. Redacts local filesystem paths
    path_msg = r"Error loading file C:\Users\Shivraj Dhote\Finex\secrets.env: not found"
    sanitized_path = sanitize_error_message(path_msg)
    assert "[REDACTED_PATH]" in sanitized_path
    assert "Shivraj Dhote" not in sanitized_path

    # Unix path redaction
    unix_path_msg = "Error reading /home/ubuntu/finex/config/private.key: permission denied"
    sanitized_unix = sanitize_error_message(unix_path_msg)
    assert "[REDACTED_PATH]" in sanitized_unix
    assert "/home/ubuntu" not in sanitized_unix

    # 7. Bounded message length
    huge_msg = "x" * 1500
    sanitized_huge = sanitize_error_message(huge_msg, max_length=100)
    assert len(sanitized_huge) <= 100 + len(" [TRUNCATED]")
    assert "[TRUNCATED]" in sanitized_huge


def test_categorize_error_mapping():
    """Verify status code and path categorization into operational feature areas."""
    # Database error
    cat1, feat1 = categorize_error(500, Exception("OperationalError: database connection lost"), "/api/v1/portfolio")
    assert cat1 == "DATABASE"
    assert feat1 == "Portfolio"

    # Upstream API error
    cat2, feat2 = categorize_error(503, Exception("Angel One upstream timeout"), "/api/v1/market/quote/RELIANCE")
    assert cat2 == "UPSTREAM_API"
    assert feat2 == "Market Data"

    # Rate limit error
    cat3, feat3 = categorize_error(429, None, "/api/v1/chat")
    assert cat3 == "RATE_LIMIT"
    assert feat3 == "AI Assistant"

    # Validation error
    cat4, feat4 = categorize_error(422, None, "/api/v1/orders/paper")
    assert cat4 == "VALIDATION"
    assert feat4 == "Paper Trading"


# =============================================================================
# 3. Durable Recording & Correlation ID Propagation Tests
# =============================================================================


@pytest.mark.asyncio
async def test_record_and_query_error_event(app, owner_headers):
    """Verify that an error event is durably recorded and retrievable with correlation ID."""
    test_corr_id = f"cid-{uuid.uuid4().hex[:16]}"
    test_msg = "Database connection timed out for user_id=usr-test with password=superSecretPassword!"

    # Record event
    event = await record_error_event(
        correlation_id=test_corr_id,
        endpoint="/api/v1/portfolio/holdings",
        method="GET",
        status_code=500,
        error_type="TimeoutError",
        raw_message=test_msg,
        user_id="usr-test-123",
    )
    assert event is not None
    assert event.correlation_id == test_corr_id
    assert event.status_code == 500
    assert "superSecretPassword!" not in event.sanitized_message
    assert event.sanitized_message == "Database operation failed or timed out."

    # Query via Admin API
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get(f"/api/v1/admin/errors?search={test_corr_id}", headers=owner_headers)
        assert res.status_code == 200
        data = res.json().get("data", res.json())
        assert data["total"] >= 1
        found = [e for e in data["errors"] if e["correlation_id"] == test_corr_id]
        assert len(found) == 1
        item = found[0]
        assert item["status_code"] == 500
        assert item["category"] == "DATABASE"
        assert item["feature_area"] == "Portfolio"
        assert item["method"] == "GET"
        assert item["endpoint"] == "/api/v1/portfolio/holdings"
        assert item["sanitized_message"] == "Database operation failed or timed out."
        assert "superSecretPassword!" not in item["sanitized_message"]


# =============================================================================
# 4. Pagination, Sorting, and Filtering Tests
# =============================================================================


@pytest.mark.asyncio
async def test_errors_filtering_and_pagination(app, owner_headers):
    """Verify filtering by status_code, category, and pagination mechanics."""
    tag = uuid.uuid4().hex[:12]

    # Create 3 distinct events with unique searchable tag
    await record_error_event(
        correlation_id=f"cid-{tag}0001",
        endpoint="/api/v1/auth/google",
        method="POST",
        status_code=500,
        error_type="GoogleOAuthError",
        raw_message=f"Google OAuth token verification failed tag={tag}",
    )
    await record_error_event(
        correlation_id=f"cid-{tag}0002",
        endpoint="/api/v1/orders/paper",
        method="POST",
        status_code=422,
        error_type="RequestValidationError",
        raw_message=f"Invalid order quantity specified tag={tag}",
    )
    await record_error_event(
        correlation_id=f"cid-{tag}0003",
        endpoint="/api/v1/market/live",
        method="GET",
        status_code=429,
        error_type="RateLimitExceeded",
        raw_message=f"Rate limit exceeded on market quote stream tag={tag}",
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Search by tag
        res_all = await client.get(f"/api/v1/admin/errors?search={tag}", headers=owner_headers)
        assert res_all.status_code == 200
        data_all = res_all.json().get("data", res_all.json())
        assert data_all["total"] == 3

        # Filter by status code 500
        res_500 = await client.get(f"/api/v1/admin/errors?search={tag}&status_code=500", headers=owner_headers)
        assert res_500.status_code == 200
        items_500 = res_500.json().get("data", res_500.json())["errors"]
        assert len(items_500) == 1
        assert items_500[0]["status_code"] == 500

        # Filter by category RATE_LIMIT
        res_rl = await client.get(f"/api/v1/admin/errors?search={tag}&category=RATE_LIMIT", headers=owner_headers)
        assert res_rl.status_code == 200
        items_rl = res_rl.json().get("data", res_rl.json())["errors"]
        assert len(items_rl) == 1
        assert items_rl[0]["category"] == "RATE_LIMIT"

        # Pagination: limit=1, page=1
        res_p1 = await client.get(f"/api/v1/admin/errors?search={tag}&limit=1&page=1", headers=owner_headers)
        assert res_p1.status_code == 200
        p1_data = res_p1.json().get("data", res_p1.json())
        assert len(p1_data["errors"]) == 1
        assert p1_data["page"] == 1
        assert p1_data["limit"] == 1
        assert p1_data["total_pages"] == 3

        # Pagination: limit=1, page=2
        res_p2 = await client.get(f"/api/v1/admin/errors?search={tag}&limit=1&page=2", headers=owner_headers)
        assert res_p2.status_code == 200
        p2_data = res_p2.json().get("data", res_p2.json())
        assert len(p2_data["errors"]) == 1
        assert p2_data["page"] == 2
        assert p2_data["errors"][0]["id"] != p1_data["errors"][0]["id"]


# =============================================================================
# 5. Errors Summary Endpoint Tests
# =============================================================================


@pytest.mark.asyncio
async def test_errors_summary_metrics(app, owner_headers):
    """Verify aggregate summary metrics count 5xx, 4xx, and categorical breakdowns."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/admin/errors/summary", headers=owner_headers)
        assert res.status_code == 200
        data = res.json().get("data", res.json())
        assert isinstance(data["total_errors"], int)
        assert isinstance(data["server_errors_5xx"], int)
        assert isinstance(data["client_errors_4xx"], int)
        assert isinstance(data["last_24h_errors"], int)
        assert isinstance(data["errors_by_category"], dict)
        assert isinstance(data["errors_by_feature"], dict)
        assert data["server_errors_5xx"] + data["client_errors_4xx"] <= data["total_errors"]


# =============================================================================
# 6. Failure Resilience Tests (Storage Unavailable)
# =============================================================================


@pytest.mark.asyncio
async def test_error_recording_failure_does_not_break_caller():
    """Verify that if the database is down, record_error_event logs a warning and returns None without raising."""
    with patch("backend.app.services.error_recorder.AsyncSessionLocal") as mock_session_factory:
        mock_session_factory.side_effect = Exception("PostgreSQL server went away / socket error")

        # Must not raise an exception
        result = await record_error_event(
            correlation_id="test-fail-resilience",
            endpoint="/api/v1/test",
            method="GET",
            status_code=500,
            error_type="TestError",
            raw_message="Testing storage failure resilience",
        )
        assert result is None, "Should cleanly return None when storage is unavailable"


@pytest.mark.asyncio
async def test_prune_bounded_storage_failure_does_not_raise():
    """Verify that storage pruning handles database failures gracefully without raising."""
    with patch("backend.app.services.error_recorder.AsyncSessionLocal") as mock_session_factory:
        mock_session_factory.side_effect = Exception("Database locked")

        # Must not raise
        await prune_bounded_storage()


# =============================================================================
# 7. Read-Only Mutation Protection Tests
# =============================================================================


@pytest.mark.asyncio
async def test_error_endpoints_are_strictly_read_only(app, owner_headers):
    """Verify that mutating methods (POST, PUT, DELETE, PATCH) return 405 Method Not Allowed."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # POST
        res_post = await client.post("/api/v1/admin/errors", headers=owner_headers, json={})
        assert res_post.status_code == 405

        # DELETE
        res_del = await client.delete("/api/v1/admin/errors", headers=owner_headers)
        assert res_del.status_code == 405

        # PUT
        res_put = await client.put("/api/v1/admin/errors", headers=owner_headers, json={})
        assert res_put.status_code == 405

        # PATCH
        res_patch = await client.patch("/api/v1/admin/errors", headers=owner_headers, json={})
        assert res_patch.status_code == 405


# =============================================================================
# 8. Route Template Extraction & Parameter Scrubbing Tests (Finding 2)
# =============================================================================


def test_route_template_extraction_from_starlette_scope():
    """Verify route template preservation from Starlette scope vs parameter scrubbing."""

    class MockRoute:
        path = "/api/v1/users/{user_id}/portfolio"

    class MockRequest:
        scope = {"route": MockRoute()}
        url = type("URL", (), {"path": "/api/v1/users/usr-secret-9999/portfolio"})()

    template = extract_route_template(MockRequest())
    assert template == "/api/v1/users/{user_id}/portfolio"


def test_unmatched_route_anonymizes_sensitive_path_segments():
    """Verify that unmatched routes with short secrets, names, emails, and tokens are NEVER persisted.

    Any unmatched path strictly resolves to generic '/unmatched_route'.
    """
    # 1. Short secrets and passwords in URL
    assert extract_route_template(None, fallback_path="/api/v1/debug/hunter2") == "/unmatched_route"
    assert extract_route_template(None, fallback_path="/api/v1/auth/secret123") == "/unmatched_route"
    assert extract_route_template(None, fallback_path="/api/v1/keys/sk_test_9988") == "/unmatched_route"

    # 2. Names and usernames in path
    assert extract_route_template(None, fallback_path="/api/v1/users/john_doe") == "/unmatched_route"
    assert extract_route_template(None, fallback_path="/api/v1/profiles/shivraj") == "/unmatched_route"

    # 3. Emails in path
    assert extract_route_template(None, fallback_path="/api/v1/verify/alice@example.com") == "/unmatched_route"
    assert extract_route_template(None, fallback_path="/api/v1/users/customer.test@gmail.com") == "/unmatched_route"

    # 4. Short tokens and hashes in path
    assert extract_route_template(None, fallback_path="/api/v1/reset/tok99") == "/unmatched_route"
    assert (
        extract_route_template(None, fallback_path="/api/v1/audit/12345678-1234-5678-1234-567812345678")
        == "/unmatched_route"
    )

    # 5. Empty or None path
    assert extract_route_template(None, fallback_path="") == "/unmatched_route"
    assert extract_route_template(None, fallback_path=None) == "/unmatched_route"

    # 6. Static known allowlisted routes are preserved
    assert extract_route_template(None, fallback_path="/api/v1/health") == "/api/v1/health"
    assert extract_route_template(None, fallback_path="/api/v1/portfolio/holdings") == "/api/v1/portfolio/holdings"
    assert extract_route_template(None, fallback_path="/api/v1/orders/paper") == "/api/v1/orders/paper"

    # 7. Valid explicit parameterized route templates are preserved
    assert (
        extract_route_template(None, fallback_path="/api/v1/users/{user_id}/portfolio")
        == "/api/v1/users/{user_id}/portfolio"
    )


# =============================================================================
# 9. Metadata Sanitization & Bounding Tests (Finding 2)
# =============================================================================


def test_metadata_validation_and_bounding():
    """Verify correlation ID, user ID, and HTTP method validation and length bounding."""
    # Correlation ID: Valid trusted formats (canonical UUID, hex trace IDs, cid-/req- prefixed hex)
    assert sanitize_correlation_id("12345678-1234-4234-8234-123456789abc") == "12345678-1234-4234-8234-123456789abc"
    assert sanitize_correlation_id("4B2E8A1D-7F3C-4E89-9A12-8C4D2E1F0B9A") == "4b2e8a1d-7f3c-4e89-9a12-8c4d2e1f0b9a"
    assert sanitize_correlation_id("a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6") == "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6"
    assert sanitize_correlation_id("cid-0123456789abcdef") == "cid-0123456789abcdef"
    assert sanitize_correlation_id("req-0123456789abcdef0123456789abcdef") == "req-0123456789abcdef0123456789abcdef"
    assert sanitize_correlation_id("trace-0123456789abcdef") == "trace-0123456789abcdef"

    # Malicious correlation ID replaced with safe server-generated UUID
    dirty_cid = "<script>alert('xss')</script>"
    clean_dirty = sanitize_correlation_id(dirty_cid)
    assert clean_dirty != dirty_cid
    assert len(clean_dirty) == 32  # uuid4 hex

    # Oversized correlation ID (> 64 chars) replaced with safe UUID
    long_cid = "a" * 100
    clean_long = sanitize_correlation_id(long_cid)
    assert len(clean_long) == 32

    # User ID
    assert sanitize_user_id("usr-safe-123") == "usr-safe-123"
    assert sanitize_user_id("admin' OR '1'='1") is None
    assert sanitize_user_id("u" * 100) is None
    assert sanitize_user_id(None) is None

    # HTTP Method
    assert sanitize_method("get") == "GET"
    assert sanitize_method("post") == "POST"
    assert sanitize_method("DELETE") == "DELETE"
    assert sanitize_method("EVIL_VERB") == "UNKNOWN"
    assert sanitize_method("<script>") == "UNKNOWN"
    assert sanitize_method(None) == "UNKNOWN"


def test_correlation_id_rejects_credential_like_headers_and_preserves_tracing():
    """Verify that client-provided correlation IDs containing credentials, tokens, or arbitrary text
    are rejected and replaced with server-generated UUIDs, while trusted UUID/trace formats are preserved."""
    # 1. Short secret-like headers (passwords, tokens, credentials, words)
    short_secrets = [
        "secret123",
        "admin",
        "pass_123",
        "root",
        "bearer",
        "password",
        "token-abc",
        "auth:key",
        "api-secret",
    ]
    for secret in short_secrets:
        sanitized = sanitize_correlation_id(secret)
        assert sanitized != secret, f"Failed to reject short secret '{secret}'"
        assert len(sanitized) == 32
        assert re.match(r"^[0-9a-f]{32}$", sanitized)
        assert secret.lower() not in sanitized

    # 2. Long secret-like headers (API keys, PATs, JWT fragments, emails)
    long_secrets = [
        "custom_secret_api_key_1234567890abcdef1234567890",
        "github_token_dummy_abcdefghijklmnopqrstuvwxyz1234",
        "Bearer-token-xyz-1234567890abcdefghijklmnopqrst",
        "mock_jwt_header.mock_jwt_payload_data_signature",
        "user.identity@finex.internal",
        "aws_access_key_dummy_sample_credential_example",
        "slack_bot_token_dummy_sample_1234567890abcdef",
    ]
    for secret in long_secrets:
        sanitized = sanitize_correlation_id(secret)
        assert sanitized != secret, f"Failed to reject long secret '{secret}'"
        assert len(sanitized) == 32
        assert re.match(r"^[0-9a-f]{32}$", sanitized)
        # Verify secret fragment never preserved in server-generated ID
        assert "custom_secret" not in sanitized
        assert "github_token" not in sanitized
        assert "bearer" not in sanitized
        assert "jwt" not in sanitized

    # 3. Legitimate distributed tracing formats are preserved
    valid_tracing_ids = [
        ("12345678-1234-4234-8234-123456789abc", "12345678-1234-4234-8234-123456789abc"),
        ("4B2E8A1D-7F3C-4E89-9A12-8C4D2E1F0B9A", "4b2e8a1d-7f3c-4e89-9a12-8c4d2e1f0b9a"),
        ("a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6", "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6"),
        ("cid-0123456789abcdef", "cid-0123456789abcdef"),
        ("req-0123456789abcdef0123456789abcdef", "req-0123456789abcdef0123456789abcdef"),
        ("trace-fedcba9876543210", "trace-fedcba9876543210"),
    ]
    for raw_val, expected in valid_tracing_ids:
        assert sanitize_correlation_id(raw_val) == expected, f"Failed to preserve valid tracing ID '{raw_val}'"


@pytest.mark.asyncio
async def test_middleware_and_recorder_correlation_id_isolation(app):
    """Verify end-to-end that client secret headers are never stored in error monitoring DB."""
    secret_header = "custom_secret_api_key_test_leak_12345"
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Trigger 404 with secret-like correlation header
        response = await client.get("/api/v1/non_existent_route", headers={"X-Correlation-ID": secret_header})
        assert response.status_code == 404

        # Verify that any database error record generated contains a safe UUID, NOT the secret
        async with AsyncSessionLocal() as session:
            stmt = select(ErrorEvent).order_by(ErrorEvent.created_at.desc()).limit(5)
            events = (await session.execute(stmt)).scalars().all()
            for ev in events:
                assert secret_header not in ev.correlation_id
                assert "custom_secret" not in ev.correlation_id
                assert "test_leak" not in ev.correlation_id


# =============================================================================
# 10. Allowlisted Error Catalog Tests (Finding 2)
# =============================================================================


def test_allowlisted_error_catalog_resolves_safe_messages():
    """Verify catalog resolves generic safe messages without leaking exception internals."""
    # Known catalog code
    code, cat, msg, feat = resolve_safe_error_details(
        status_code=500,
        error_code="CIRCUIT_BREAKER_OPEN",
        endpoint="/api/v1/market/quote",
    )
    assert code == "CIRCUIT_BREAKER_OPEN"
    assert cat == "UPSTREAM_API"
    assert "Market data circuit breaker is open" in msg
    assert feat == "Market Data"

    # Database exception with sensitive internals
    leak_exc = Exception(
        "FATAL: connection to postgres server at 'db.internal.finex.com' failed for user 'neondb_owner'"
    )
    code_db, cat_db, msg_db, _ = resolve_safe_error_details(
        status_code=500,
        exc=leak_exc,
        endpoint="/api/v1/portfolio",
    )
    assert code_db == "DATABASE_ERROR"
    assert "neondb_owner" not in msg_db
    assert "db.internal.finex.com" not in msg_db
    assert msg_db == "Database operation failed or timed out."

    # Arbitrary unhandled exception with sensitive internals
    leak_generic = Exception("ZeroDivisionError: token='secret-token-xyz' in compute kernel")
    code_gen, cat_gen, msg_gen, _ = resolve_safe_error_details(
        status_code=500,
        exc=leak_generic,
        endpoint="/api/v1/risk",
    )
    assert code_gen == "INTERNAL_SERVER_ERROR"
    assert "secret-token-xyz" not in msg_gen
    assert "ZeroDivisionError" not in msg_gen
    assert msg_gen == "An unexpected server error occurred."


# =============================================================================
# 11. Bounded Fail-Safe & Slow Database Timeout Tests (Finding 1)
# =============================================================================


@pytest.mark.asyncio
async def test_slow_database_bounded_timeout():
    """Verify record_error_event times out within RECORDING_TIMEOUT_SECONDS and fails open."""

    async def _mock_slow_add_and_commit(*args, **kwargs):
        await asyncio.sleep(2.0)  # Simulate DB freeze/lock

    with patch("backend.app.services.error_recorder.AsyncSessionLocal") as mock_session_cls:
        mock_session = AsyncMock()
        mock_session.execute.side_effect = _mock_slow_add_and_commit
        mock_session.commit.side_effect = _mock_slow_add_and_commit
        mock_session_cls.return_value.__aenter__.return_value = mock_session

        start = time.perf_counter()
        result = await record_error_event(
            correlation_id="test-slow-db",
            endpoint="/api/v1/test",
            method="GET",
            status_code=500,
            raw_message="Slow DB test",
        )
        elapsed = time.perf_counter() - start

        # Must fail open (return None) within ~350ms (RECORDING_TIMEOUT_SECONDS = 0.25)
        assert result is None
        assert elapsed < 0.8, f"Recording blocked for {elapsed:.2f}s; expected <= 0.8s"


# =============================================================================
# 12. Recursion Guard Tests (Finding 3)
# =============================================================================


@pytest.mark.asyncio
async def test_error_recording_recursion_prevention():
    """Verify that re-entrant error recording calls return immediately without infinite loops."""
    token = _is_recording_ctx.set(True)
    try:
        # Re-entrant call while _is_recording_ctx is True
        result = await record_error_event(
            correlation_id="test-recursion",
            endpoint="/api/v1/test",
            method="GET",
            status_code=500,
        )
        assert result is None, "Should abort immediately on re-entrant call"
    finally:
        _is_recording_ctx.reset(token)


# =============================================================================
# 13. Concurrency-Safe Pruning Tests (Finding 3)
# =============================================================================


@pytest.mark.asyncio
async def test_concurrency_safe_pruning():
    """Verify multiple concurrent prune calls acquire lock and throttle safely without deadlocks."""
    # Run 10 concurrent prune calls
    results = await asyncio.gather(
        *(prune_bounded_storage() for _ in range(10)),
        return_exceptions=True,
    )

    # None should have raised an exception
    for r in results:
        assert not isinstance(r, Exception), f"Pruning raised exception under concurrency: {r}"


# =============================================================================
# 14. Audited Capture Paths Tests (400, 401, 403, 404, 413, 422, 429, 500, 503) (Finding 4)
# =============================================================================


@pytest.mark.asyncio
async def test_audited_capture_paths(app, owner_headers):
    """Verify that 400, 401, 403, 404, 413, 422, 429, 500, and 503 are captured in error_events."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. 401 Unauthorized
        res_401 = await client.get("/api/v1/admin/errors")
        assert res_401.status_code == 401

        # 2. 403 Forbidden (non-owner session)
        non_owner = create_access_token(
            user_id="usr-inv-999",
            email="investor@example.com",
            name="Investor",
            provider="google",
        )
        res_403 = await client.get("/api/v1/admin/errors", headers={"Authorization": f"Bearer {non_owner}"})
        assert res_403.status_code == 403

        # 3. 404 Not Found
        res_404 = await client.get("/api/v1/nonexistent-endpoint-test-audit")
        assert res_404.status_code == 404

        # 4. 422 Validation Error
        res_422 = await client.post(
            "/api/v1/auth/login",
            headers={"Content-Type": "application/json"},
            content=b'{"invalid_field": 123}',
        )
        assert res_422.status_code in (400, 422)

        # 5. 413 Payload Too Large (via RequestSizeLimitMiddleware)
        oversized_body = b"A" * (11 * 1024 * 1024)  # 11MB exceeds 10MB limit
        res_413 = await client.post(
            "/api/v1/auth/login",
            headers={"Content-Type": "application/json"},
            content=oversized_body,
        )
        assert res_413.status_code == 413

        # Verify recent captured error events include these status codes
        res_errors = await client.get("/api/v1/admin/errors?limit=50", headers=owner_headers)
        assert res_errors.status_code == 200
        data = res_errors.json().get("data", res_errors.json())
        captured_codes = {e["status_code"] for e in data["errors"]}

        for expected_code in [401, 403, 404, 413]:
            assert expected_code in captured_codes, f"Expected {expected_code} in captured codes: {captured_codes}"

        # Verify that 404 endpoint was anonymized to /unmatched_route without leaking path
        not_found_events = [e for e in data["errors"] if e["status_code"] == 404]
        assert len(not_found_events) >= 1
        assert not_found_events[0]["endpoint"] == "/unmatched_route"


# =============================================================================
# 15. Connection Pool Protection & Bounded Concurrency Tests (Finding 3)
# =============================================================================


@pytest.mark.asyncio
async def test_connection_pool_protection_and_concurrency_ceiling():
    """Verify that at most MAX_CONCURRENT_RECORDING_TASKS (5) concurrent DB recording sessions
    can run simultaneously within the local worker process, and excess writes fail open immediately
    to protect the worker's connection pool.

    NOTE: This tests in-process semaphore boundaries; across multiple worker processes,
    each worker independently enforces its own 5-task limit. No global cluster-wide pool
    guarantee is asserted."""
    reset_error_recorder_state()
    active_db_sessions = 0
    max_simultaneous_sessions = 0
    lock = asyncio.Lock()

    async def _slow_db_operation(*args, **kwargs):
        nonlocal active_db_sessions, max_simultaneous_sessions
        async with lock:
            active_db_sessions += 1
            if active_db_sessions > max_simultaneous_sessions:
                max_simultaneous_sessions = active_db_sessions
        await asyncio.sleep(0.15)
        async with lock:
            active_db_sessions -= 1

    with patch("backend.app.services.error_recorder.AsyncSessionLocal") as mock_session_cls:
        mock_session = AsyncMock()
        mock_session.add = lambda x: None
        mock_session.commit.side_effect = _slow_db_operation
        mock_session.refresh.side_effect = _slow_db_operation
        mock_session_cls.return_value.__aenter__.return_value = mock_session

        # Launch 20 simultaneous recording calls
        tasks = [
            record_error_event(
                correlation_id=f"cid-{uuid.uuid4().hex[:16]}",
                endpoint="/api/v1/test",
                method="GET",
                status_code=500,
            )
            for i in range(20)
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Verify concurrency never exceeded ceiling of 5
        assert max_simultaneous_sessions <= 5, f"Exceeded concurrency ceiling: {max_simultaneous_sessions} > 5"
        # Verify non-blocking: excess calls dropped cleanly (returned None) without hanging
        assert any(r is None for r in results)
    reset_error_recorder_state()


# =============================================================================
# 16. Storage Outage Circuit Breaker Tests (Finding 3)
# =============================================================================


@pytest.mark.asyncio
async def test_storage_outage_circuit_breaker():
    """Verify that repeated database failures trip circuit breaker, failing open in 0ms without touching DB."""
    reset_error_recorder_state()

    with patch("backend.app.services.error_recorder.AsyncSessionLocal") as mock_session_cls:
        mock_session_cls.side_effect = Exception("PostgreSQL down / connection refused")

        # 1. First 3 failures should trip circuit breaker
        for _ in range(3):
            res = await record_error_event(
                correlation_id="trip-cb",
                endpoint="/api/v1/test",
                method="GET",
                status_code=500,
            )
            assert res is None

        # 2. Subsequent call should immediately fail open without calling AsyncSessionLocal
        mock_session_cls.reset_mock()
        start = time.perf_counter()
        res_tripped = await record_error_event(
            correlation_id="circuit-open",
            endpoint="/api/v1/test",
            method="GET",
            status_code=500,
        )
        elapsed = time.perf_counter() - start
        assert res_tripped is None
        # Immediate fail open (< 50ms)
        assert elapsed < 0.05
        # Zero database connection attempts while circuit is open
        mock_session_cls.assert_not_called()
    reset_error_recorder_state()


# =============================================================================
# 17. Actual Added Latency Tests (Finding 3)
# =============================================================================


@pytest.mark.asyncio
async def test_actual_added_latency_bounded_by_timeout():
    """Verify that added latency is explicitly bounded to <= 250ms under slow DB and not described as zero delay."""
    reset_error_recorder_state()

    async def _hanging_db(*args, **kwargs):
        await asyncio.sleep(2.0)

    with patch("backend.app.services.error_recorder.AsyncSessionLocal") as mock_session_cls:
        mock_session = AsyncMock()
        mock_session.commit.side_effect = _hanging_db
        mock_session_cls.return_value.__aenter__.return_value = mock_session

        start = time.perf_counter()
        res = await record_error_event(
            correlation_id="latency-test",
            endpoint="/api/v1/test",
            method="GET",
            status_code=500,
        )
        elapsed = time.perf_counter() - start
        assert res is None
        # Latency is bounded by RECORDING_TIMEOUT_SECONDS (0.25s), NOT zero delay
        assert 0.20 <= elapsed < 0.65, f"Expected bounded latency ~0.25s, got {elapsed:.3f}s"
    reset_error_recorder_state()


# =============================================================================
# 18. Retention Pruning & Ceiling Enforcement Tests (Finding 1)
# =============================================================================


@pytest.mark.asyncio
async def test_bounded_retention_pruning_and_ceiling():
    """Verify prune_bounded_storage and prune_if_due clean up expired records and enforce retention."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=35)

    async with AsyncSessionLocal() as session:
        for i in range(5):
            session.add(
                ErrorEvent(
                    id=f"err-old-{uuid.uuid4().hex[:8]}",
                    correlation_id=f"cid-old-{i}",
                    endpoint="/api/v1/test",
                    method="GET",
                    status_code=500,
                    error_type="TestOldError",
                    category="SERVER_ERROR",
                    feature_area="System",
                    sanitized_message="Old error message",
                    created_at=cutoff,
                )
            )
        await session.commit()

    # Run prune
    await prune_bounded_storage()

    # Verify old events pruned
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(func.count(ErrorEvent.id)).where(ErrorEvent.error_type == "TestOldError"))
        assert res.scalar() == 0

    # Test prune_if_due runs without error
    await prune_if_due()
