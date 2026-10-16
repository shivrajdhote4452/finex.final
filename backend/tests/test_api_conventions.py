import pytest
from backend.app.factory import create_app
from httpx import ASGITransport, AsyncClient


@pytest.fixture
def app():
    return create_app()


@pytest.mark.asyncio
async def test_correlation_id_propagation(app):
    custom_cid = "test-custom-correlation-uuid-9999"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            "/api/v1/health/live",
            headers={"X-Correlation-ID": custom_cid},
        )
        assert response.status_code == 200
        assert response.headers.get("X-Correlation-ID") == custom_cid
        body = response.json()
        assert body["meta"]["correlation_id"] == custom_cid


@pytest.mark.asyncio
async def test_security_headers_present(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/health/live")
        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        assert response.headers.get("X-Frame-Options") == "DENY"
        assert "max-age" in response.headers.get("Strict-Transport-Security", "")


@pytest.mark.asyncio
async def test_sample_calculate_success_envelope_200(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {"quantity": "10.5", "price": "2500.00", "trigger_error": False}
        response = await client.post("/api/v1/sample/calculate", json=payload)
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert float(body["data"]["market_value"]) == 26250.0
        assert body["data"]["currency"] == "INR"
        assert "correlation_id" in body["meta"]


@pytest.mark.asyncio
async def test_sample_calculate_validation_error_422(app):
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test"
    ) as client:
        # Invalid payload: negative quantity
        payload = {"quantity": "-5", "price": "100.00"}
        response = await client.post("/api/v1/sample/calculate", json=payload)
        assert response.status_code == 422
        body = response.json()
        assert body["success"] is False
        assert body["error"]["code"] == "VALIDATION_ERROR"
        assert len(body["error"]["details"]) > 0
        assert "quantity" in body["error"]["details"][0]["field"]


@pytest.mark.asyncio
async def test_sample_calculate_unhandled_error_500(app):
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test"
    ) as client:
        payload = {"quantity": "10", "price": "100", "trigger_error": True}
        response = await client.post("/api/v1/sample/calculate", json=payload)
        assert response.status_code == 500
        body = response.json()
        assert body["success"] is False
        assert body["error"]["code"] == "INTERNAL_SERVER_ERROR"
        assert "unexpected error" in body["error"]["message"]
        # Must NOT leak raw exception stack traces in response message
        assert "Deliberate" not in body["error"]["message"]
