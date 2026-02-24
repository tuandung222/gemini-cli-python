from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from re import Pattern
from typing import Any, Mapping, Sequence

from py_agent_runtime.runtime.modes import ApprovalMode


class PolicyDecision(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    ASK_USER = "ask_user"


@dataclass(frozen=True)
class PolicyRule:
    decision: PolicyDecision
    tool_name: str | None = None
    args_pattern: Pattern[str] | None = None
    priority: float = 0.0
    modes: Sequence[ApprovalMode] | None = None
    allow_redirection: bool = False
    source: str | None = None
    deny_message: str | None = None
    name: str | None = None


@dataclass(frozen=True)
class PolicyCheckInput:
    name: str
    args: Mapping[str, Any] | None = None
    server_name: str | None = None


@dataclass(frozen=True)
class CheckResult:
    decision: PolicyDecision
    rule: PolicyRule | None = None

