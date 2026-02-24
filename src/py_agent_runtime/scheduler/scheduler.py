from __future__ import annotations

from py_agent_runtime.scheduler.confirmation import resolve_confirmation
from py_agent_runtime.scheduler.policy_bridge import update_policy_after_confirmation
from py_agent_runtime.policy.types import PolicyCheckInput, PolicyDecision
from py_agent_runtime.runtime.config import RuntimeConfig
from py_agent_runtime.scheduler.state_manager import SchedulerStateManager
from py_agent_runtime.scheduler.types import (
    CompletedToolCall,
    CoreToolCallStatus,
    ToolCallRequestInfo,
    ToolCallResponseInfo,
)
from py_agent_runtime.tools.base import ToolConfirmationOutcome
from py_agent_runtime.tools.registry import ToolRegistry


class Scheduler:
    def __init__(
        self,
        config: RuntimeConfig,
        state: SchedulerStateManager | None = None,
        tool_registry: ToolRegistry | None = None,
    ) -> None:
        self._config = config
        self._state = state or SchedulerStateManager()
        self._tool_registry = tool_registry or config.tool_registry

    def schedule(self, requests: list[ToolCallRequestInfo]) -> list[CompletedToolCall]:
        self._state.enqueue(requests)

        while True:
            request = self._state.dequeue()
            if request is None:
                break
            self._state.complete(self._process_single_request(request))

        return self._state.drain_completed()

    def _process_single_request(self, request: ToolCallRequestInfo) -> CompletedToolCall:
        confirmation_outcome: ToolConfirmationOutcome | None = None
        tool = self._tool_registry.get_tool(request.name)
        if tool is None:
            return CompletedToolCall(
                status=CoreToolCallStatus.ERROR,
                request=request,
                response=ToolCallResponseInfo(
                    call_id=request.call_id,
                    result_display=None,
                    error=f"Tool \"{request.name}\" not found.",
                    error_type="tool_not_registered",
                ),
            )

        validation_error = tool.validate_params(request.args)
        if validation_error:
            return CompletedToolCall(
                status=CoreToolCallStatus.ERROR,
                request=request,
                response=ToolCallResponseInfo(
                    call_id=request.call_id,
                    result_display=None,
                    error=validation_error,
                    error_type="invalid_tool_params",
                ),
            )

        policy_result = self._config.policy_engine.check(
            PolicyCheckInput(name=request.name, args=request.args)
        )
        if policy_result.decision == PolicyDecision.DENY:
            deny_message = (
                policy_result.rule.deny_message
                if policy_result.rule and policy_result.rule.deny_message
                else "Tool execution denied by policy."
            )
            return CompletedToolCall(
                status=CoreToolCallStatus.ERROR,
                request=request,
                response=ToolCallResponseInfo(
                    call_id=request.call_id,
                    result_display=None,
                    error=deny_message,
                    error_type="policy_violation",
                ),
            )

        if policy_result.decision == PolicyDecision.ASK_USER and not self._config.interactive:
            return CompletedToolCall(
                status=CoreToolCallStatus.ERROR,
                request=request,
                response=ToolCallResponseInfo(
                    call_id=request.call_id,
                    result_display=None,
                    error=(
                        f"Tool execution for \"{request.name}\" requires user confirmation, "
                        "which is unavailable in non-interactive mode."
                    ),
                    error_type="policy_violation",
                ),
            )

        if policy_result.decision == PolicyDecision.ASK_USER:
            confirmation_outcome = resolve_confirmation(self._config, request)
            update_policy_after_confirmation(
                self._config, request, confirmation_outcome
            )
            if confirmation_outcome == ToolConfirmationOutcome.CANCEL:
                return CompletedToolCall(
                    status=CoreToolCallStatus.CANCELLED,
                    request=request,
                    response=ToolCallResponseInfo(
                        call_id=request.call_id,
                        result_display="Cancelled",
                        error="User denied execution.",
                        error_type="cancelled",
                        data={"outcome": confirmation_outcome.value},
                    ),
                )

        try:
            result = tool.execute(self._config, request.args)
            if result.error:
                return CompletedToolCall(
                    status=CoreToolCallStatus.ERROR,
                    request=request,
                    response=ToolCallResponseInfo(
                        call_id=request.call_id,
                        result_display=result.return_display,
                        error=result.error,
                        error_type="execution_failed",
                    ),
                )
            return CompletedToolCall(
                status=CoreToolCallStatus.SUCCESS,
                request=request,
                response=ToolCallResponseInfo(
                    call_id=request.call_id,
                    result_display=result.return_display,
                    data=(
                        {"confirmation_outcome": confirmation_outcome.value}
                        if confirmation_outcome is not None
                        else None
                    ),
                ),
            )
        except Exception as exc:  # pragma: no cover
            return CompletedToolCall(
                status=CoreToolCallStatus.ERROR,
                request=request,
                response=ToolCallResponseInfo(
                    call_id=request.call_id,
                    result_display=None,
                    error=str(exc),
                    error_type="unhandled_exception",
                ),
            )
