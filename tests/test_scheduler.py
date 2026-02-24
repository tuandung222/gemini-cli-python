from pathlib import Path
from typing import Any, Mapping

from py_agent_runtime.bus.types import Message, MessageBusType
from py_agent_runtime.policy.types import PolicyDecision, PolicyRule
from py_agent_runtime.runtime.config import RuntimeConfig
from py_agent_runtime.runtime.modes import ApprovalMode
from py_agent_runtime.scheduler.scheduler import Scheduler
from py_agent_runtime.scheduler.types import CoreToolCallStatus, ToolCallRequestInfo
from py_agent_runtime.tools.base import BaseTool, ToolResult
from py_agent_runtime.tools.enter_plan_mode import EnterPlanModeTool


class _WriteFileTestTool(BaseTool):
    name = "write_file"
    description = "Test write tool."

    def execute(self, config: RuntimeConfig, params: Mapping[str, Any]) -> ToolResult:
        return ToolResult(llm_content="ok", return_display="ok")


class _DangerousTestTool(BaseTool):
    name = "dangerous_custom_tool"
    description = "Test custom tool."

    def execute(self, config: RuntimeConfig, params: Mapping[str, Any]) -> ToolResult:
        return ToolResult(llm_content="ok", return_display="ok")


def test_scheduler_executes_allowed_tool() -> None:
    config = RuntimeConfig(target_dir=Path("."), interactive=True, plan_enabled=True)
    config.tool_registry.register_tool(EnterPlanModeTool())
    config.policy_engine.add_rule(
        PolicyRule(
            tool_name="enter_plan_mode",
            decision=PolicyDecision.ALLOW,
            priority=9.0,
        )
    )

    scheduler = Scheduler(config)
    results = scheduler.schedule([ToolCallRequestInfo(name="enter_plan_mode", args={})])
    assert len(results) == 1
    assert results[0].status == CoreToolCallStatus.SUCCESS


def test_scheduler_blocks_denied_tool() -> None:
    config = RuntimeConfig(target_dir=Path("."), interactive=True, plan_enabled=True)
    config.tool_registry.register_tool(EnterPlanModeTool())
    config.policy_engine.add_rule(
        PolicyRule(
            tool_name="enter_plan_mode",
            decision=PolicyDecision.DENY,
            priority=9.0,
        )
    )

    scheduler = Scheduler(config)
    results = scheduler.schedule([ToolCallRequestInfo(name="enter_plan_mode", args={})])
    assert len(results) == 1
    assert results[0].status == CoreToolCallStatus.ERROR
    assert results[0].response.error_type == "policy_violation"


def test_scheduler_ask_user_can_cancel() -> None:
    config = RuntimeConfig(target_dir=Path("."), interactive=True, plan_enabled=True)
    config.tool_registry.register_tool(EnterPlanModeTool())
    config.policy_engine.add_rule(
        PolicyRule(
            tool_name="enter_plan_mode",
            decision=PolicyDecision.ASK_USER,
            priority=2.0,
        )
    )

    def _confirmation_handler(message: Message) -> None:
        correlation_id = message.payload["correlation_id"]
        config.get_message_bus().publish(
            message_type=MessageBusType.TOOL_CONFIRMATION_RESPONSE,
            payload={
                "correlation_id": correlation_id,
                "confirmed": False,
                "outcome": "cancel",
                "requires_user_confirmation": True,
            },
        )

    config.get_message_bus().subscribe(
        message_type=MessageBusType.TOOL_CONFIRMATION_REQUEST,
        handler=_confirmation_handler,
    )

    scheduler = Scheduler(config)
    results = scheduler.schedule([ToolCallRequestInfo(name="enter_plan_mode", args={})])
    assert len(results) == 1
    assert results[0].status == CoreToolCallStatus.CANCELLED
    assert results[0].response.error_type == "cancelled"


def test_scheduler_proceed_always_updates_policy() -> None:
    config = RuntimeConfig(target_dir=Path("."), interactive=True, plan_enabled=True)
    config.tool_registry.register_tool(EnterPlanModeTool())
    config.policy_engine.add_rule(
        PolicyRule(
            tool_name="enter_plan_mode",
            decision=PolicyDecision.ASK_USER,
            priority=2.0,
        )
    )

    def _confirmation_handler(message: Message) -> None:
        correlation_id = message.payload["correlation_id"]
        config.get_message_bus().publish(
            message_type=MessageBusType.TOOL_CONFIRMATION_RESPONSE,
            payload={
                "correlation_id": correlation_id,
                "confirmed": True,
                "outcome": "proceed_always",
                "requires_user_confirmation": True,
            },
        )

    config.get_message_bus().subscribe(
        message_type=MessageBusType.TOOL_CONFIRMATION_REQUEST,
        handler=_confirmation_handler,
    )

    scheduler = Scheduler(config)
    first = scheduler.schedule([ToolCallRequestInfo(name="enter_plan_mode", args={})])
    assert first[0].status == CoreToolCallStatus.SUCCESS
    assert first[0].response.data == {"confirmation_outcome": "proceed_always"}

    config.get_message_bus().unsubscribe(
        message_type=MessageBusType.TOOL_CONFIRMATION_REQUEST,
        handler=_confirmation_handler,
    )

    second = scheduler.schedule([ToolCallRequestInfo(name="enter_plan_mode", args={})])
    assert second[0].status == CoreToolCallStatus.SUCCESS


def test_scheduler_results_do_not_leak_between_schedule_calls() -> None:
    config = RuntimeConfig(target_dir=Path("."), interactive=True, plan_enabled=True)
    config.tool_registry.register_tool(EnterPlanModeTool())
    config.policy_engine.add_rule(
        PolicyRule(
            tool_name="enter_plan_mode",
            decision=PolicyDecision.ALLOW,
            priority=9.0,
        )
    )

    scheduler = Scheduler(config)
    first = scheduler.schedule([ToolCallRequestInfo(name="enter_plan_mode", args={})])
    second = scheduler.schedule([ToolCallRequestInfo(name="enter_plan_mode", args={})])

    assert len(first) == 1
    assert len(second) == 1


def test_scheduler_non_interactive_blocks_ask_user_tools() -> None:
    config = RuntimeConfig(target_dir=Path("."), interactive=False, plan_enabled=True)
    config.tool_registry.register_tool(EnterPlanModeTool())
    config.policy_engine.add_rule(
        PolicyRule(
            tool_name="enter_plan_mode",
            decision=PolicyDecision.ASK_USER,
            priority=9.0,
        )
    )

    scheduler = Scheduler(config)
    result = scheduler.schedule([ToolCallRequestInfo(name="enter_plan_mode", args={})])[0]
    assert result.status == CoreToolCallStatus.ERROR
    assert result.response.error_type == "policy_violation"
    assert result.response.error is not None
    assert (
        "non-interactive mode" in result.response.error
        or "denied by policy" in result.response.error.lower()
    )


def test_scheduler_default_mode_write_tool_requires_confirmation() -> None:
    config = RuntimeConfig(target_dir=Path("."), interactive=True)
    config.tool_registry.register_tool(_WriteFileTestTool())

    scheduler = Scheduler(config)
    result = scheduler.schedule(
        [ToolCallRequestInfo(name="write_file", args={"file_path": "a.txt", "content": "x"})]
    )[0]

    assert result.status == CoreToolCallStatus.CANCELLED
    assert result.response.error_type == "cancelled"


def test_scheduler_auto_edit_mode_auto_approves_default_write_tool() -> None:
    config = RuntimeConfig(
        target_dir=Path("."),
        interactive=True,
        approval_mode=ApprovalMode.AUTO_EDIT,
    )
    config.tool_registry.register_tool(_WriteFileTestTool())

    scheduler = Scheduler(config)
    result = scheduler.schedule(
        [ToolCallRequestInfo(name="write_file", args={"file_path": "a.txt", "content": "x"})]
    )[0]

    assert result.status == CoreToolCallStatus.SUCCESS
    assert result.response.result_display == "ok"


def test_scheduler_yolo_mode_auto_approves_catch_all_tool() -> None:
    config = RuntimeConfig(
        target_dir=Path("."),
        interactive=True,
        approval_mode=ApprovalMode.YOLO,
    )
    config.tool_registry.register_tool(_DangerousTestTool())

    scheduler = Scheduler(config)
    result = scheduler.schedule([ToolCallRequestInfo(name="dangerous_custom_tool", args={})])[0]

    assert result.status == CoreToolCallStatus.SUCCESS
    assert result.response.result_display == "ok"
