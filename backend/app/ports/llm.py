from abc import ABC, abstractmethod
from typing import List, Optional

from pydantic import BaseModel, Field


class ModelMessage(BaseModel):
    role: str = Field(..., description="system, user, assistant")
    content: str = Field(..., description="Message text content")


class LLMResponse(BaseModel):
    content: str
    model_name: str
    tokens_prompt: Optional[int] = None
    tokens_completion: Optional[int] = None
    latency_ms: float = 0.0


class AbstractLLMProvider(ABC):
    """Port interface for LLM completions and explanations."""

    @abstractmethod
    async def generate_response(
        self,
        messages: List[ModelMessage],
        temperature: float = 0.0,
        max_tokens: int = 1000,
    ) -> LLMResponse:
        """Execute LLM completion with bounded timeout and temperature."""
        pass
