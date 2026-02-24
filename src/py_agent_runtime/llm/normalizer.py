from __future__ import annotations

import json
from typing import Any, Iterable, Sequence
from uuid import uuid4

from py_agent_runtime.llm.types import LLMMessage, LLMToolCall, LLMTurnResponse
from py_agent_runtime.tools.base import BaseTool
from py_agent_runtime.tools.registry import ToolRegistry


def parse_openai_chat_completion(response: Any) -> LLMTurnResponse:
    choices = getattr(response, "choices", None)
    if not choices:
        raise ValueError("OpenAI response did not include choices.")

    first_choice = choices[0]
    message = getattr(first_choice, "message", None)
    if message is None:
        raise ValueError("OpenAI response choice did not include message.")

    content = getattr(message, "content", None)
    tool_calls_raw = getattr(message, "tool_calls", None) or []
    tool_calls: list[LLMToolCall] = []
    for item in tool_calls_raw:
        function_obj = getattr(item, "function", None)
        if function_obj is None:
            raise ValueError("OpenAI tool call item is missing function payload.")
        name = getattr(function_obj, "name", None)
        if not isinstance(name, str) or not name.strip():
            raise ValueError("OpenAI tool call function name is missing.")

        arguments = getattr(function_obj, "arguments", "")
        parsed_args = parse_tool_arguments(arguments, tool_name=name)
        call_id = getattr(item, "id", None)
        tool_calls.append(
            LLMToolCall(
                name=name,
                args=parsed_args,
                call_id=call_id if isinstance(call_id, str) else None,
            )
        )

    finish_reason = getattr(first_choice, "finish_reason", None)
    return LLMTurnResponse(
        content=content if isinstance(content, str) else None,
        tool_calls=tool_calls,
        finish_reason=finish_reason if isinstance(finish_reason, str) else None,
        raw=response,
    )


def parse_tool_arguments(arguments: Any, tool_name: str) -> dict[str, Any]:
    if isinstance(arguments, dict):
        return arguments
    if arguments in ("", None):
        return {}
    if not isinstance(arguments, str):
        raise ValueError(f"Tool '{tool_name}' arguments must be a JSON string or object.")
    try:
        parsed = json.loads(arguments)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Tool '{tool_name}' arguments are not valid JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise ValueError(f"Tool '{tool_name}' arguments JSON must decode to an object.")
    return parsed


def to_openai_messages(messages: Sequence[LLMMessage]) -> list[dict[str, Any]]:
    serialized: list[dict[str, Any]] = []
    for message in messages:
        row: dict[str, Any] = {"role": message.role}
        if message.content is not None:
            row["content"] = message.content

        if message.role == "assistant" and message.tool_calls:
            row["tool_calls"] = [
                {
                    "id": call.call_id or f"call_{uuid4()}",
                    "type": "function",
                    "function": {
                        "name": call.name,
                        "arguments": json.dumps(call.args, sort_keys=True),
                    },
                }
                for call in message.tool_calls
            ]

        if message.role == "tool":
            if not message.tool_call_id:
                raise ValueError("Tool messages must include `tool_call_id` for OpenAI chat API.")
            row["tool_call_id"] = message.tool_call_id
            row["content"] = message.content or ""
            if message.name:
                row["name"] = message.name

        serialized.append(row)
    return serialized


def build_openai_tool_schemas(
    tools: Iterable[BaseTool],
    include_names: set[str] | None = None,
) -> list[dict[str, Any]]:
    schemas: list[dict[str, Any]] = []
    for tool in tools:
        if include_names is not None and tool.name not in include_names:
            continue
        params = getattr(tool, "parameters_json_schema", None)
        parameters_schema = params if isinstance(params, dict) else default_tool_schema()
        schemas.append(
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": parameters_schema,
                },
            }
        )
    return schemas


def build_openai_tool_schemas_from_registry(
    registry: ToolRegistry,
    include_names: set[str] | None = None,
) -> list[dict[str, Any]]:
    return build_openai_tool_schemas(registry.get_all_tools(), include_names=include_names)


def default_tool_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {},
        "additionalProperties": True,
    }

