from py_agent_runtime.agents.local_executor import (
    AgentTerminateMode,
    FunctionCall,
    LocalAgentExecutor,
    TASK_COMPLETE_TOOL_NAME,
)


def test_complete_task_required() -> None:
    result = LocalAgentExecutor.process_function_calls([])
    assert result.task_completed is False
    assert result.terminate_reason == AgentTerminateMode.ERROR_NO_COMPLETE_TASK_CALL


def test_complete_task_success_with_result() -> None:
    result = LocalAgentExecutor.process_function_calls(
        [FunctionCall(name=TASK_COMPLETE_TOOL_NAME, args={"result": "done"})]
    )
    assert result.task_completed is True
    assert result.terminate_reason == AgentTerminateMode.GOAL
    assert result.submitted_output == "done"


def test_complete_task_missing_result_is_error() -> None:
    result = LocalAgentExecutor.process_function_calls(
        [FunctionCall(name=TASK_COMPLETE_TOOL_NAME, args={})]
    )
    assert result.task_completed is False
    assert result.terminate_reason == AgentTerminateMode.ERROR
    assert any("Missing required" in error for error in result.errors)

