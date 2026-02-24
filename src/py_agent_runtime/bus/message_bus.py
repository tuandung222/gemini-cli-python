from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from typing import Any

from py_agent_runtime.bus.types import Message, MessageBusType
from py_agent_runtime.policy.engine import PolicyEngine
from py_agent_runtime.policy.types import PolicyCheckInput, PolicyDecision
from py_agent_runtime.tools.base import ToolConfirmationOutcome

MessageHandler = Callable[[Message], None]


class MessageBus:
    def __init__(self, policy_engine: PolicyEngine | None = None) -> None:
        self._subscribers: dict[MessageBusType, list[MessageHandler]] = defaultdict(list)
        self._policy_engine = policy_engine

    def subscribe(self, message_type: MessageBusType, handler: MessageHandler) -> None:
        self._subscribers[message_type].append(handler)

    def unsubscribe(self, message_type: MessageBusType, handler: MessageHandler) -> None:
        self._subscribers[message_type] = [
            registered for registered in self._subscribers[message_type] if registered != handler
        ]

    def publish(self, message_type: MessageBusType, payload: dict[str, Any]) -> None:
        if (
            message_type == MessageBusType.TOOL_CONFIRMATION_REQUEST
            and self._policy_engine is not None
        ):
            self._publish_confirmation_request_with_policy(payload)
            return

        message = Message(type=message_type, payload=payload)
        for handler in self._subscribers[message_type]:
            handler(message)

    def request(
        self,
        request_type: MessageBusType,
        payload: dict[str, Any],
        response_type: MessageBusType,
        matcher: Callable[[Message], bool] | None = None,
    ) -> Message:
        response: Message | None = None

        def _handler(message: Message) -> None:
            nonlocal response
            if matcher is None or matcher(message):
                response = message

        self.subscribe(response_type, _handler)
        try:
            self.publish(request_type, payload)
        finally:
            self.unsubscribe(response_type, _handler)

        if response is None:
            raise TimeoutError(
                f"Request timed out waiting for {response_type.value} in synchronous bus flow."
            )
        return response

    def _publish_confirmation_request_with_policy(self, payload: dict[str, Any]) -> None:
        if self._policy_engine is None:
            self.publish(
                MessageBusType.TOOL_CONFIRMATION_RESPONSE,
                {
                    "correlation_id": str(payload.get("correlation_id", "")),
                    "confirmed": False,
                    "outcome": ToolConfirmationOutcome.CANCEL.value,
                    "requires_user_confirmation": False,
                    "error": "Policy engine is not configured.",
                },
            )
            return

        correlation_id = str(payload.get("correlation_id", ""))
        tool_call = payload.get("tool_call")
        if not isinstance(tool_call, dict):
            self.publish(
                MessageBusType.TOOL_CONFIRMATION_RESPONSE,
                {
                    "correlation_id": correlation_id,
                    "confirmed": False,
                    "outcome": ToolConfirmationOutcome.CANCEL.value,
                    "requires_user_confirmation": False,
                },
            )
            return

        name = str(tool_call.get("name", ""))
        args = tool_call.get("args")
        args_mapping = args if isinstance(args, dict) else {}
        server_name_raw = payload.get("server_name")
        server_name = server_name_raw if isinstance(server_name_raw, str) else None

        decision = self._policy_engine.check(
            PolicyCheckInput(name=name, args=args_mapping, server_name=server_name)
        ).decision

        if decision == PolicyDecision.ALLOW:
            self.publish(
                MessageBusType.TOOL_CONFIRMATION_RESPONSE,
                {
                    "correlation_id": correlation_id,
                    "confirmed": True,
                    "outcome": ToolConfirmationOutcome.PROCEED_ONCE.value,
                    "requires_user_confirmation": False,
                },
            )
            return

        if decision == PolicyDecision.DENY:
            self.publish(
                MessageBusType.TOOL_CONFIRMATION_RESPONSE,
                {
                    "correlation_id": correlation_id,
                    "confirmed": False,
                    "outcome": ToolConfirmationOutcome.CANCEL.value,
                    "requires_user_confirmation": False,
                },
            )
            return

        # ASK_USER path: forward request to UI handlers.
        message = Message(type=MessageBusType.TOOL_CONFIRMATION_REQUEST, payload=payload)
        handlers = list(self._subscribers[MessageBusType.TOOL_CONFIRMATION_REQUEST])
        if not handlers:
            # No human confirmation handler wired: fail closed.
            self.publish(
                MessageBusType.TOOL_CONFIRMATION_RESPONSE,
                {
                    "correlation_id": correlation_id,
                    "confirmed": False,
                    "outcome": ToolConfirmationOutcome.CANCEL.value,
                    "requires_user_confirmation": True,
                    "error": "No confirmation handler is registered.",
                },
            )
            return

        for handler in handlers:
            handler(message)
