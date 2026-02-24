from __future__ import annotations

from py_agent_runtime.llm.anthropic_provider import AnthropicChatProvider
from py_agent_runtime.llm.base_provider import LLMProvider
from py_agent_runtime.llm.gemini_provider import GeminiChatProvider
from py_agent_runtime.llm.huggingface_provider import HuggingFaceInferenceProvider
from py_agent_runtime.llm.openai_provider import OpenAIChatProvider


def create_provider(
    provider: str,
    *,
    model: str | None = None,
    max_retries: int = 2,
    retry_base_delay_seconds: float = 0.0,
    retry_max_delay_seconds: float | None = None,
) -> LLMProvider:
    normalized = provider.strip().lower()
    if normalized == "openai":
        return OpenAIChatProvider(
            model=model or "gpt-4.1-mini",
            max_retries=max_retries,
            retry_base_delay_seconds=retry_base_delay_seconds,
            retry_max_delay_seconds=retry_max_delay_seconds,
        )
    if normalized == "gemini":
        return GeminiChatProvider(
            model=model or "gemini-2.5-pro",
            max_retries=max_retries,
            retry_base_delay_seconds=retry_base_delay_seconds,
            retry_max_delay_seconds=retry_max_delay_seconds,
        )
    if normalized == "anthropic":
        return AnthropicChatProvider(
            model=model or "claude-3-7-sonnet-latest",
            max_retries=max_retries,
            retry_base_delay_seconds=retry_base_delay_seconds,
            retry_max_delay_seconds=retry_max_delay_seconds,
        )
    if normalized == "huggingface":
        return HuggingFaceInferenceProvider(
            model=model or "moonshotai/Kimi-K2.5",
            max_retries=max_retries,
            retry_base_delay_seconds=retry_base_delay_seconds,
            retry_max_delay_seconds=retry_max_delay_seconds,
        )
    raise ValueError(f"Unsupported provider: {provider}")
