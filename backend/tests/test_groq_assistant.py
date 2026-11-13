"""Tests for AskFinEx Groq-only LLM integration and fallback behavior."""

from unittest.mock import AsyncMock, patch
import pytest
from backend.app.config import Settings
from backend.app.domain.gemini_assistant import GeminiInvestmentAssistant


@pytest.mark.asyncio
async def test_groq_unconfigured_graceful_degradation():
    """Verify that when GROQ_API_KEY is missing or placeholder, safe local fallback operates cleanly."""
    mock_settings = Settings(
        GROQ_API_KEY="YOUR_GROQ_API_KEY_HERE",
        LLM_PROVIDER="groq",
    )
    assistant = GeminiInvestmentAssistant()
    assistant.settings = mock_settings

    assert assistant.is_groq_api_ready() is False
    assert assistant.is_llm_ready() is False
    info = assistant.get_provider_info()
    assert info["provider"] == "mock-offline"

    # Test processing a turn with unconfigured key -> returns safe deterministic fallback
    res = await assistant.process_user_turn(
        user_id="usr-test-01",
        user_message="Hello, how does FinEx help me?",
    )
    assert res.reply is not None
    assert len(res.reply) > 0
    assert res.is_setup_incomplete is False


@pytest.mark.asyncio
async def test_groq_configured_and_successful_reply():
    """Verify that when GROQ_API_KEY is configured, Groq API is called and returns live content."""
    mock_settings = Settings(
        GROQ_API_KEY="gsk_valid_mock_key_1234567890",
        GROQ_MODEL="openai/gpt-oss-120b",
        LLM_PROVIDER="groq",
    )
    assistant = GeminiInvestmentAssistant()
    assistant.settings = mock_settings

    assert assistant.is_groq_api_ready() is True
    assert assistant.is_llm_ready() is True
    info = assistant.get_provider_info()
    assert info["provider"] == "groq-configured"
    assert info["model"] == "openai/gpt-oss-120b"

    # Mock call_groq_api to return a valid synthesis
    with patch.object(assistant, "call_groq_api", new_callable=AsyncMock) as mock_groq:
        mock_groq.return_value = "Groq LPU synthesized technical momentum analysis for NSE equities."

        res = await assistant.process_user_turn(
            user_id="usr-test-01",
            user_message="What are the best stocks for tomorrow?",
        )
        assert "Groq LPU" in res.reply
        mock_groq.assert_awaited()


@pytest.mark.asyncio
async def test_groq_api_error_falls_back_gracefully():
    """Verify that if Groq API call fails or times out, assistant falls back to verified deterministic data."""
    mock_settings = Settings(
        GROQ_API_KEY="gsk_valid_mock_key_1234567890",
        GROQ_MODEL="openai/gpt-oss-120b",
        LLM_PROVIDER="groq",
    )
    assistant = GeminiInvestmentAssistant()
    assistant.settings = mock_settings

    # Mock call_groq_api returning None (simulating API failure / timeout)
    with patch.object(assistant, "call_groq_api", new_callable=AsyncMock) as mock_groq:
        mock_groq.return_value = None

        res = await assistant.process_user_turn(
            user_id="usr-test-01",
            user_message="Tell me about top stocks",
        )
        assert res.reply is not None
        assert "RELIANCE" in res.reply or "सत्यापित" in res.reply or "portfolio" in res.reply.lower()
