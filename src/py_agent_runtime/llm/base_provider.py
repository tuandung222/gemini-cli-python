from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Sequence

from py_agent_runtime.llm.types import LLMMessage, LLMTurnResponse


class LLMProvider(ABC):
    @abstractmethod
    def generate(
        self,
        messages: Sequence[LLMMessage],
        tools: Sequence[dict[str, Any]] | None = None,
        *,
        model: str | None = None,
        temperature: float | None = None,
    ) -> LLMTurnResponse:
        raise NotImplementedError

