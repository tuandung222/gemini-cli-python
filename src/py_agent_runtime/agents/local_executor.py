from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping


TASK_COMPLETE_TOOL_NAME = "complete_task"


class AgentTerminateMode(str, Enum):
    GOAL = "goal"
    ERROR_NO_COMPLETE_TASK_CALL = "error_no_complete_task_call"
    ERROR = "error"


@dataclass(frozen=True)
class FunctionCall:
    name: str
    args: Mapping[str, Any]
    call_id: str | None = None


@dataclass(frozen=True)
class ProcessedTurn:
    task_completed: bool
    submitted_output: str | None
    terminate_reason: AgentTerminateMode | None
    errors: list[str]


class LocalAgentExecutor:
    """
    Baseline local executor protocol.

    This intentionally focuses on the critical TS parity contract:
    - The agent must call `complete_task` to terminate successfully.
    - `complete_task` must include a non-empty `result` argument.
    """

    @staticmethod
    def process_function_calls(function_calls: list[FunctionCall]) -> ProcessedTurn:
        if not function_calls:
            return ProcessedTurn(
                task_completed=False,
                submitted_output=None,
                terminate_reason=AgentTerminateMode.ERROR_NO_COMPLETE_TASK_CALL,
                errors=[
                    "Agent stopped calling tools but did not call "
                    f"'{TASK_COMPLETE_TOOL_NAME}' to finalize the session."
                ],
            )

        errors: list[str] = []
        submitted_output: str | None = None
        task_completed = False

        for call in function_calls:
            if call.name != TASK_COMPLETE_TOOL_NAME:
                continue

            if task_completed:
                errors.append("Task already marked complete in this turn. Ignoring duplicate call.")
                continue

            result = call.args.get("result")
            if result is None or (isinstance(result, str) and not result.strip()):
                errors.append(
                    'Missing required "result" argument. You must provide your findings when '
                    "calling complete_task."
                )
                continue

            submitted_output = str(result)
            task_completed = True

        if task_completed:
            return ProcessedTurn(
                task_completed=True,
                submitted_output=submitted_output,
                terminate_reason=AgentTerminateMode.GOAL,
                errors=errors,
            )

        if errors:
            return ProcessedTurn(
                task_completed=False,
                submitted_output=None,
                terminate_reason=AgentTerminateMode.ERROR,
                errors=errors,
            )

        return ProcessedTurn(
            task_completed=False,
            submitted_output=None,
            terminate_reason=AgentTerminateMode.ERROR_NO_COMPLETE_TASK_CALL,
            errors=[
                "Agent stopped calling tools but did not call "
                f"'{TASK_COMPLETE_TOOL_NAME}' to finalize the session."
            ],
        )

