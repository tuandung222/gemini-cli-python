from pathlib import Path

from py_agent_runtime.bus.types import Message, MessageBusType
from py_agent_runtime.policy.types import PolicyDecision, PolicyRule
from py_agent_runtime.runtime.config import RuntimeConfig
from py_agent_runtime.scheduler.scheduler import Scheduler
from py_agent_runtime.scheduler.types import CoreToolCallStatus, ToolCallRequestInfo
from py_agent_runtime.tools.enter_plan_mode import EnterPlanModeTool


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
