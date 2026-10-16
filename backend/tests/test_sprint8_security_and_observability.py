"""Sprint 8: Security Hardening, Observability, Token Lifecycle, and Multi-Tenant Isolation Tests.

Tasks: S8-API-01, S8-API-02
Author: Shivraj Dhote
"""

import pytest
from backend.app.core.middleware import RateLimiterMiddleware
from backend.app.factory import create_app
from backend.app.routers.auth import create_access_token, revoke_token
from backend.app.routers.health import set_database_health_checker
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


def test_security_headers_present(client):
    """S8-API-01: Verify defensive security headers on all responses."""
    resp = client.get("/api/v1/health/live")
    assert resp.status_code == 200
    headers = resp.headers
    assert headers.get("X-Content-Type-Options") == "nosniff"
    assert headers.get("X-Frame-Options") == "DENY"
    assert headers.get("Strict-Transport-Security") == "max-age=31536000; includeSubDomains"
    assert headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert "default-src 'self'" in headers.get("Content-Security-Policy", "")
    assert "geolocation=()" in headers.get("Permissions-Policy", "")


def test_observability_correlation_and_latency_headers(client):
    """S8-API-02: Verify correlation ID, request ID, and timing metadata propagation."""
    custom_cid = "trace-test-uuid-9999"
    resp = client.get("/api/v1/health/live", headers={"X-Correlation-ID": custom_cid})
    assert resp.status_code == 200
    assert resp.headers.get("X-Correlation-ID") == custom_cid
    assert resp.headers.get("X-Request-ID") == custom_cid
    assert "X-Response-Time-Ms" in resp.headers
    response_time = float(resp.headers["X-Response-Time-Ms"])
    assert response_time >= 0.0


def test_token_revocation_and_refresh_lifecycle(client):
    """S8-API-01: Verify JWT revocation immediately denies access and single-use rotation."""
    token = create_access_token("usr-test-lifecycle", "lifecycle@finex.local", "Test User")
    auth_header = {"Authorization": f"Bearer {token}"}

    # 1. Active token succeeds
    resp1 = client.get("/api/v1/users/me", headers=auth_header)
    assert resp1.status_code == 200
    assert resp1.json()["data"]["user_id"] == "usr-test-lifecycle"

    # 2. Refresh / rotate token
    refresh_resp = client.post("/api/v1/auth/refresh", headers=auth_header)
    assert refresh_resp.status_code == 200
    new_token = refresh_resp.json()["data"]["access_token"]
    assert new_token != token

    # 3. Old token is now revoked and rejected
    resp_old = client.get("/api/v1/users/me", headers=auth_header)
    assert resp_old.status_code == 401

    # 4. New token succeeds
    new_auth_header = {"Authorization": f"Bearer {new_token}"}
    resp_new = client.get("/api/v1/users/me", headers=new_auth_header)
    assert resp_new.status_code == 200

    # 5. Explicit revocation
    revoke_resp = client.post("/api/v1/auth/revoke", headers=new_auth_header)
    assert revoke_resp.status_code == 200
    assert revoke_resp.json()["data"]["revoked"] is True

    # 6. Now new token is also rejected
    resp_revoked = client.get("/api/v1/users/me", headers=new_auth_header)
    assert resp_revoked.status_code == 401


def test_request_size_limit_enforcement(client):
    """S8-API-01: Verify oversized request payloads are safely rejected before processing."""
    # 3 MB payload sent to standard JSON endpoint (limit 2 MB)
    oversized_headers = {
        "Content-Length": str(3 * 1024 * 1024),
        "Content-Type": "application/json",
    }
    resp = client.post("/api/v1/auth/google", data="{}", headers=oversized_headers)
    assert resp.status_code == 413
    assert resp.json()["error"]["code"] == "PAYLOAD_TOO_LARGE"


def test_dependency_aware_readiness_probe_healthy_and_degraded(client):
    """S8-API-02: Verify /readyz fails with 503 when dependency fails, while /healthz remains 200."""
    try:
        # 1. Healthy state
        set_database_health_checker(lambda: {"connections": 5, "latency_ms": 1.2})
        resp_healthy = client.get("/api/v1/health/ready")
        assert resp_healthy.status_code == 200
        assert resp_healthy.json()["data"]["status"] == "ok"

        # 2. Degraded state (e.g. Postgres disconnect)
        def faulty_checker():
            raise ConnectionError("Database unreachable")

        set_database_health_checker(faulty_checker)
        resp_degraded = client.get("/api/v1/health/ready")
        assert resp_degraded.status_code == 503
        assert resp_degraded.json()["data"]["status"] == "degraded"

        # Liveness must remain healthy even when database is degraded
        resp_liveness = client.get("/api/v1/health/live")
        assert resp_liveness.status_code == 200
        assert resp_liveness.json()["data"]["status"] == "ok"
    finally:
        set_database_health_checker(None)


def test_multi_tenant_cross_user_isolation(client):
    """S8-API-01: Verify strict cross-user data isolation between tenants."""
    user1_headers = {"Authorization": "Bearer test-dev-token-sub-usr-tenant-001"}
    user2_headers = {"Authorization": "Bearer test-dev-token-sub-usr-tenant-002"}

    # 1. User 1 creates an alert rule
    alert_payload = {
        "rule_type": "PRICE_ABOVE",
        "symbol": "TCS",
        "comparison_operator": ">=",
        "threshold_value": 4500.0,
        "threshold_unit": "INR",
        "cooldown_minutes": 60,
    }
    create_alert = client.post("/api/v1/alerts/rules", json=alert_payload, headers=user1_headers)
    assert create_alert.status_code == 201
    rule_id = create_alert.json()["data"]["id"]


    # User 2 list rules -> must NOT see User 1's rule
    user2_rules = client.get("/api/v1/alerts/rules", headers=user2_headers)
    assert user2_rules.status_code == 200
    user2_rule_ids = [r["id"] for r in user2_rules.json()["data"]["rules"]]
    assert rule_id not in user2_rule_ids

    # 2. User 1 creates a financial goal
    goal_payload = {
        "title": "Tenant 1 Emergency Fund",
        "category": "EMERGENCY_FUND",
        "target_amount": 300000.0,
        "current_amount": 50000.0,
        "target_date": "2027-12-31",
        "assumed_annual_return_pct": 8.0,
    }
    create_goal = client.post("/api/v1/goals", json=goal_payload, headers=user1_headers)
    assert create_goal.status_code == 201
    goal_id = create_goal.json()["data"]["id"]


    # User 2 cannot access or view User 1's goal
    user2_get_goal = client.get(f"/api/v1/goals/{goal_id}", headers=user2_headers)
    assert user2_get_goal.status_code == 404

    # User 2 list goals -> must NOT contain User 1's goal
    user2_goals = client.get("/api/v1/goals", headers=user2_headers)
    assert user2_goals.status_code == 200
    user2_goal_ids = [g["id"] for g in user2_goals.json()["data"]["goals"]]
    assert goal_id not in user2_goal_ids


def test_rate_limiter_burst_enforcement():
    """S8-API-01: Direct test on RateLimiterMiddleware to verify 429 and Retry-After."""
    from fastapi import FastAPI
    from fastapi.responses import PlainTextResponse

    small_app = FastAPI()
    # Configure tiny limit for testing: 3 req / 60 sec
    small_app.add_middleware(RateLimiterMiddleware, default_limit=3, auth_limit=2, window_seconds=10)

    @small_app.get("/test-rate")
    def sample():
        return PlainTextResponse("OK")

    test_c = TestClient(small_app)

    # 3 allowed requests
    assert test_c.get("/test-rate").status_code == 200
    assert test_c.get("/test-rate").status_code == 200
    assert test_c.get("/test-rate").status_code == 200

    # 4th request must be rejected with 429
    fourth = test_c.get("/test-rate")
    assert fourth.status_code == 429
    assert fourth.headers.get("Retry-After") is not None
    assert fourth.json()["error"]["code"] == "RATE_LIMIT_EXCEEDED"
