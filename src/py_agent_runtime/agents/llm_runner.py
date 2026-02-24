from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from py_agent_runtime.agents.agent_scheduler import schedule_agent_tools
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
    ) -> None:
        self._config = config
        self._provider = provider
        self._max_turns = max_turns
        self._scheduler_id = scheduler_id
        self._model = model
        self._temperature = temperature

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
                return AgentRunResult(
                    success=False,
                    result=None,
                    error=(
                        "Agent stopped calling tools without calling "
                        f"'{TASK_COMPLETE_TOOL_NAME}' to finalize the session."
                    ),
                    turns=turn,
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
                return AgentRunResult(
                    success=False,
                    result=None,
                    error="; ".join(processed.errors),
                    turns=turn,
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
                        return AgentRunResult(
                            success=False,
                            result=None,
                            error=completed_call.response.error or "Tool execution failed.",
                            turns=turn,
                        )

            if processed.task_completed:
                return AgentRunResult(
                    success=True,
                    result=processed.submitted_output or "",
                    error=None,
                    turns=turn,
                )

            if not request_infos:
                return AgentRunResult(
                    success=False,
                    result=None,
                    error=(
                        "Agent did not invoke executable tools and did not call "
                        f"'{TASK_COMPLETE_TOOL_NAME}'."
                    ),
                    turns=turn,
                )

        return AgentRunResult(
            success=False,
            result=None,
            error=f"Agent exceeded max turns ({self._max_turns}) without completing task.",
            turns=self._max_turns,
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
