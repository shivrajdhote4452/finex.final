"""Tests for AskFinEx Groq-only LLM integration, timeout controls, status reporting, and fallback behavior."""

from unittest.mock import AsyncMock, MagicMock, patch
import httpx
import pytest
from backend.app.config import Settings
from backend.app.domain.gemini_assistant import GeminiInvestmentAssistant, gemini_assistant
from backend.app.factory import create_app
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


# ------------------------------------------------------------------------------
# 1. Missing Key & Unconfigured Degradation
# ------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_groq_missing_key_graceful_degradation():
    """Verify that when GROQ_API_KEY is missing or placeholder, safe local fallback operates cleanly."""
    mock_settings = Settings(
        GROQ_API_KEY="YOUR_GROQ_API_KEY_HERE",
        LLM_PROVIDER="groq",
    )
    assistant = GeminiInvestmentAssistant(settings=mock_settings)

    assert assistant.is_groq_api_ready() is False
    assert assistant.is_llm_ready() is False
    assert assistant.is_configured() is False
    assert assistant.is_verified_working() is False

    info = assistant.get_provider_info()
    assert info["provider"] == "mock-offline"
    assert info["model"] == "deterministic-engine"

    # Verify live verification immediately returns False without network calls
    assert await assistant.verify_live_connection() is False

    # Verify processing a user turn yields safe deterministic response without errors
    res = await assistant.process_user_turn(
        user_id="usr-test-01",
        user_message="Hello, how does FinEx help me?",
    )
    assert res.reply is not None
    assert len(res.reply) > 0
    assert res.is_setup_incomplete is False


# ------------------------------------------------------------------------------
# 2. Explicit Offline Mode
# ------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_groq_explicit_offline_mode():
    """Verify that when LLM_PROVIDER is set to offline/mock, assistant reports offline regardless of key."""
    mock_settings = Settings(
        GROQ_API_KEY="gsk_valid_mock_key_1234567890",
        LLM_PROVIDER="offline",
    )
    assistant = GeminiInvestmentAssistant(settings=mock_settings)

    # API key is present, but provider is explicitly offline
    assert assistant.is_groq_api_ready() is True
    assert assistant.is_llm_ready() is False
    assert assistant.is_configured() is False
    assert assistant.is_verified_working() is False

    info = assistant.get_provider_info()
    assert info["provider"] == "mock-offline"
    assert info["model"] == "deterministic-engine"

    # call_groq_api returns None immediately
    assert await assistant.call_groq_api("ping", "pong") is None

    # process_user_turn directly returns deterministic response without calling call_groq_api
    with patch.object(assistant, "call_groq_api", new_callable=AsyncMock) as mock_groq:
        res = await assistant.process_user_turn(
            user_id="usr-test-01",
            user_message="What are top stocks?",
        )
        assert res.reply is not None
        mock_groq.assert_not_called()


# ------------------------------------------------------------------------------
# 3. Successful Groq Call & Live Verification
# ------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_groq_success_and_live_status():
    """Verify that valid Groq response marks assistant live and returns synthesized reply."""
    mock_settings = Settings(
        GROQ_API_KEY="gsk_valid_mock_key_1234567890",
        GROQ_MODEL="openai/gpt-oss-120b",
        LLM_PROVIDER="groq",
    )
    assistant = GeminiInvestmentAssistant(settings=mock_settings)

    assert assistant.is_groq_api_ready() is True
    assert assistant.is_llm_ready() is True
    assert assistant.is_configured() is True
    assert assistant.is_verified_working() is False  # not yet verified

    info_before = assistant.get_provider_info()
    assert info_before["provider"] == "groq-configured"

    # Simulate HTTP 200 response with usable message content
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [
            {"message": {"content": "Groq LPU synthesized technical momentum analysis for NSE equities."}}
        ]
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response):
        reply = await assistant.call_groq_api("Evaluate market", "You are an assistant")
        assert reply == "Groq LPU synthesized technical momentum analysis for NSE equities."
        assert assistant.is_verified_working() is True

        info_after = assistant.get_provider_info()
        assert info_after["provider"] == "groq-live"
        assert info_after["model"] == "openai/gpt-oss-120b"


# ------------------------------------------------------------------------------
# 4. HTTP 200 Without Usable Response Does Not Mark Live
# ------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_groq_http_200_empty_content_does_not_mark_live():
    """Verify that an HTTP 200 with empty choices or whitespace content does not mark provider live."""
    mock_settings = Settings(
        GROQ_API_KEY="gsk_valid_mock_key_1234567890",
        GROQ_MODEL="openai/gpt-oss-120b",
        LLM_PROVIDER="groq",
    )
    assistant = GeminiInvestmentAssistant(settings=mock_settings)

    # Case A: Choices array is empty
    mock_resp_empty_choices = MagicMock(spec=httpx.Response)
    mock_resp_empty_choices.status_code = 200
    mock_resp_empty_choices.json.return_value = {"choices": []}

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp_empty_choices):
        reply = await assistant.call_groq_api("ping", "pong")
        assert reply is None
        assert assistant.is_verified_working() is False
        assert assistant.get_provider_info()["provider"] == "groq-configured"

    # Case B: Content is blank whitespace
    mock_resp_blank = MagicMock(spec=httpx.Response)
    mock_resp_blank.status_code = 200
    mock_resp_blank.json.return_value = {"choices": [{"message": {"content": "   "}}]}

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp_blank):
        reply = await assistant.call_groq_api("ping", "pong")
        assert reply is None
        assert assistant.is_verified_working() is False
        assert assistant.get_provider_info()["provider"] == "groq-configured"


# ------------------------------------------------------------------------------
# 5. Timeout & Connection Error Fallback Promptness
# ------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_groq_timeout_aborts_immediately_without_looping_all_models():
    """Verify that a request timeout halts immediately without trying remaining models."""
    mock_settings = Settings(
        GROQ_API_KEY="gsk_valid_mock_key_1234567890",
        GROQ_MODEL="openai/gpt-oss-120b",
        GROQ_TIMEOUT=5.0,
        LLM_PROVIDER="groq",
    )
    assistant = GeminiInvestmentAssistant(settings=mock_settings)

    call_count = 0

    async def mock_post(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        raise httpx.ReadTimeout("Groq read timed out after 5s")

    with patch("httpx.AsyncClient.post", side_effect=mock_post):
        reply = await assistant.call_groq_api("Evaluate market", "You are an assistant")
        assert reply is None
        # Must have aborted after first timeout instead of retrying across all models
        assert call_count == 1
        assert assistant.is_verified_working() is False


# ------------------------------------------------------------------------------
# 6. Provider Succeeds and Later Fails
# ------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_groq_provider_succeeds_and_later_fails():
    """Verify state transitions: unverified -> live on success -> configured on subsequent failure."""
    mock_settings = Settings(
        GROQ_API_KEY="gsk_valid_mock_key_1234567890",
        GROQ_MODEL="openai/gpt-oss-120b",
        LLM_PROVIDER="groq",
    )
    assistant = GeminiInvestmentAssistant(settings=mock_settings)

    # 1. Initially configured but unverified
    assert assistant.is_verified_working() is False
    assert assistant.get_provider_info()["provider"] == "groq-configured"

    # 2. First call succeeds
    mock_success = MagicMock(spec=httpx.Response)
    mock_success.status_code = 200
    mock_success.json.return_value = {
        "choices": [{"message": {"content": "Initial successful analysis."}}]
    }
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_success):
        reply1 = await assistant.call_groq_api("ping", "pong")
        assert reply1 == "Initial successful analysis."
        assert assistant.is_verified_working() is True
        assert assistant.get_provider_info()["provider"] == "groq-live"

    # 3. Later call fails (e.g. 500 error / key revoked / network down)
    mock_failure = MagicMock(spec=httpx.Response)
    mock_failure.status_code = 500
    mock_failure.text = "Internal Server Error"
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_failure):
        reply2 = await assistant.call_groq_api("ping", "pong")
        assert reply2 is None
        # State correctly drops back to unverified
        assert assistant.is_verified_working() is False
        assert assistant.get_provider_info()["provider"] == "groq-configured"


# ------------------------------------------------------------------------------
# 7. No Unnecessary Duplicate Groq Calls in process_user_turn
# ------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_no_duplicate_groq_calls_when_api_fails():
    """Verify that when Groq fails, process_user_turn makes exactly ONE call before falling back."""
    mock_settings = Settings(
        GROQ_API_KEY="gsk_valid_mock_key_1234567890",
        GROQ_MODEL="openai/gpt-oss-120b",
        LLM_PROVIDER="groq",
    )
    assistant = GeminiInvestmentAssistant(settings=mock_settings)

    with patch.object(assistant, "call_groq_api", new_callable=AsyncMock) as mock_groq:
        mock_groq.return_value = None  # Groq fails/unavailable

        res = await assistant.process_user_turn(
            user_id="usr-test-01",
            user_message="What are the best stocks for tomorrow?",
        )

        # Verified: exactly ONE call was made, zero redundant duplicate calls
        assert mock_groq.call_count == 1
        # Fallback response is returned cleanly
        assert res.reply is not None
        assert "RELIANCE" in res.reply or "सत्यापित" in res.reply or "portfolio" in res.reply.lower()


# ------------------------------------------------------------------------------
# 8. Model Fallback on Model-Specific Error
# ------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_groq_fallback_model_on_model_not_found_error():
    """Verify that model-specific 404 cleanly attempts the fallback model within time budget."""
    mock_settings = Settings(
        GROQ_API_KEY="gsk_valid_mock_key_1234567890",
        GROQ_MODEL="custom/non-existent-model",
        LLM_PROVIDER="groq",
    )
    assistant = GeminiInvestmentAssistant(settings=mock_settings)

    call_models = []

    async def mock_post(url, json=None, headers=None):
        model = json.get("model")
        call_models.append(model)
        if model == "custom/non-existent-model":
            resp = MagicMock(spec=httpx.Response)
            resp.status_code = 404
            resp.text = "Model not found"
            return resp
        else:
            resp = MagicMock(spec=httpx.Response)
            resp.status_code = 200
            resp.json.return_value = {
                "choices": [{"message": {"content": "Fallback model response succeeded."}}]
            }
            return resp

    with patch("httpx.AsyncClient.post", side_effect=mock_post):
        reply = await assistant.call_groq_api("ping", "pong")
        assert reply == "Fallback model response succeeded."
        assert len(call_models) == 2
        assert call_models[0] == "custom/non-existent-model"
        assert assistant.is_verified_working() is True


# ------------------------------------------------------------------------------
# 9. Router Status Endpoint Reporting Consistency
# ------------------------------------------------------------------------------
def test_router_status_endpoint_offline_mode(client):
    """Verify /api/v1/ai/assistant/status reports consistent offline simulation mode when unconfigured."""
    with patch.object(gemini_assistant, "is_llm_ready", return_value=False), \
         patch.object(gemini_assistant, "is_configured", return_value=False), \
         patch.object(gemini_assistant, "is_verified_working", return_value=False), \
         patch.object(gemini_assistant, "get_provider_info", return_value={"provider": "mock-offline", "model": "deterministic-engine"}):
        res = client.get("/api/v1/ai/assistant/status")
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["is_configured"] is False
        assert data["has_live_groq"] is False
        assert data["has_live_llm"] is False
        assert data["is_verified_working"] is False
        assert data["provider"] == "mock-offline"
        assert "simulation mode" in data["status_message"].lower()


def test_router_status_endpoint_live_mode(client):
    """Verify /api/v1/ai/assistant/status reports live Groq status when verified."""
    with patch.object(gemini_assistant, "is_llm_ready", return_value=True), \
         patch.object(gemini_assistant, "is_configured", return_value=True), \
         patch.object(gemini_assistant, "is_verified_working", return_value=True), \
         patch.object(gemini_assistant, "get_provider_info", return_value={"provider": "groq-live", "model": "openai/gpt-oss-120b"}):
        res = client.get("/api/v1/ai/assistant/status")
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["is_configured"] is True
        assert data["has_live_groq"] is True
        assert data["has_live_llm"] is True
        assert data["is_verified_working"] is True
        assert data["provider"] == "groq-live"
        assert "verified working live" in data["status_message"].lower()


def test_router_status_endpoint_configured_but_unverified_mode(client):
    """Verify /api/v1/ai/assistant/status reports configured (unverified) status when API verification fails."""
    with patch.object(gemini_assistant, "is_llm_ready", return_value=True), \
         patch.object(gemini_assistant, "is_configured", return_value=True), \
         patch.object(gemini_assistant, "is_verified_working", return_value=False), \
         patch.object(gemini_assistant, "verify_live_connection", new_callable=AsyncMock, return_value=False), \
         patch.object(gemini_assistant, "get_provider_info", return_value={"provider": "groq-configured", "model": "openai/gpt-oss-120b"}):
        res = client.get("/api/v1/ai/assistant/status")
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["is_configured"] is True
        assert data["has_live_groq"] is False
        assert data["has_live_llm"] is False
        assert data["is_verified_working"] is False
        assert data["provider"] == "groq-configured"
        assert "is configured" in data["status_message"].lower()
