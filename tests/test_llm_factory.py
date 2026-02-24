from __future__ import annotations

import pytest

import py_agent_runtime.llm.factory as llm_factory


def test_factory_rejects_unsupported_provider() -> None:
    with pytest.raises(ValueError):
        llm_factory.create_provider("unknown")


def test_factory_routes_to_openai_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeOpenAIProvider:
        def __init__(self, model: str) -> None:
            self.model = model

    monkeypatch.setattr(llm_factory, "OpenAIChatProvider", FakeOpenAIProvider)
    provider = llm_factory.create_provider("openai", model="gpt-x")
    assert isinstance(provider, FakeOpenAIProvider)
    assert provider.model == "gpt-x"


def test_factory_routes_to_gemini_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeGeminiProvider:
        def __init__(self, model: str) -> None:
            self.model = model

    monkeypatch.setattr(llm_factory, "GeminiChatProvider", FakeGeminiProvider)
    provider = llm_factory.create_provider("gemini", model="gemini-x")
    assert isinstance(provider, FakeGeminiProvider)
    assert provider.model == "gemini-x"


def test_factory_routes_to_anthropic_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeAnthropicProvider:
        def __init__(self, model: str) -> None:
            self.model = model

    monkeypatch.setattr(llm_factory, "AnthropicChatProvider", FakeAnthropicProvider)
    provider = llm_factory.create_provider("anthropic", model="claude-x")
    assert isinstance(provider, FakeAnthropicProvider)
    assert provider.model == "claude-x"
