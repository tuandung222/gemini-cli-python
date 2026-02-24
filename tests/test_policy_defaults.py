from pathlib import Path

from py_agent_runtime.policy.types import PolicyCheckInput, PolicyDecision
from py_agent_runtime.runtime.config import RuntimeConfig
from py_agent_runtime.runtime.modes import ApprovalMode


def test_runtime_config_loads_default_policy_rules() -> None:
    config = RuntimeConfig(target_dir=Path("."), interactive=True)

    read_result = config.policy_engine.check(PolicyCheckInput(name="read_file"))
    write_result = config.policy_engine.check(PolicyCheckInput(name="write_file"))

    assert read_result.decision == PolicyDecision.ALLOW
    assert write_result.decision == PolicyDecision.ASK_USER


def test_auto_edit_mode_allows_write_tools_from_default_policies() -> None:
    config = RuntimeConfig(
        target_dir=Path("."),
        interactive=True,
        approval_mode=ApprovalMode.AUTO_EDIT,
    )

    write_result = config.policy_engine.check(PolicyCheckInput(name="write_file"))
    replace_result = config.policy_engine.check(PolicyCheckInput(name="replace"))

    assert write_result.decision == PolicyDecision.ALLOW
    assert replace_result.decision == PolicyDecision.ALLOW


def test_yolo_mode_enables_catch_all_allow_except_explicit_ask_user() -> None:
    config = RuntimeConfig(
        target_dir=Path("."),
        interactive=True,
        approval_mode=ApprovalMode.YOLO,
    )

    arbitrary_result = config.policy_engine.check(
        PolicyCheckInput(name="dangerous_custom_tool", args={"x": 1})
    )
    ask_user_result = config.policy_engine.check(PolicyCheckInput(name="ask_user"))

    assert arbitrary_result.decision == PolicyDecision.ALLOW
    assert ask_user_result.decision == PolicyDecision.ASK_USER


def test_plan_mode_applies_catch_all_deny_with_explicit_read_tool_allow() -> None:
    config = RuntimeConfig(
        target_dir=Path("."),
        interactive=True,
        approval_mode=ApprovalMode.PLAN,
    )

    read_result = config.policy_engine.check(PolicyCheckInput(name="read_file"))
    write_result = config.policy_engine.check(PolicyCheckInput(name="write_file"))

    assert read_result.decision == PolicyDecision.ALLOW
    assert write_result.decision == PolicyDecision.DENY
