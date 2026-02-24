from __future__ import annotations

from typing import Any, Sequence

from py_agent_runtime.llm.base_provider import LLMProvider
from py_agent_runtime.llm.types import LLMMessage, LLMTurnResponse


class GeminiChatProvider(LLMProvider):
    def __init__(self, *, model: str = "gemini-2.5-pro") -> None:
        self._model = model

    def generate(
        self,
        messages: Sequence[LLMMessage],
        tools: Sequence[dict[str, Any]] | None = None,
        *,
        model: str | None = None,
        temperature: float | None = None,
    ) -> LLMTurnResponse:
        raise NotImplementedError(
            "GeminiChatProvider is not implemented yet. OpenAI provider is available today."
        )

