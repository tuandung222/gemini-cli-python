from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Mapping

import pytest

from py_agent_runtime.llm.normalizer import (
    build_openai_tool_schemas,
    parse_anthropic_message_response,
    parse_gemini_generate_content,
    parse_openai_chat_completion,
    parse_tool_arguments,
    to_anthropic_messages,
    to_anthropic_tools,
    to_gemini_contents,
    to_gemini_tools,
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


def test_to_gemini_contents_serializes_assistant_tool_calls_and_tool_results() -> None:
    messages = [
        LLMMessage(role="system", content="rules"),
        LLMMessage(role="user", content="task"),
        LLMMessage(
            role="assistant",
            content="thinking",
            tool_calls=(LLMToolCall(name="sample_tool", args={"x": 1}, call_id="c1"),),
        ),
        LLMMessage(role="tool", tool_call_id="c1", name="sample_tool", content='{"ok":true}'),
    ]
    contents = to_gemini_contents(messages)
    assert len(contents) == 4
    assert contents[2]["role"] == "model"
    assert contents[2]["parts"][1]["functionCall"]["name"] == "sample_tool"
    assert contents[3]["parts"][0]["functionResponse"]["name"] == "sample_tool"


def test_parse_gemini_generate_content_from_candidate_parts() -> None:
    response = SimpleNamespace(
        text=None,
        function_calls=None,
        candidates=[
            {
                "finish_reason": "STOP",
                "content": {
                    "parts": [
                        {"text": "ok"},
                        {"functionCall": {"id": "g1", "name": "sample_tool", "args": {"x": 1}}},
                    ]
                },
            }
        ],
    )
    parsed = parse_gemini_generate_content(response)
    assert parsed.content == "ok"
    assert parsed.finish_reason == "STOP"
    assert parsed.tool_calls[0].name == "sample_tool"
    assert parsed.tool_calls[0].args == {"x": 1}


def test_to_anthropic_messages_extracts_system_and_tool_result() -> None:
    messages = [
        LLMMessage(role="system", content="rules"),
        LLMMessage(role="user", content="task"),
        LLMMessage(
            role="assistant",
            content=None,
            tool_calls=(LLMToolCall(name="sample_tool", args={"x": 1}, call_id="c1"),),
        ),
        LLMMessage(role="tool", tool_call_id="c1", content='{"ok":true}'),
    ]
    system_prompt, anth_messages = to_anthropic_messages(messages)
    assert system_prompt == "rules"
    assert anth_messages[0]["role"] == "user"
    assert anth_messages[1]["role"] == "assistant"
    assert anth_messages[1]["content"][0]["type"] == "tool_use"
    assert anth_messages[2]["content"][0]["type"] == "tool_result"


def test_parse_anthropic_message_response_extracts_text_and_tool_calls() -> None:
    response = SimpleNamespace(
        content=[
            SimpleNamespace(type="text", text="ok"),
            SimpleNamespace(type="tool_use", id="a1", name="sample_tool", input={"x": 1}),
        ],
        stop_reason="tool_use",
    )
    parsed = parse_anthropic_message_response(response)
    assert parsed.content == "ok"
    assert parsed.finish_reason == "tool_use"
    assert parsed.tool_calls[0].name == "sample_tool"
    assert parsed.tool_calls[0].args == {"x": 1}


def test_provider_tool_schema_conversion_helpers() -> None:
    tools = [
        {
            "type": "function",
            "function": {
                "name": "sample_tool",
                "description": "d",
                "parameters": {"type": "object"},
            },
        }
    ]
    gemini_tools = to_gemini_tools(tools)
    anthropic_tools = to_anthropic_tools(tools)
    assert gemini_tools[0]["function_declarations"][0]["name"] == "sample_tool"
    assert anthropic_tools[0]["name"] == "sample_tool"
