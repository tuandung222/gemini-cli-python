from __future__ import annotations

import pytest

from py_agent_runtime.llm.factory import create_provider
from py_agent_runtime.llm.types import LLMMessage


def test_factory_rejects_unsupported_provider() -> None:
    with pytest.raises(ValueError):
        create_provider("unknown")


def test_gemini_provider_stub_is_declared_but_not_implemented() -> None:
    provider = create_provider("gemini")
    with pytest.raises(NotImplementedError):
        provider.generate([LLMMessage(role="user", content="hello")])


def test_anthropic_provider_stub_is_declared_but_not_implemented() -> None:
    provider = create_provider("anthropic")
    with pytest.raises(NotImplementedError):
        provider.generate([LLMMessage(role="user", content="hello")])

