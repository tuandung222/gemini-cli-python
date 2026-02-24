from __future__ import annotations

from pathlib import Path

from py_agent_runtime.policy.types import PolicyCheckInput, PolicyDecision, PolicyRule
from py_agent_runtime.runtime.config import RuntimeConfig


def test_runtime_config_propagates_non_interactive_to_policy_engine() -> None:
    config = RuntimeConfig(target_dir=Path("."), interactive=False)
    config.policy_engine.add_rule(
        PolicyRule(tool_name="ask_user_tool", decision=PolicyDecision.ASK_USER, priority=1.0)
    )

    result = config.policy_engine.check(PolicyCheckInput(name="ask_user_tool"))
    assert result.decision == PolicyDecision.DENY


def test_runtime_config_set_interactive_updates_policy_engine() -> None:
    config = RuntimeConfig(target_dir=Path("."), interactive=True)
    config.policy_engine.add_rule(
        PolicyRule(tool_name="ask_user_tool", decision=PolicyDecision.ASK_USER, priority=1.0)
    )

    before = config.policy_engine.check(PolicyCheckInput(name="ask_user_tool"))
    assert before.decision == PolicyDecision.ASK_USER

    config.set_interactive(False)
    after = config.policy_engine.check(PolicyCheckInput(name="ask_user_tool"))
    assert after.decision == PolicyDecision.DENY

