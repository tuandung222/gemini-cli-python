from __future__ import annotations

from pathlib import Path

from py_agent_runtime.runtime.config import RuntimeConfig
from py_agent_runtime.runtime.modes import ApprovalMode
from py_agent_runtime.tools.enter_plan_mode import EnterPlanModeTool
from py_agent_runtime.tools.exit_plan_mode import ExitPlanModeTool


def test_enter_plan_mode_sets_approval_mode(tmp_path: Path) -> None:
    config = RuntimeConfig(target_dir=tmp_path, plan_enabled=True)
    tool = EnterPlanModeTool()

    result = tool.execute(config, {"reason": "Analyze first"})
    assert result.error is None
    assert config.get_approval_mode() == ApprovalMode.PLAN
    assert "Analyze first" in (result.llm_content or "")


def test_exit_plan_mode_approves_and_switches_to_auto_edit(tmp_path: Path) -> None:
    config = RuntimeConfig(target_dir=tmp_path, plan_enabled=True)
    config.set_approval_mode(ApprovalMode.PLAN)

    plan_file = config.plans_dir / "plan.md"
    plan_file.parent.mkdir(parents=True, exist_ok=True)
    plan_file.write_text("# Plan\n- Step\n", encoding="utf-8")

    tool = ExitPlanModeTool()
    result = tool.execute(
        config,
        {
            "plan_path": str(plan_file.relative_to(config.target_dir)),
            "approved": True,
            "approval_mode": "autoEdit",
        },
    )
    assert result.error is None
    assert config.get_approval_mode() == ApprovalMode.AUTO_EDIT
    assert config.get_approved_plan_path() == plan_file


def test_exit_plan_mode_rejection_with_feedback(tmp_path: Path) -> None:
    config = RuntimeConfig(target_dir=tmp_path, plan_enabled=True)
    config.set_approval_mode(ApprovalMode.PLAN)
    plan_file = config.plans_dir / "plan.md"
    plan_file.parent.mkdir(parents=True, exist_ok=True)
    plan_file.write_text("# Plan\n- Step\n", encoding="utf-8")

    tool = ExitPlanModeTool()
    result = tool.execute(
        config,
        {
            "plan_path": str(plan_file.relative_to(config.target_dir)),
            "approved": False,
            "feedback": "Need more details",
        },
    )
    assert result.error is None
    assert "Need more details" in result.llm_content
    assert config.get_approval_mode() == ApprovalMode.PLAN


def test_exit_plan_mode_rejects_invalid_approval_mode(tmp_path: Path) -> None:
    config = RuntimeConfig(target_dir=tmp_path, plan_enabled=True)
    config.set_approval_mode(ApprovalMode.PLAN)
    plan_file = config.plans_dir / "plan.md"
    plan_file.parent.mkdir(parents=True, exist_ok=True)
    plan_file.write_text("# Plan\n- Step\n", encoding="utf-8")

    tool = ExitPlanModeTool()
    result = tool.execute(
        config,
        {
            "plan_path": str(plan_file.relative_to(config.target_dir)),
            "approved": True,
            "approval_mode": "yolo",
        },
    )
    assert result.error is not None
    assert "Invalid approval_mode" in result.error


def test_exit_plan_mode_fails_on_invalid_path(tmp_path: Path) -> None:
    config = RuntimeConfig(target_dir=tmp_path, plan_enabled=True)
    config.set_approval_mode(ApprovalMode.PLAN)
    tool = ExitPlanModeTool()
    result = tool.execute(
        config,
        {"plan_path": "../outside.md", "approved": True},
    )
    assert result.error is not None
    assert "Access denied" in result.error
