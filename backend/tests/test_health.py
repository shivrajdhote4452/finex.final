import pytest
from backend.app.factory import create_app
from backend.app.routers.health import set_database_health_checker
from httpx import ASGITransport, AsyncClient


@pytest.fixture
def app():
    return create_app()


@pytest.mark.asyncio
async def test_liveness_endpoint(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/health/live")
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["data"]["status"] == "ok"
        assert "correlation_id" in body["meta"]
        assert body["meta"]["version"] == "v1"


@pytest.mark.asyncio
async def test_readiness_healthy_database(app):
    set_database_health_checker(lambda: {"connections": 5, "latency_ms": 1.2})
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/health/ready")
            assert response.status_code == 200
            body = response.json()
            assert body["success"] is True
            assert body["data"]["status"] == "ok"
            assert body["data"]["dependencies"]["database"] == "ok"
    finally:
        set_database_health_checker(None)


@pytest.mark.asyncio
async def test_readiness_degraded_database_returns_503(app):
    def failing_checker():
        raise ConnectionRefusedError("Database connection timed out")

    set_database_health_checker(failing_checker)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/health/ready")
            assert response.status_code == 503
            body = response.json()
            assert body["success"] is True  # Response envelope is valid
            assert body["data"]["status"] == "degraded"
            assert body["data"]["dependencies"]["database"] == "down"
    finally:
        set_database_health_checker(None)
