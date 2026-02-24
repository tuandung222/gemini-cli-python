from __future__ import annotations

from types import SimpleNamespace

import pytest

from py_agent_runtime.llm.openai_provider import OpenAIChatProvider
from py_agent_runtime.llm.types import LLMMessage


class FakeCompletions:
    def __init__(self) -> None:
        self.last_payload: dict[str, object] | None = None
        self.calls = 0
        self.failures: list[Exception] = []

    def create(self, **kwargs: object) -> object:
        self.calls += 1
        self.last_payload = dict(kwargs)
        if self.failures:
            raise self.failures.pop(0)
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content="ok", tool_calls=[]),
                    finish_reason="stop",
                )
            ]
        )


class FakeOpenAIClient:
    def __init__(self) -> None:
        self.chat = SimpleNamespace(completions=FakeCompletions())


class RetryableError(RuntimeError):
    def __init__(self, message: str, status_code: int) -> None:
        super().__init__(message)
        self.status_code = status_code


class NonRetryableError(RuntimeError):
    def __init__(self, message: str, status_code: int) -> None:
        super().__init__(message)
        self.status_code = status_code


def test_openai_provider_requires_env_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(ValueError):
        OpenAIChatProvider(client=FakeOpenAIClient())


def test_openai_provider_reads_env_and_calls_chat_api(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    fake_client = FakeOpenAIClient()
    provider = OpenAIChatProvider(model="gpt-4.1-mini", client=fake_client)
    response = provider.generate(
        messages=[LLMMessage(role="user", content="hello")],
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "sample",
                    "description": "d",
                    "parameters": {"type": "object"},
                },
            }
        ],
        temperature=0.2,
    )
    assert response.content == "ok"

    payload = fake_client.chat.completions.last_payload
    assert payload is not None
    assert payload["model"] == "gpt-4.1-mini"
    assert payload["tool_choice"] == "auto"
    assert payload["temperature"] == 0.2
    assert isinstance(payload["messages"], list)


def test_openai_provider_retries_transient_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    fake_client = FakeOpenAIClient()
    fake_client.chat.completions.failures = [
        RetryableError("rate limited", 429),
        RetryableError("service unavailable", 503),
    ]
    provider = OpenAIChatProvider(model="gpt-4.1-mini", client=fake_client, max_retries=2)

    response = provider.generate(messages=[LLMMessage(role="user", content="hello")])
    assert response.content == "ok"
    assert fake_client.chat.completions.calls == 3


def test_openai_provider_does_not_retry_non_retryable_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    fake_client = FakeOpenAIClient()
    fake_client.chat.completions.failures = [NonRetryableError("bad request", 400)]
    provider = OpenAIChatProvider(model="gpt-4.1-mini", client=fake_client, max_retries=3)

    with pytest.raises(NonRetryableError):
        provider.generate(messages=[LLMMessage(role="user", content="hello")])
    assert fake_client.chat.completions.calls == 1


def test_openai_provider_passes_retry_backoff_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    fake_client = FakeOpenAIClient()
    captured: dict[str, object] = {}

    def _fake_retry(fn, **kwargs):  # noqa: ANN001, ANN003
        captured.update(kwargs)
        return fn()

    monkeypatch.setattr("py_agent_runtime.llm.openai_provider.call_with_retries", _fake_retry)
    provider = OpenAIChatProvider(
        model="gpt-4.1-mini",
        client=fake_client,
        max_retries=3,
        retry_base_delay_seconds=0.25,
        retry_max_delay_seconds=1.5,
    )

    response = provider.generate(messages=[LLMMessage(role="user", content="hello")])
    assert response.content == "ok"
    assert captured["max_retries"] == 3
    assert captured["base_delay_seconds"] == 0.25
    assert captured["max_delay_seconds"] == 1.5
