from __future__ import annotations

import json
from typing import Any, Iterable

from py_agent_runtime.policy.types import (
    CheckResult,
    PolicyCheckInput,
    PolicyDecision,
    PolicyRule,
)
from py_agent_runtime.runtime.modes import ApprovalMode


def _stable_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _is_wildcard_pattern(name: str) -> bool:
    return name.endswith("__*")


def _matches_wildcard(pattern: str, tool_name: str) -> bool:
    prefix = pattern[:-3]
    return tool_name.startswith(prefix + "__")


class PolicyEngine:
    def __init__(
        self,
        rules: Iterable[PolicyRule] | None = None,
        default_decision: PolicyDecision = PolicyDecision.ASK_USER,
        non_interactive: bool = False,
        approval_mode: ApprovalMode = ApprovalMode.DEFAULT,
    ) -> None:
        self._rules = sorted(
            list(rules or []), key=lambda item: item.priority, reverse=True
        )
        self._default_decision = default_decision
        self._non_interactive = non_interactive
        self._approval_mode = approval_mode

    def set_approval_mode(self, mode: ApprovalMode) -> None:
        self._approval_mode = mode

    def get_approval_mode(self) -> ApprovalMode:
        return self._approval_mode

    def set_non_interactive(self, non_interactive: bool) -> None:
        self._non_interactive = non_interactive

    def get_non_interactive(self) -> bool:
        return self._non_interactive

    def add_rule(self, rule: PolicyRule) -> None:
        self._rules.append(rule)
        self._rules.sort(key=lambda item: item.priority, reverse=True)

    def get_rules(self) -> list[PolicyRule]:
        return list(self._rules)

    def has_rule_for_tool(self, tool_name: str, ignore_dynamic: bool = False) -> bool:
        for rule in self._rules:
            if rule.tool_name != tool_name:
                continue
            if ignore_dynamic and rule.source == "AgentRegistry (Dynamic)":
                continue
            return True
        return False

    def remove_rules_for_tool(self, tool_name: str, source: str | None = None) -> None:
        def _keep(rule: PolicyRule) -> bool:
            if rule.tool_name != tool_name:
                return True
            if source is None:
                return False
            return rule.source != source

        self._rules = [rule for rule in self._rules if _keep(rule)]

    def check(self, tool_call: PolicyCheckInput) -> CheckResult:
        stringified_args = _stable_json(tool_call.args or {})

        for rule in self._rules:
            if rule.modes and self._approval_mode not in rule.modes:
                continue

            if rule.tool_name:
                if _is_wildcard_pattern(rule.tool_name):
                    if not _matches_wildcard(rule.tool_name, tool_call.name):
                        continue
                elif rule.tool_name != tool_call.name:
                    continue

            if rule.args_pattern and not rule.args_pattern.search(stringified_args):
                continue

            return CheckResult(self._apply_non_interactive(rule.decision), rule)

        return CheckResult(self._apply_non_interactive(self._default_decision), None)

    def _apply_non_interactive(self, decision: PolicyDecision) -> PolicyDecision:
        if self._non_interactive and decision == PolicyDecision.ASK_USER:
            return PolicyDecision.DENY
        return decision
