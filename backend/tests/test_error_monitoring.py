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

import uuid
from unittest.mock import patch

import pytest
from backend.app.config import get_settings
from backend.app.database import engine
from backend.app.factory import create_app
from backend.app.models import Base
from backend.app.routers.auth import create_access_token
from backend.app.services.error_recorder import (
    categorize_error,
    prune_bounded_storage,
    record_error_event,
    sanitize_error_message,
)
from httpx import ASGITransport, AsyncClient


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
    test_corr_id = f"test-cid-{uuid.uuid4().hex[:12]}"
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
    assert "password=[REDACTED]" in event.sanitized_message

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
        assert "password=[REDACTED]" in item["sanitized_message"]
        assert "superSecretPassword!" not in item["sanitized_message"]


# =============================================================================
# 4. Pagination, Sorting, and Filtering Tests
# =============================================================================


@pytest.mark.asyncio
async def test_errors_filtering_and_pagination(app, owner_headers):
    """Verify filtering by status_code, category, and pagination mechanics."""
    tag = uuid.uuid4().hex[:8]

    # Create 3 distinct events with unique searchable tag
    await record_error_event(
        correlation_id=f"c1-{tag}",
        endpoint="/api/v1/auth/google",
        method="POST",
        status_code=500,
        error_type="GoogleOAuthError",
        raw_message=f"Google OAuth token verification failed tag={tag}",
    )
    await record_error_event(
        correlation_id=f"c2-{tag}",
        endpoint="/api/v1/orders/paper",
        method="POST",
        status_code=422,
        error_type="RequestValidationError",
        raw_message=f"Invalid order quantity specified tag={tag}",
    )
    await record_error_event(
        correlation_id=f"c3-{tag}",
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
