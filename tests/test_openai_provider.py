from __future__ import annotations

from types import SimpleNamespace

import pytest

from py_agent_runtime.llm.openai_provider import OpenAIChatProvider
from py_agent_runtime.llm.types import LLMMessage


class FakeCompletions:
    def __init__(self) -> None:
        self.last_payload: dict[str, object] | None = None

    def create(self, **kwargs: object) -> object:
        self.last_payload = dict(kwargs)
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

