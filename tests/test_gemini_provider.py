from __future__ import annotations

from types import SimpleNamespace

import pytest

from py_agent_runtime.llm.gemini_provider import GeminiChatProvider
from py_agent_runtime.llm.types import LLMMessage


class FakeGeminiModels:
    def __init__(self) -> None:
        self.last_payload: dict[str, object] | None = None
        self.calls = 0
        self.failures: list[Exception] = []

    def generate_content(self, **kwargs: object) -> object:
        self.calls += 1
        self.last_payload = dict(kwargs)
        if self.failures:
            raise self.failures.pop(0)
        return SimpleNamespace(
            text="ok",
            function_calls=[
                SimpleNamespace(
                    id="gem_call_1",
                    name="sample_tool",
                    args={"value": "abc"},
                )
            ],
            candidates=[SimpleNamespace(finish_reason="STOP")],
        )


class FakeGeminiClient:
    def __init__(self) -> None:
        self.models = FakeGeminiModels()


class RetryableError(RuntimeError):
    def __init__(self, message: str, status_code: int) -> None:
        super().__init__(message)
        self.status_code = status_code


def test_gemini_provider_requires_env_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    with pytest.raises(ValueError):
        GeminiChatProvider(client=FakeGeminiClient())


def test_gemini_provider_reads_env_and_calls_generate_content(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    fake_client = FakeGeminiClient()
    provider = GeminiChatProvider(model="gemini-2.5-pro", client=fake_client)
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

    payload = fake_client.models.last_payload
    assert payload is not None
    assert payload["model"] == "gemini-2.5-pro"
    assert isinstance(payload["contents"], list)
    assert isinstance(payload["config"], dict)


def test_gemini_provider_retries_transient_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    fake_client = FakeGeminiClient()
    fake_client.models.failures = [RetryableError("rate limited", 429)]
    provider = GeminiChatProvider(model="gemini-2.5-pro", client=fake_client, max_retries=1)

    response = provider.generate(messages=[LLMMessage(role="user", content="hello")])
    assert response.content == "ok"
    assert fake_client.models.calls == 2
