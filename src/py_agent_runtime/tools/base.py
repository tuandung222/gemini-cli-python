from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, TYPE_CHECKING

if TYPE_CHECKING:
    from py_agent_runtime.runtime.config import RuntimeConfig


class ToolConfirmationOutcome(str, Enum):
    PROCEED_ONCE = "proceed_once"
    PROCEED_ALWAYS = "proceed_always"
    CANCEL = "cancel"


@dataclass(frozen=True)
class ToolResult:
    llm_content: str
    return_display: str | dict[str, Any] | None = None
    error: str | None = None


class BaseTool(ABC):
    name: str
    description: str
    parameters_json_schema: dict[str, Any] | None = None

    def validate_params(self, params: Mapping[str, Any]) -> str | None:
        return None

    @abstractmethod
    def execute(self, config: RuntimeConfig, params: Mapping[str, Any]) -> ToolResult:
        raise NotImplementedError
