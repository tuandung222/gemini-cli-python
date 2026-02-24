from __future__ import annotations

import os
from typing import Any, Sequence
from typing import Protocol, cast

from py_agent_runtime.llm.base_provider import LLMProvider
from py_agent_runtime.llm.normalizer import (
    parse_anthropic_message_response,
    to_anthropic_messages,
    to_anthropic_tools,
)
from py_agent_runtime.llm.types import LLMMessage, LLMTurnResponse


class _AnthropicMessagesAPI(Protocol):
    def create(self, **kwargs: Any) -> Any: ...


class AnthropicClientLike(Protocol):
    @property
    def messages(self) -> _AnthropicMessagesAPI: ...


class AnthropicChatProvider(LLMProvider):
    def __init__(
        self,
        *,
        model: str = "claude-3-7-sonnet-latest",
        api_key: str | None = None,
        max_tokens: int = 2048,
        client: AnthropicClientLike | None = None,
    ) -> None:
        effective_api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not effective_api_key:
            raise ValueError(
                "Missing Anthropic API key. Set ANTHROPIC_API_KEY environment variable."
            )

        self._model = model
        self._api_key = effective_api_key
        self._max_tokens = max_tokens
        self._client = client or self._create_client()

    def generate(
        self,
        messages: Sequence[LLMMessage],
        tools: Sequence[dict[str, Any]] | None = None,
        *,
        model: str | None = None,
        temperature: float | None = None,
    ) -> LLMTurnResponse:
        system_prompt, anthropic_messages = to_anthropic_messages(messages)

        payload: dict[str, Any] = {
            "model": model or self._model,
            "max_tokens": self._max_tokens,
            "messages": anthropic_messages,
        }
        if system_prompt:
            payload["system"] = system_prompt
        if tools:
            converted_tools = to_anthropic_tools(tools)
            if converted_tools:
                payload["tools"] = converted_tools
        if temperature is not None:
            payload["temperature"] = temperature

        response = self._client.messages.create(**payload)
        return parse_anthropic_message_response(response)

    def _create_client(self) -> AnthropicClientLike:
        try:
            from anthropic import Anthropic
        except ImportError as exc:  # pragma: no cover
            raise ImportError(
                "anthropic package is required for AnthropicChatProvider. "
                "Install with `pip install anthropic`."
            ) from exc

        client = Anthropic(api_key=self._api_key)
        return cast(AnthropicClientLike, client)
