from py_agent_runtime.agents.local_executor import (
    AgentTerminateMode,
    FunctionCall,
    LocalAgentExecutor,
    TASK_COMPLETE_TOOL_NAME,
    create_unauthorized_tool_error,
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


def test_unauthorized_tool_call_is_error() -> None:
    result = LocalAgentExecutor.process_function_calls(
        [FunctionCall(name="write_file", args={"path": "x"})],
        allowed_tool_names={"read_file"},
    )
    assert result.task_completed is False
    assert result.terminate_reason == AgentTerminateMode.ERROR
    assert result.errors == [create_unauthorized_tool_error("write_file")]


def test_authorized_non_complete_tool_still_requires_complete_task() -> None:
    result = LocalAgentExecutor.process_function_calls(
        [FunctionCall(name="read_file", args={"path": "x"})],
        allowed_tool_names={"read_file"},
    )
    assert result.task_completed is False
    assert result.terminate_reason == AgentTerminateMode.ERROR_NO_COMPLETE_TASK_CALL


def test_build_allowed_tool_names_filters_subagents() -> None:
    allowed = LocalAgentExecutor.build_allowed_tool_names(
        available_tool_names={"read_file", "write_file", "generalist"},
        all_agent_names={"generalist"},
    )
    assert allowed == {"read_file", "write_file"}


def test_build_allowed_tool_names_filters_missing_tools() -> None:
    allowed = LocalAgentExecutor.build_allowed_tool_names(
        available_tool_names={"read_file", "write_file"},
        all_agent_names={"generalist"},
        configured_tool_names=["read_file", "generalist", "nonexistent"],
    )
    assert allowed == {"read_file"}


def test_process_function_calls_can_skip_complete_task_requirement() -> None:
    result = LocalAgentExecutor.process_function_calls(
        [FunctionCall(name="read_file", args={"path": "x"})],
        allowed_tool_names={"read_file"},
        enforce_complete_task=False,
    )
    assert result.task_completed is False
    assert result.terminate_reason is None
    assert result.errors == []
