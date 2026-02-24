from __future__ import annotations

from uuid import uuid4

from py_agent_runtime.bus.types import Message, MessageBusType
from py_agent_runtime.runtime.config import RuntimeConfig
from py_agent_runtime.scheduler.types import ToolCallRequestInfo
from py_agent_runtime.tools.base import ToolConfirmationOutcome


def resolve_confirmation(
    config: RuntimeConfig, request: ToolCallRequestInfo
) -> ToolConfirmationOutcome:
    correlation_id = str(uuid4())
    response = config.get_message_bus().request(
        request_type=MessageBusType.TOOL_CONFIRMATION_REQUEST,
        payload={
            "correlation_id": correlation_id,
            "tool_call": {
                "name": request.name,
                "args": request.args,
            },
        },
        response_type=MessageBusType.TOOL_CONFIRMATION_RESPONSE,
        matcher=lambda message: _match_correlation(message, correlation_id),
    )

    raw_outcome = response.payload.get("outcome")
    if isinstance(raw_outcome, str):
        try:
            return ToolConfirmationOutcome(raw_outcome)
        except ValueError:
            pass

    confirmed = bool(response.payload.get("confirmed"))
    return (
        ToolConfirmationOutcome.PROCEED_ONCE
        if confirmed
        else ToolConfirmationOutcome.CANCEL
    )


def _match_correlation(message: Message, correlation_id: str) -> bool:
    return str(message.payload.get("correlation_id", "")) == correlation_id

