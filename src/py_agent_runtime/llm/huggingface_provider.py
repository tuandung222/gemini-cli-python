from __future__ import annotations

import os

from py_agent_runtime.llm.openai_provider import OpenAIChatProvider, OpenAIClientLike


class HuggingFaceInferenceProvider(OpenAIChatProvider):
    def __init__(
        self,
        *,
        model: str = "moonshotai/Kimi-K2.5",
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float | None = None,
        max_retries: int = 2,
        retry_base_delay_seconds: float = 0.0,
        retry_max_delay_seconds: float | None = None,
        client: OpenAIClientLike | None = None,
    ) -> None:
        effective_api_key = (
            api_key
            or os.environ.get("HF_TOKEN")
            or os.environ.get("HUGGINGFACEHUB_API_TOKEN")
        )
        if not effective_api_key:
            raise ValueError(
                "Missing Hugging Face token. Set HF_TOKEN or HUGGINGFACEHUB_API_TOKEN."
            )
        effective_base_url = (
            base_url
            or os.environ.get("HUGGINGFACE_BASE_URL")
            or "https://router.huggingface.co/v1"
        )

        super().__init__(
            model=model,
            api_key=effective_api_key,
            base_url=effective_base_url,
            timeout=timeout,
            max_retries=max_retries,
            retry_base_delay_seconds=retry_base_delay_seconds,
            retry_max_delay_seconds=retry_max_delay_seconds,
            client=client,
        )
