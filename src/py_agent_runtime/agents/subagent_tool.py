from __future__ import annotations

from typing import Any, Mapping

from py_agent_runtime.agents.agent_scheduler import schedule_agent_tools
from py_agent_runtime.agents.local_executor import (
    FunctionCall,
    LocalAgentExecutor,
    TASK_COMPLETE_TOOL_NAME,
)
from py_agent_runtime.agents.types import AgentDefinition
from py_agent_runtime.runtime.config import RuntimeConfig
from py_agent_runtime.scheduler.types import CoreToolCallStatus, ToolCallRequestInfo
from py_agent_runtime.tools.base import BaseTool, ToolResult
from py_agent_runtime.tools.registry import ToolRegistry


class SubagentToolWrapper:
    def __init__(self, definition: AgentDefinition) -> None:
        self._definition = definition

    def build(self) -> "SubagentTool":
        return SubagentTool(self._definition)


class SubagentTool(BaseTool):
    def __init__(self, definition: AgentDefinition) -> None:
        self._definition = definition
        self.name = definition.name
        self.description = definition.description

    def validate_params(self, params: Mapping[str, Any]) -> str | None:
        turns = params.get("turns")
        if not isinstance(turns, list) or not turns:
            return "`turns` must be a non-empty array of turn tool calls."

        for idx, turn in enumerate(turns, start=1):
            if not isinstance(turn, list):
                return f"turn #{idx} must be an array of tool calls."
            for call_idx, call in enumerate(turn, start=1):
                if not isinstance(call, dict):
                    return f"turn #{idx} call #{call_idx} must be an object."
                name = call.get("name")
                args = call.get("args")
                if not isinstance(name, str) or not name.strip():
                    return f"turn #{idx} call #{call_idx}: `name` must be a non-empty string."
                if not isinstance(args, dict):
                    return f"turn #{idx} call #{call_idx}: `args` must be an object."
        return None

    def execute(self, config: RuntimeConfig, params: Mapping[str, Any]) -> ToolResult:
        validation_error = self.validate_params(params)
        if validation_error:
            return ToolResult(llm_content=validation_error, return_display="Error", error=validation_error)

        raw_turns = params.get("turns")
        assert isinstance(raw_turns, list)  # validated above

        allowed_tool_names = self._build_allowed_tool_names(config)
        agent_tool_registry = self._build_agent_tool_registry(config, allowed_tool_names)
        scheduler_id = f"subagent:{self._definition.name}"

        for turn_index, raw_turn in enumerate(raw_turns, start=1):
            assert isinstance(raw_turn, list)  # validated above
            function_calls = self._to_function_calls(raw_turn)
            processed = LocalAgentExecutor.process_function_calls(
                function_calls=function_calls,
                allowed_tool_names=allowed_tool_names,
                enforce_complete_task=False,
            )
            if processed.errors:
                message = (
                    f"Subagent '{self._definition.name}' protocol error on turn #{turn_index}: "
                    + "; ".join(processed.errors)
                )
                return ToolResult(
                    llm_content=message,
                    return_display="Subagent protocol error",
                    error=message,
                )

            tool_requests = [
                ToolCallRequestInfo(name=call.name, args=dict(call.args))
                for call in function_calls
                if call.name != TASK_COMPLETE_TOOL_NAME and call.name in allowed_tool_names
            ]
            if tool_requests:
                completed_calls = schedule_agent_tools(
                    config=config,
                    requests=tool_requests,
                    scheduler_id=scheduler_id,
                    tool_registry=agent_tool_registry,
                )
                failed = [
                    completed
                    for completed in completed_calls
                    if completed.status in {CoreToolCallStatus.ERROR, CoreToolCallStatus.CANCELLED}
                ]
                if failed:
                    first = failed[0]
                    error = first.response.error or "Unknown error during subagent tool execution."
                    message = (
                        f"Subagent '{self._definition.name}' tool execution failed on turn #{turn_index}: "
                        f"{first.request.name}: {error}"
                    )
                    return ToolResult(
                        llm_content=message,
                        return_display="Subagent execution failed",
                        error=message,
                    )

            if processed.task_completed:
                result = processed.submitted_output or ""
                return ToolResult(
                    llm_content=(
                        f"Subagent '{self._definition.name}' finished successfully with result: {result}"
                    ),
                    return_display={
                        "agent": self._definition.name,
                        "turn": turn_index,
                        "result": result,
                    },
                )

        message = (
            f"Subagent '{self._definition.name}' stopped without calling "
            f"'{TASK_COMPLETE_TOOL_NAME}'."
        )
        return ToolResult(
            llm_content=message,
            return_display="Subagent protocol error",
            error=message,
        )

    def _build_allowed_tool_names(self, config: RuntimeConfig) -> set[str]:
        available = set(config.tool_registry.get_all_tool_names())
        all_agents = set(config.get_agent_registry().get_all_agent_names())
        all_agents.add(self._definition.name)
        configured = list(self._definition.tool_names) if self._definition.tool_names is not None else None
        return LocalAgentExecutor.build_allowed_tool_names(
            available_tool_names=available,
            all_agent_names=all_agents,
            configured_tool_names=configured,
        )

    @staticmethod
    def _build_agent_tool_registry(config: RuntimeConfig, allowed_tool_names: set[str]) -> ToolRegistry:
        registry = ToolRegistry()
        for tool_name in sorted(allowed_tool_names):
            tool = config.tool_registry.get_tool(tool_name)
            if tool is not None:
                registry.register_tool(tool)
        return registry

    @staticmethod
    def _to_function_calls(raw_turn: list[object]) -> list[FunctionCall]:
        function_calls: list[FunctionCall] = []
        for raw_call in raw_turn:
            if not isinstance(raw_call, dict):  # defensive; validated earlier
                continue
            name = raw_call.get("name")
            args = raw_call.get("args")
            if not isinstance(name, str) or not isinstance(args, dict):
                continue
            function_calls.append(FunctionCall(name=name, args=args))
        return function_calls

