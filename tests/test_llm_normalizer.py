from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Mapping

import pytest

from py_agent_runtime.llm.normalizer import (
    build_openai_tool_schemas,
    parse_openai_chat_completion,
    parse_tool_arguments,
    to_openai_messages,
)
from py_agent_runtime.llm.types import LLMMessage, LLMToolCall
from py_agent_runtime.runtime.config import RuntimeConfig
from py_agent_runtime.tools.base import BaseTool, ToolResult


class SampleTool(BaseTool):
    name = "sample_tool"
    description = "A sample tool."

    def validate_params(self, params: Mapping[str, Any]) -> str | None:
        return None

    def execute(self, config: RuntimeConfig, params: Mapping[str, Any]) -> ToolResult:
        return ToolResult(llm_content="ok", return_display="ok")


def _make_tool_response() -> Any:
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content=None,
                    tool_calls=[
                        SimpleNamespace(
                            id="call_1",
                            function=SimpleNamespace(
                                name="sample_tool",
                                arguments='{"value":"abc"}',
                            ),
                        )
                    ],
                ),
                finish_reason="tool_calls",
            )
        ]
    )


def test_parse_openai_chat_completion_tool_calls() -> None:
    parsed = parse_openai_chat_completion(_make_tool_response())
    assert parsed.finish_reason == "tool_calls"
    assert len(parsed.tool_calls) == 1
    assert parsed.tool_calls[0].name == "sample_tool"
    assert parsed.tool_calls[0].args == {"value": "abc"}
    assert parsed.tool_calls[0].call_id == "call_1"


def test_parse_tool_arguments_rejects_invalid_json() -> None:
    with pytest.raises(ValueError):
        parse_tool_arguments("{", tool_name="sample_tool")


def test_to_openai_messages_serializes_assistant_tool_calls() -> None:
    messages = [
        LLMMessage(role="user", content="hello"),
        LLMMessage(
            role="assistant",
            content=None,
            tool_calls=(LLMToolCall(name="sample_tool", args={"x": 1}, call_id="c1"),),
        ),
        LLMMessage(role="tool", tool_call_id="c1", content='{"status":"ok"}'),
    ]
    serialized = to_openai_messages(messages)
    assert serialized[1]["tool_calls"][0]["function"]["name"] == "sample_tool"
    assert serialized[2]["role"] == "tool"
    assert serialized[2]["tool_call_id"] == "c1"


def test_build_openai_tool_schemas_uses_default_shape() -> None:
    schemas = build_openai_tool_schemas([SampleTool()])
    assert len(schemas) == 1
    schema = schemas[0]["function"]["parameters"]
    assert schema["type"] == "object"
    assert schema["additionalProperties"] is True

