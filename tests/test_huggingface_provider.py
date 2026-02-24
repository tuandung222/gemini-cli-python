from __future__ import annotations

from types import SimpleNamespace

import pytest

from py_agent_runtime.llm.huggingface_provider import HuggingFaceInferenceProvider
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


def test_huggingface_provider_requires_env_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HF_TOKEN", raising=False)
    monkeypatch.delenv("HUGGINGFACEHUB_API_TOKEN", raising=False)
    with pytest.raises(ValueError):
        HuggingFaceInferenceProvider(client=FakeOpenAIClient())


def test_huggingface_provider_reads_env_and_calls_chat_api(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HF_TOKEN", "test-hf-token")
    fake_client = FakeOpenAIClient()
    provider = HuggingFaceInferenceProvider(model="moonshotai/Kimi-K2.5", client=fake_client)

    response = provider.generate(messages=[LLMMessage(role="user", content="hello")], temperature=0.2)
    assert response.content == "ok"

    payload = fake_client.chat.completions.last_payload
    assert payload is not None
    assert payload["model"] == "moonshotai/Kimi-K2.5"
    assert payload["temperature"] == 0.2
    assert isinstance(payload["messages"], list)

