from __future__ import annotations

from pathlib import Path

from py_agent_runtime.policy.types import PolicyDecision, PolicyRule
from py_agent_runtime.runtime.config import RuntimeConfig
from py_agent_runtime.runtime.modes import ApprovalMode
from py_agent_runtime.scheduler.scheduler import Scheduler
from py_agent_runtime.scheduler.types import CoreToolCallStatus, ToolCallRequestInfo
from py_agent_runtime.tools.enter_plan_mode import EnterPlanModeTool
from py_agent_runtime.tools.exit_plan_mode import ExitPlanModeTool


def _allow(config: RuntimeConfig, tool_name: str) -> None:
    config.policy_engine.add_rule(
        PolicyRule(tool_name=tool_name, decision=PolicyDecision.ALLOW, priority=9.0)
    )


def test_golden_planning_directive_flow(tmp_path: Path) -> None:
    config = RuntimeConfig(target_dir=tmp_path, interactive=True, plan_enabled=True)
    config.tool_registry.register_tool(EnterPlanModeTool())
    config.tool_registry.register_tool(ExitPlanModeTool())
    _allow(config, "enter_plan_mode")
    _allow(config, "exit_plan_mode")

    scheduler = Scheduler(config)
    enter_result = scheduler.schedule([ToolCallRequestInfo(name="enter_plan_mode", args={})])[0]
    assert enter_result.status == CoreToolCallStatus.SUCCESS
    assert config.get_approval_mode() == ApprovalMode.PLAN

    plan_file = config.plans_dir / "implementation.md"
    plan_file.parent.mkdir(parents=True, exist_ok=True)
    plan_file.write_text("# Plan\n- Step 1\n", encoding="utf-8")
    plan_path = plan_file.relative_to(config.target_dir).as_posix()

    exit_result = scheduler.schedule(
        [
            ToolCallRequestInfo(
                name="exit_plan_mode",
                args={"plan_path": plan_path, "approved": True, "approval_mode": "default"},
            )
        ]
    )[0]
    assert exit_result.status == CoreToolCallStatus.SUCCESS
    assert config.get_approval_mode() == ApprovalMode.DEFAULT
    assert config.get_approved_plan_path() == plan_file


def test_golden_inquiry_without_plan_file_fails(tmp_path: Path) -> None:
    config = RuntimeConfig(target_dir=tmp_path, interactive=True, plan_enabled=True)
    config.tool_registry.register_tool(ExitPlanModeTool())
    _allow(config, "exit_plan_mode")

    scheduler = Scheduler(config)
    result = scheduler.schedule(
        [
            ToolCallRequestInfo(
                name="exit_plan_mode",
                args={"plan_path": ".gemini/tmp/plans/missing.md", "approved": True},
            )
        ]
    )[0]
    assert result.status == CoreToolCallStatus.ERROR
    assert result.response.error_type == "execution_failed"
    assert result.response.error is not None
    assert "does not exist" in result.response.error


def test_golden_policy_deny_path(tmp_path: Path) -> None:
    config = RuntimeConfig(target_dir=tmp_path, interactive=True, plan_enabled=True)
    config.tool_registry.register_tool(EnterPlanModeTool())
    config.policy_engine.add_rule(
        PolicyRule(
            tool_name="enter_plan_mode",
            decision=PolicyDecision.DENY,
            priority=9.0,
            deny_message="Denied by policy for test.",
        )
    )

    scheduler = Scheduler(config)
    result = scheduler.schedule([ToolCallRequestInfo(name="enter_plan_mode", args={})])[0]
    assert result.status == CoreToolCallStatus.ERROR
    assert result.response.error_type == "policy_violation"
    assert result.response.error == "Denied by policy for test."


def test_golden_ask_user_without_confirmation_handler_cancels(tmp_path: Path) -> None:
    config = RuntimeConfig(target_dir=tmp_path, interactive=True, plan_enabled=True)
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
    assert result.status == CoreToolCallStatus.CANCELLED
    assert result.response.error_type == "cancelled"


def test_golden_non_interactive_ask_user_path_is_denied(tmp_path: Path) -> None:
    config = RuntimeConfig(target_dir=tmp_path, interactive=False, plan_enabled=True)
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
        "non-interactive mode" in result.response.error.lower()
        or "denied by policy" in result.response.error.lower()
    )
