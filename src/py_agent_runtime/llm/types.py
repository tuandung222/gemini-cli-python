from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


LLMRole = Literal["system", "user", "assistant", "tool"]


@dataclass(frozen=True)
class LLMToolCall:
    name: str
    args: dict[str, Any]
    call_id: str | None = None


@dataclass(frozen=True)
class LLMMessage:
    role: LLMRole
    content: str | None = None
    tool_call_id: str | None = None
    name: str | None = None
    tool_calls: tuple[LLMToolCall, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class LLMTurnResponse:
    content: str | None
    tool_calls: list[LLMToolCall]
    finish_reason: str | None = None
    raw: Any | None = None

