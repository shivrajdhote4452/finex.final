import pytest
from backend.app.factory import create_app
from httpx import ASGITransport, AsyncClient


@pytest.fixture
def app():
    return create_app()


@pytest.mark.asyncio
async def test_protected_route_missing_token_returns_401(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/sample/protected")
        assert response.status_code == 401
        body = response.json()
        assert body["success"] is False
        assert body["error"]["code"] == "MISSING_TOKEN"


@pytest.mark.asyncio
async def test_protected_route_invalid_format_returns_401(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            "/api/v1/sample/protected",
            headers={"Authorization": "Basic invalid_format"},
        )
        assert response.status_code == 401
        body = response.json()
        assert body["error"]["code"] == "INVALID_TOKEN_FORMAT"


@pytest.mark.asyncio
async def test_protected_route_expired_token_returns_401(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            "/api/v1/sample/protected",
            headers={"Authorization": "Bearer expired-token"},
        )
        assert response.status_code == 401
        body = response.json()
        assert body["error"]["code"] == "TOKEN_EXPIRED"


@pytest.mark.asyncio
async def test_protected_route_valid_token_returns_200(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            "/api/v1/sample/protected",
            headers={"Authorization": "Bearer test-user-token"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["data"]["user_id"] == "11111111-2222-3333-4444-555555555555"
        assert body["data"]["role"] == "developer"
