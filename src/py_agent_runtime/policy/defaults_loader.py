from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from py_agent_runtime.policy.loader import load_policies_from_toml
from py_agent_runtime.policy.types import PolicyRule

DEFAULT_POLICY_TIER = 1


@dataclass(frozen=True)
class DefaultPolicyLoadResult:
    rules: list[PolicyRule]
    errors: list[str]


def default_policy_directory() -> Path:
    return Path(__file__).resolve().parent / "defaults"


def load_default_policies() -> DefaultPolicyLoadResult:
    load_result = load_policies_from_toml(
        [default_policy_directory()],
        get_policy_tier=lambda _path: DEFAULT_POLICY_TIER,
    )
    return DefaultPolicyLoadResult(rules=load_result.rules, errors=load_result.errors)
