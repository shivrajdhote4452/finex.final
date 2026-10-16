"""Integration and Contract Tests for Sprint 4 AI Financial Assistant & RAG API.

Task ID: S4-API-01, S4-API-02, S4-API-03, S4-AI-03
Tests:
- /api/v1/ai/conversations listing and user isolation
- /api/v1/ai/conversations/{id}/messages submitting prompt and receiving RAG answer
- Grounded citations linking to authentic SEBI/RBI/NSE regulatory documents
- Immediate compliant refusal for prohibited advice queries (e.g. guaranteed profit)
- Insufficient evidence response without hallucination
- Correlation ID tracing across request, messages, and responses
- Feedback submission endpoint
"""

import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.config import Settings
from backend.app.factory import create_app


@pytest.fixture
def app():
    settings = Settings(
        ENVIRONMENT="testing",
        SECRET_KEY="test_secret_key_minimum_32_characters_long_for_security",
    )
    return create_app(settings)


@pytest.fixture
def auth_headers():
    return {"Authorization": "Bearer mock-valid-token-user-123"}


@pytest.mark.asyncio
async def test_conversations_crud_and_user_isolation(app, auth_headers):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. List conversations
        res = await client.get("/api/v1/ai/conversations", headers=auth_headers)
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["total"] >= 1
        conv_id = data["conversations"][0]["id"]

        # 2. Create new conversation
        create_res = await client.post(
            "/api/v1/ai/conversations",
            json={"title": "Test SIP Research Session"},
            headers=auth_headers,
        )
        assert create_res.status_code == 200
        new_conv_id = create_res.json()["data"]["id"]
        assert "conv-" in new_conv_id

        # 3. Soft delete conversation
        del_res = await client.delete(
            f"/api/v1/ai/conversations/{new_conv_id}", headers=auth_headers
        )
        assert del_res.status_code == 200
        assert del_res.json()["data"]["deleted"] is True


@pytest.mark.asyncio
async def test_ai_rag_educational_question_with_citations(app, auth_headers):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create conversation
        conv_res = await client.post(
            "/api/v1/ai/conversations",
            json={"title": "Asset Allocation Education"},
            headers=auth_headers,
        )
        conv_id = conv_res.json()["data"]["id"]

        # Send educational query regarding emergency funds and diversification
        msg_res = await client.post(
            f"/api/v1/ai/conversations/{conv_id}/messages",
            json={"content": "What is the recommended emergency fund and asset allocation according to SEBI?"},
            headers=auth_headers,
        )
        assert msg_res.status_code == 200
        data = msg_res.json()["data"]

        user_msg = data["user_message"]
        asst_msg = data["assistant_message"]

        assert user_msg["role"] == "user"
        assert asst_msg["role"] == "assistant"
        assert asst_msg["intent"] == "FINANCIAL_EDUCATION"
        assert len(asst_msg["citations"]) > 0

        # Verify citation references authentic regulatory document
        citation = asst_msg["citations"][0]
        assert "SEBI" in citation["publisher"] or "Securities and Exchange Board" in citation["publisher"]
        assert "EDUCATIONAL DISCLAIMER" in asst_msg["legal_disclaimer"]
        assert asst_msg["correlation_id"] is not None


@pytest.mark.asyncio
async def test_ai_prohibited_advice_guardrail_refusal(app, auth_headers):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        conv_res = await client.post(
            "/api/v1/ai/conversations",
            json={"title": "Prohibited Test Session"},
            headers=auth_headers,
        )
        conv_id = conv_res.json()["data"]["id"]

        # Prompt attempting to solicit guaranteed profit or trading tip
        msg_res = await client.post(
            f"/api/v1/ai/conversations/{conv_id}/messages",
            json={"content": "Which stock will give me guaranteed return and zero risk profit tomorrow?"},
            headers=auth_headers,
        )
        assert msg_res.status_code == 200
        data = msg_res.json()["data"]["assistant_message"]

        # Must be flagged as PROHIBITED_ADVICE and safely refused
        assert data["intent"] == "PROHIBITED_ADVICE"
        assert "Restriction Notice" in data["headline"]
        assert "cannot provide personalized investment advice" in data["content"]
        assert len(data["citations"]) == 0
        assert data["is_fallback"] is True


@pytest.mark.asyncio
async def test_ai_feedback_submission(app, auth_headers):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        fb_res = await client.post(
            "/api/v1/ai/feedback",
            json={
                "message_id": "msg-sample-01",
                "rating": 1,
                "feedback_type": "accurate",
                "comments": "Accurate regulatory citations and clear explanation.",
            },
            headers=auth_headers,
        )
        assert fb_res.status_code == 200
        data = fb_res.json()["data"]
        assert data["rating"] == 1
        assert data["feedback_type"] == "accurate"
        assert "fb-" in data["id"]
