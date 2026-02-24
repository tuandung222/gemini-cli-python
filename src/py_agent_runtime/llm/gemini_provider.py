from __future__ import annotations

import os
from importlib import import_module
from typing import Any, Sequence
from typing import Protocol, cast

from py_agent_runtime.llm.base_provider import LLMProvider
from py_agent_runtime.llm.normalizer import (
    parse_gemini_generate_content,
    to_gemini_contents,
    to_gemini_tools,
)
from py_agent_runtime.llm.retry import call_with_retries
from py_agent_runtime.llm.types import LLMMessage, LLMTurnResponse


class _GeminiModelsAPI(Protocol):
    def generate_content(self, **kwargs: Any) -> Any: ...


class GeminiClientLike(Protocol):
    @property
    def models(self) -> _GeminiModelsAPI: ...


class GeminiChatProvider(LLMProvider):
    def __init__(
        self,
        *,
        model: str = "gemini-2.5-pro",
        api_key: str | None = None,
        max_retries: int = 2,
        retry_base_delay_seconds: float = 0.0,
        retry_max_delay_seconds: float | None = None,
        client: GeminiClientLike | None = None,
    ) -> None:
        effective_api_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get(
            "GOOGLE_API_KEY"
        )
        if not effective_api_key:
            raise ValueError(
                "Missing Gemini API key. Set GEMINI_API_KEY or GOOGLE_API_KEY environment variable."
            )

        self._model = model
        self._api_key = effective_api_key
        self._max_retries = max_retries
        self._retry_base_delay_seconds = retry_base_delay_seconds
        self._retry_max_delay_seconds = retry_max_delay_seconds
        self._client = client or self._create_client()

    def generate(
        self,
        messages: Sequence[LLMMessage],
        tools: Sequence[dict[str, Any]] | None = None,
        *,
        model: str | None = None,
        temperature: float | None = None,
    ) -> LLMTurnResponse:
        payload: dict[str, Any] = {
            "model": model or self._model,
            "contents": to_gemini_contents(messages),
        }
        config: dict[str, Any] = {}
        if tools:
            converted_tools = to_gemini_tools(tools)
            if converted_tools:
                config["tools"] = converted_tools
        if temperature is not None:
            config["temperature"] = temperature
        if config:
            payload["config"] = config

        response = call_with_retries(
            lambda: self._client.models.generate_content(**payload),
            max_retries=self._max_retries,
            base_delay_seconds=self._retry_base_delay_seconds,
            max_delay_seconds=self._retry_max_delay_seconds,
        )
        return parse_gemini_generate_content(response)

    def _create_client(self) -> GeminiClientLike:
        try:
            genai = import_module("google.genai")
        except ImportError as exc:  # pragma: no cover
            raise ImportError(
                "google-genai package is required for GeminiChatProvider. "
                "Install with `pip install google-genai`."
            ) from exc

        client = genai.Client(api_key=self._api_key)
        return cast(GeminiClientLike, client)
