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


def parse_gemini_generate_content(response: Any) -> LLMTurnResponse:
    content = _extract_gemini_text(response)
    tool_calls = _extract_gemini_tool_calls(response)
    finish_reason = _extract_gemini_finish_reason(response)
    return LLMTurnResponse(
        content=content,
        tool_calls=tool_calls,
        finish_reason=finish_reason,
        raw=response,
    )


def to_gemini_contents(messages: Sequence[LLMMessage]) -> list[dict[str, Any]]:
    contents: list[dict[str, Any]] = []
    for message in messages:
        if message.role == "assistant":
            parts: list[dict[str, Any]] = []
            if message.content:
                parts.append({"text": message.content})
            for call in message.tool_calls:
                parts.append(
                    {
                        "functionCall": {
                            "name": call.name,
                            "args": call.args,
                        }
                    }
                )
            if not parts:
                parts.append({"text": ""})
            contents.append({"role": "model", "parts": parts})
            continue

        if message.role == "tool":
            if not message.tool_call_id:
                raise ValueError("Gemini tool response messages require `tool_call_id`.")
            contents.append(
                {
                    "role": "user",
                    "parts": [
                        {
                            "functionResponse": {
                                "name": message.name or "tool",
                                "response": {
                                    "tool_call_id": message.tool_call_id,
                                    "content": message.content or "",
                                },
                            }
                        }
                    ],
                }
            )
            continue

        text = message.content or ""
        if message.role == "system" and text:
            text = f"[SYSTEM]\n{text}"
        contents.append({"role": "user", "parts": [{"text": text}]})
    return contents


def to_gemini_tools(tools: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    declarations: list[dict[str, Any]] = []
    for tool in tools:
        if tool.get("type") != "function":
            continue
        function = tool.get("function")
        if not isinstance(function, dict):
            continue
        name = function.get("name")
        if not isinstance(name, str) or not name.strip():
            continue
        declarations.append(
            {
                "name": name,
                "description": function.get("description", ""),
                "parameters": function.get("parameters", default_tool_schema()),
            }
        )
    if not declarations:
        return []
    return [{"function_declarations": declarations}]


def parse_anthropic_message_response(response: Any) -> LLMTurnResponse:
    blocks = getattr(response, "content", None) or []
    text_parts: list[str] = []
    tool_calls: list[LLMToolCall] = []
    for block in blocks:
        block_type = _read(block, "type")
        if block_type == "text":
            text = _read(block, "text")
            if isinstance(text, str):
                text_parts.append(text)
            continue
        if block_type == "tool_use":
            name = _read(block, "name")
            if not isinstance(name, str) or not name.strip():
                raise ValueError("Anthropic tool_use block is missing name.")
            tool_input = _read(block, "input")
            args = parse_tool_arguments(tool_input, tool_name=name)
            call_id = _read(block, "id")
            tool_calls.append(
                LLMToolCall(
                    name=name,
                    args=args,
                    call_id=call_id if isinstance(call_id, str) else None,
                )
            )
    text_content = "".join(text_parts).strip() or None
    stop_reason = getattr(response, "stop_reason", None)
    return LLMTurnResponse(
        content=text_content,
        tool_calls=tool_calls,
        finish_reason=stop_reason if isinstance(stop_reason, str) else None,
        raw=response,
    )


def to_anthropic_messages(
    messages: Sequence[LLMMessage],
) -> tuple[str | None, list[dict[str, Any]]]:
    system_parts: list[str] = []
    anthropic_messages: list[dict[str, Any]] = []

    for message in messages:
        if message.role == "system":
            if message.content:
                system_parts.append(message.content)
            continue

        if message.role == "user":
            anthropic_messages.append(
                {"role": "user", "content": [{"type": "text", "text": message.content or ""}]}
            )
            continue

        if message.role == "assistant":
            blocks: list[dict[str, Any]] = []
            if message.content:
                blocks.append({"type": "text", "text": message.content})
            for tool_call in message.tool_calls:
                blocks.append(
                    {
                        "type": "tool_use",
                        "id": tool_call.call_id or f"toolu_{uuid4().hex}",
                        "name": tool_call.name,
                        "input": tool_call.args,
                    }
                )
            if not blocks:
                blocks.append({"type": "text", "text": ""})
            anthropic_messages.append({"role": "assistant", "content": blocks})
            continue

        if not message.tool_call_id:
            raise ValueError("Anthropic tool response messages require `tool_call_id`.")
        anthropic_messages.append(
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": message.tool_call_id,
                        "content": message.content or "",
                    }
                ],
            }
        )

    system = "\n\n".join(system_parts).strip() or None
    return system, anthropic_messages


def to_anthropic_tools(tools: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    anthropic_tools: list[dict[str, Any]] = []
    for tool in tools:
        if tool.get("type") != "function":
            continue
        function = tool.get("function")
        if not isinstance(function, dict):
            continue
        name = function.get("name")
        if not isinstance(name, str) or not name.strip():
            continue
        anthropic_tools.append(
            {
                "name": name,
                "description": function.get("description", ""),
                "input_schema": function.get("parameters", default_tool_schema()),
            }
        )
    return anthropic_tools


def _read(value: Any, key: str) -> Any:
    if isinstance(value, dict):
        return value.get(key)
    return getattr(value, key, None)


def _extract_gemini_text(response: Any) -> str | None:
    raw_text = getattr(response, "text", None)
    if isinstance(raw_text, str) and raw_text.strip():
        return raw_text

    candidates = getattr(response, "candidates", None) or []
    if not candidates:
        return None
    first = candidates[0]
    candidate_content = _read(first, "content")
    parts = _read(candidate_content, "parts") or []
    chunks: list[str] = []
    for part in parts:
        text = _read(part, "text")
        if isinstance(text, str) and text:
            chunks.append(text)
    merged = "".join(chunks).strip()
    return merged or None


def _extract_gemini_tool_calls(response: Any) -> list[LLMToolCall]:
    raw_calls = getattr(response, "function_calls", None)
    if raw_calls is None:
        raw_calls = []
        candidates = getattr(response, "candidates", None) or []
        if candidates:
            content = _read(candidates[0], "content")
            for part in _read(content, "parts") or []:
                function_call = _read(part, "function_call")
                if function_call is None:
                    function_call = _read(part, "functionCall")
                if function_call is not None:
                    raw_calls.append(function_call)

    parsed_calls: list[LLMToolCall] = []
    for call in raw_calls:
        name = _read(call, "name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Gemini function call is missing name.")
        args_raw = _read(call, "args")
        if args_raw is None:
            args_raw = _read(call, "arguments")
        args = parse_tool_arguments(args_raw, tool_name=name)
        call_id = _read(call, "id")
        parsed_calls.append(
            LLMToolCall(
                name=name,
                args=args,
                call_id=call_id if isinstance(call_id, str) else None,
            )
        )
    return parsed_calls


def _extract_gemini_finish_reason(response: Any) -> str | None:
    candidates = getattr(response, "candidates", None) or []
    if not candidates:
        return None
    reason = _read(candidates[0], "finish_reason")
    if isinstance(reason, str):
        return reason
    if reason is None:
        return None
    return str(reason)
