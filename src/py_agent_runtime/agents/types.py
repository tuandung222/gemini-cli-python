from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class AgentKind(str, Enum):
    LOCAL = "local"
    REMOTE = "remote"


@dataclass(frozen=True)
class AgentDefinition:
    name: str
    description: str
    kind: AgentKind = AgentKind.LOCAL
    display_name: str | None = None
    enabled: bool = True
    tool_names: tuple[str, ...] | None = None
    completion_schema: dict[str, Any] | None = None
