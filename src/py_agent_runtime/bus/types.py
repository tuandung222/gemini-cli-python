from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class MessageBusType(str, Enum):
    TOOL_CONFIRMATION_REQUEST = "tool-confirmation-request"
    TOOL_CONFIRMATION_RESPONSE = "tool-confirmation-response"
    UPDATE_POLICY = "update-policy"
    TOOL_CALLS_UPDATE = "tool-calls-update"
    ASK_USER_REQUEST = "ask-user-request"
    ASK_USER_RESPONSE = "ask-user-response"


@dataclass(frozen=True)
class Message:
    type: MessageBusType
    payload: dict[str, Any]

