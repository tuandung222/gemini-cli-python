from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4


class CoreToolCallStatus(str, Enum):
    VALIDATING = "validating"
    SCHEDULED = "scheduled"
    AWAITING_APPROVAL = "awaiting_approval"
    EXECUTING = "executing"
    SUCCESS = "success"
    ERROR = "error"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class ToolCallRequestInfo:
    name: str
    args: dict[str, Any]
    call_id: str = field(default_factory=lambda: str(uuid4()))
    scheduler_id: str = "root"
    parent_call_id: str | None = None
    prompt_id: str = "default"
    is_client_initiated: bool = False


@dataclass(frozen=True)
class ToolCallResponseInfo:
    call_id: str
    result_display: Any | None
    error: str | None = None
    error_type: str | None = None
    data: dict[str, Any] | None = None


@dataclass(frozen=True)
class CompletedToolCall:
    status: CoreToolCallStatus
    request: ToolCallRequestInfo
    response: ToolCallResponseInfo
