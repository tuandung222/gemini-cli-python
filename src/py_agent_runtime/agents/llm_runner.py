from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from py_agent_runtime.agents.agent_scheduler import schedule_agent_tools
from py_agent_runtime.agents.completion_schema import validate_completion_output
from py_agent_runtime.agents.local_executor import (
    FunctionCall,
    LocalAgentExecutor,
    TASK_COMPLETE_TOOL_NAME,
)
from py_agent_runtime.llm.base_provider import LLMProvider
from py_agent_runtime.llm.normalizer import build_openai_tool_schemas_from_registry
from py_agent_runtime.llm.types import LLMMessage
from py_agent_runtime.runtime.config import RuntimeConfig
from py_agent_runtime.scheduler.types import CoreToolCallStatus, ToolCallRequestInfo


@dataclass(frozen=True)
class AgentRunResult:
    success: bool
    result: str | None
    error: str | None
    turns: int


class LLMAgentRunner:
    def __init__(
        self,
        config: RuntimeConfig,
        provider: LLMProvider,
        *,
        max_turns: int = 15,
        scheduler_id: str = "root_agent",
        model: str | None = None,
        temperature: float | None = None,
        enable_recovery_turn: bool = True,
        completion_schema: dict[str, Any] | None = None,
    ) -> None:
        self._config = config
        self._provider = provider
        self._max_turns = max_turns
        self._scheduler_id = scheduler_id
        self._model = model
        self._temperature = temperature
        self._enable_recovery_turn = enable_recovery_turn
        self._completion_schema = completion_schema

    def run(self, user_prompt: str, system_prompt: str | None = None) -> AgentRunResult:
        messages: list[LLMMessage] = []
        if system_prompt:
            messages.append(LLMMessage(role="system", content=system_prompt))
        messages.append(LLMMessage(role="user", content=user_prompt))

        allowed_tool_names = self._build_allowed_tool_names()
        tool_schemas = build_openai_tool_schemas_from_registry(
            self._config.tool_registry,
            include_names=allowed_tool_names,
        )
        tool_schemas.append(self._completion_tool_schema())

        for turn in range(1, self._max_turns + 1):
            llm_response = self._provider.generate(
                messages=messages,
                tools=tool_schemas,
                model=self._model,
                temperature=self._temperature,
            )
            messages.append(
                LLMMessage(
                    role="assistant",
                    content=llm_response.content,
                    tool_calls=tuple(llm_response.tool_calls),
                )
            )

            if not llm_response.tool_calls:
                return self._failure_with_optional_recovery(
                    messages=messages,
                    tool_schemas=tool_schemas,
                    turn=turn,
                    fallback_error=(
                        "Agent stopped calling tools without calling "
                        f"'{TASK_COMPLETE_TOOL_NAME}' to finalize the session."
                    ),
                    reason="no_tool_calls",
                )

            function_calls = [
                FunctionCall(name=tool_call.name, args=tool_call.args, call_id=tool_call.call_id)
                for tool_call in llm_response.tool_calls
            ]
            processed = LocalAgentExecutor.process_function_calls(
                function_calls=function_calls,
                allowed_tool_names=allowed_tool_names,
                enforce_complete_task=False,
            )
            if processed.errors:
                return self._failure_with_optional_recovery(
                    messages=messages,
                    tool_schemas=tool_schemas,
                    turn=turn,
                    fallback_error="; ".join(processed.errors),
                    reason="protocol_violation",
                )

            request_infos = [
                ToolCallRequestInfo(
                    name=call.name,
                    args=dict(call.args),
                    call_id=call.call_id or str(uuid4()),
                    prompt_id=f"turn-{turn}",
                )
                for call in function_calls
                if call.name != TASK_COMPLETE_TOOL_NAME and call.name in allowed_tool_names
            ]
            if request_infos:
                completed_calls = schedule_agent_tools(
                    config=self._config,
                    requests=request_infos,
                    scheduler_id=self._scheduler_id,
                )
                for completed_call in completed_calls:
                    messages.append(
                        LLMMessage(
                            role="tool",
                            tool_call_id=completed_call.request.call_id,
                            content=self._serialize_tool_response(completed_call),
                            name=completed_call.request.name,
                        )
                    )
                    if completed_call.status in {CoreToolCallStatus.ERROR, CoreToolCallStatus.CANCELLED}:
                        return self._failure_with_optional_recovery(
                            messages=messages,
                            tool_schemas=tool_schemas,
                            turn=turn,
                            fallback_error=completed_call.response.error or "Tool execution failed.",
                            reason="tool_execution_failed",
                        )

            if processed.task_completed:
                final_result = processed.submitted_output or ""
                completion_error = self._validate_completion_result(final_result)
                if completion_error is not None:
                    return self._failure_with_optional_recovery(
                        messages=messages,
                        tool_schemas=tool_schemas,
                        turn=turn,
                        fallback_error=completion_error,
                        reason="completion_schema_violation",
                    )
                return AgentRunResult(
                    success=True,
                    result=final_result,
                    error=None,
                    turns=turn,
                )

            if not request_infos:
                return self._failure_with_optional_recovery(
                    messages=messages,
                    tool_schemas=tool_schemas,
                    turn=turn,
                    fallback_error=(
                        "Agent did not invoke executable tools and did not call "
                        f"'{TASK_COMPLETE_TOOL_NAME}'."
                    ),
                    reason="no_executable_calls",
                )

        return self._failure_with_optional_recovery(
            messages=messages,
            tool_schemas=tool_schemas,
            turn=self._max_turns,
            fallback_error=f"Agent exceeded max turns ({self._max_turns}) without completing task.",
            reason="max_turns",
        )

    def _build_allowed_tool_names(self) -> set[str]:
        available = set(self._config.tool_registry.get_all_tool_names())
        agent_names = set(self._config.get_agent_registry().get_all_agent_names())
        return LocalAgentExecutor.build_allowed_tool_names(
            available_tool_names=available,
            all_agent_names=agent_names,
        )

    @staticmethod
    def _completion_tool_schema() -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": TASK_COMPLETE_TOOL_NAME,
                "description": "Submit the final answer and terminate the task.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "result": {
                            "type": "string",
                            "description": "Final answer for the task.",
                        }
                    },
                    "required": ["result"],
                    "additionalProperties": True,
                },
            },
        }

    @staticmethod
    def _serialize_tool_response(completed_call: Any) -> str:
        payload: dict[str, Any] = {
            "status": completed_call.status.value,
            "result_display": completed_call.response.result_display,
            "error": completed_call.response.error,
            "error_type": completed_call.response.error_type,
        }
        return json.dumps(payload, default=str, sort_keys=True)

    def _failure_with_optional_recovery(
        self,
        *,
        messages: list[LLMMessage],
        tool_schemas: list[dict[str, Any]],
        turn: int,
        fallback_error: str,
        reason: str,
    ) -> AgentRunResult:
        if not self._enable_recovery_turn:
            return AgentRunResult(success=False, result=None, error=fallback_error, turns=turn)

        recovered = self._attempt_final_recovery(messages, tool_schemas, turn=turn + 1, reason=reason)
        if recovered is not None:
            return recovered
        return AgentRunResult(success=False, result=None, error=fallback_error, turns=turn)

    def _attempt_final_recovery(
        self,
        messages: list[LLMMessage],
        tool_schemas: list[dict[str, Any]],
        *,
        turn: int,
        reason: str,
    ) -> AgentRunResult | None:
        recovery_prompt = (
            f"Execution limit reached ({reason}). Final recovery turn: call "
            f"`{TASK_COMPLETE_TOOL_NAME}` immediately with your best available answer. "
            "Do not call any other tools."
        )
        recovery_messages = [*messages, LLMMessage(role="user", content=recovery_prompt)]
        try:
            recovery_response = self._provider.generate(
                messages=recovery_messages,
                tools=tool_schemas,
                model=self._model,
                temperature=self._temperature,
            )
        except Exception:
            return None
        recovery_calls = [
            FunctionCall(name=call.name, args=call.args, call_id=call.call_id)
            for call in recovery_response.tool_calls
        ]
        if not recovery_calls:
            return None
        non_complete = [call for call in recovery_calls if call.name != TASK_COMPLETE_TOOL_NAME]
        if non_complete:
            return None

        processed = LocalAgentExecutor.process_function_calls(
            function_calls=recovery_calls,
            allowed_tool_names=set(),
            enforce_complete_task=False,
        )
        if not processed.task_completed:
            return None
        final_result = processed.submitted_output or ""
        completion_error = self._validate_completion_result(final_result)
        if completion_error is not None:
            return None
        return AgentRunResult(
            success=True,
            result=final_result,
            error=None,
            turns=turn,
        )

    def _validate_completion_result(self, result: str) -> str | None:
        if self._completion_schema is None:
            return None
        return validate_completion_output(result, self._completion_schema)
