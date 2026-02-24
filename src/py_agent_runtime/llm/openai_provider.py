from __future__ import annotations

import os
from typing import Any, Protocol, Sequence, cast

from py_agent_runtime.llm.base_provider import LLMProvider
from py_agent_runtime.llm.normalizer import parse_openai_chat_completion, to_openai_messages
from py_agent_runtime.llm.retry import call_with_retries
from py_agent_runtime.llm.types import LLMMessage, LLMTurnResponse


class _OpenAIChatCompletionsAPI(Protocol):
    def create(self, **kwargs: Any) -> Any: ...


class _OpenAIChatNamespace(Protocol):
    @property
    def completions(self) -> _OpenAIChatCompletionsAPI: ...


class OpenAIClientLike(Protocol):
    @property
    def chat(self) -> _OpenAIChatNamespace: ...


class OpenAIChatProvider(LLMProvider):
    def __init__(
        self,
        *,
        model: str = "gpt-4.1-mini",
        api_key: str | None = None,
        base_url: str | None = None,
        organization: str | None = None,
        project: str | None = None,
        timeout: float | None = None,
        max_retries: int = 2,
        retry_base_delay_seconds: float = 0.0,
        retry_max_delay_seconds: float | None = None,
        client: OpenAIClientLike | None = None,
    ) -> None:
        effective_api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not effective_api_key:
            raise ValueError(
                "Missing OpenAI API key. Set OPENAI_API_KEY environment variable."
            )

        self._default_model = model
        self._api_key = effective_api_key
        self._base_url = base_url
        self._organization = organization
        self._project = project
        self._timeout = timeout
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
            "model": model or self._default_model,
            "messages": to_openai_messages(messages),
        }
        if tools:
            payload["tools"] = list(tools)
            payload["tool_choice"] = "auto"
        if temperature is not None:
            payload["temperature"] = temperature

        response = call_with_retries(
            lambda: self._client.chat.completions.create(**payload),
            max_retries=self._max_retries,
            base_delay_seconds=self._retry_base_delay_seconds,
            max_delay_seconds=self._retry_max_delay_seconds,
        )
        return parse_openai_chat_completion(response)

    def _create_client(self) -> OpenAIClientLike:
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover
            raise ImportError(
                "openai package is required for OpenAIChatProvider. Install with `pip install openai`."
            ) from exc

        client = OpenAI(
            api_key=self._api_key,
            base_url=self._base_url,
            organization=self._organization,
            project=self._project,
            timeout=self._timeout,
        )
        return cast(OpenAIClientLike, client)
