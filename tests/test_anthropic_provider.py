from __future__ import annotations

from types import SimpleNamespace

import pytest

from py_agent_runtime.llm.anthropic_provider import AnthropicChatProvider
from py_agent_runtime.llm.types import LLMMessage


class FakeAnthropicMessages:
    def __init__(self) -> None:
        self.last_payload: dict[str, object] | None = None

    def create(self, **kwargs: object) -> object:
        self.last_payload = dict(kwargs)
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

