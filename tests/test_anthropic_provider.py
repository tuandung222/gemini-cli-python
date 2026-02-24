from __future__ import annotations

from types import SimpleNamespace

import pytest

from py_agent_runtime.llm.anthropic_provider import AnthropicChatProvider
from py_agent_runtime.llm.types import LLMMessage


class FakeAnthropicMessages:
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
            content=[
                SimpleNamespace(type="text", text="ok"),
                SimpleNamespace(
                    type="tool_use",
                    id="anth_call_1",
                    name="sample_tool",
                    input={"value": "abc"},
                ),
            ],
            stop_reason="tool_use",
        )


class FakeAnthropicClient:
    def __init__(self) -> None:
        self.messages = FakeAnthropicMessages()


class RetryableError(RuntimeError):
    def __init__(self, message: str, status_code: int) -> None:
        super().__init__(message)
        self.status_code = status_code


def test_anthropic_provider_requires_env_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(ValueError):
        AnthropicChatProvider(client=FakeAnthropicClient())


def test_anthropic_provider_reads_env_and_calls_messages_create(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-anthropic-key")
    fake_client = FakeAnthropicClient()
    provider = AnthropicChatProvider(model="claude-3-7-sonnet-latest", client=fake_client)
    response = provider.generate(
        messages=[LLMMessage(role="user", content="hello")],
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "sample_tool",
                    "description": "d",
                    "parameters": {"type": "object"},
                },
            }
        ],
        temperature=0.3,
    )
    assert response.content == "ok"
    assert len(response.tool_calls) == 1
    assert response.tool_calls[0].name == "sample_tool"
    assert response.tool_calls[0].args == {"value": "abc"}

    payload = fake_client.messages.last_payload
    assert payload is not None
    assert payload["model"] == "claude-3-7-sonnet-latest"
    assert isinstance(payload["messages"], list)
    assert isinstance(payload["tools"], list)
    assert payload["temperature"] == 0.3


def test_anthropic_provider_retries_transient_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-anthropic-key")
    fake_client = FakeAnthropicClient()
    fake_client.messages.failures = [RetryableError("service unavailable", 503)]
    provider = AnthropicChatProvider(
        model="claude-3-7-sonnet-latest",
        client=fake_client,
        max_retries=1,
    )

    response = provider.generate(messages=[LLMMessage(role="user", content="hello")])
    assert response.content == "ok"
    assert fake_client.messages.calls == 2


def test_anthropic_provider_passes_retry_backoff_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-anthropic-key")
    fake_client = FakeAnthropicClient()
    captured: dict[str, object] = {}

    def _fake_retry(fn, **kwargs):  # noqa: ANN001, ANN003
        captured.update(kwargs)
        return fn()

    monkeypatch.setattr("py_agent_runtime.llm.anthropic_provider.call_with_retries", _fake_retry)
    provider = AnthropicChatProvider(
        model="claude-3-7-sonnet-latest",
        client=fake_client,
        max_retries=3,
        retry_base_delay_seconds=0.2,
        retry_max_delay_seconds=1.2,
    )

    response = provider.generate(messages=[LLMMessage(role="user", content="hello")])
    assert response.content == "ok"
    assert captured["max_retries"] == 3
    assert captured["base_delay_seconds"] == 0.2
    assert captured["max_delay_seconds"] == 1.2
