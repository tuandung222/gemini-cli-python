from __future__ import annotations

from py_agent_runtime.policy.types import PolicyDecision, PolicyRule
from py_agent_runtime.runtime.config import RuntimeConfig
from py_agent_runtime.scheduler.types import ToolCallRequestInfo
from py_agent_runtime.tools.base import ToolConfirmationOutcome


def update_policy_after_confirmation(
    config: RuntimeConfig,
    request: ToolCallRequestInfo,
    outcome: ToolConfirmationOutcome,
) -> None:
    if outcome != ToolConfirmationOutcome.PROCEED_ALWAYS:
        return

    config.policy_engine.add_rule(
        PolicyRule(
            tool_name=request.name,
            decision=PolicyDecision.ALLOW,
            priority=2.95,
            source="Dynamic (Confirmed)",
        )
    )

