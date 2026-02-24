from py_agent_runtime.bus.message_bus import MessageBus
from py_agent_runtime.bus.types import Message, MessageBusType
from py_agent_runtime.policy.engine import PolicyEngine
from py_agent_runtime.policy.types import PolicyDecision, PolicyRule


def test_message_bus_confirmation_auto_allow_from_policy() -> None:
    policy = PolicyEngine(
        rules=[
            PolicyRule(
                tool_name="sample_tool",
                decision=PolicyDecision.ALLOW,
                priority=9.0,
            )
        ]
    )
    bus = MessageBus(policy_engine=policy)

    response = bus.request(
        request_type=MessageBusType.TOOL_CONFIRMATION_REQUEST,
        payload={
            "correlation_id": "c1",
            "tool_call": {"name": "sample_tool", "args": {}},
        },
        response_type=MessageBusType.TOOL_CONFIRMATION_RESPONSE,
        matcher=lambda message: message.payload.get("correlation_id") == "c1",
    )
    assert response.payload["confirmed"] is True
    assert response.payload["outcome"] == "proceed_once"


def test_message_bus_confirmation_auto_deny_from_policy() -> None:
    policy = PolicyEngine(
        rules=[
            PolicyRule(
                tool_name="sample_tool",
                decision=PolicyDecision.DENY,
                priority=9.0,
            )
        ]
    )
    bus = MessageBus(policy_engine=policy)

    response = bus.request(
        request_type=MessageBusType.TOOL_CONFIRMATION_REQUEST,
        payload={
            "correlation_id": "c2",
            "tool_call": {"name": "sample_tool", "args": {}},
        },
        response_type=MessageBusType.TOOL_CONFIRMATION_RESPONSE,
        matcher=lambda message: message.payload.get("correlation_id") == "c2",
    )
    assert response.payload["confirmed"] is False
    assert response.payload["outcome"] == "cancel"


def test_message_bus_ask_user_round_trip() -> None:
    policy = PolicyEngine(
        rules=[
            PolicyRule(
                tool_name="sample_tool",
                decision=PolicyDecision.ASK_USER,
                priority=9.0,
            )
        ]
    )
    bus = MessageBus(policy_engine=policy)

    def _handler(message: Message) -> None:
        cid = message.payload["correlation_id"]
        bus.publish(
            MessageBusType.TOOL_CONFIRMATION_RESPONSE,
            {
                "correlation_id": cid,
                "confirmed": True,
                "outcome": "proceed_always",
                "requires_user_confirmation": True,
            },
        )

    bus.subscribe(MessageBusType.TOOL_CONFIRMATION_REQUEST, _handler)

    response = bus.request(
        request_type=MessageBusType.TOOL_CONFIRMATION_REQUEST,
        payload={
            "correlation_id": "c3",
            "tool_call": {"name": "sample_tool", "args": {}},
        },
        response_type=MessageBusType.TOOL_CONFIRMATION_RESPONSE,
        matcher=lambda message: message.payload.get("correlation_id") == "c3",
    )
    assert response.payload["confirmed"] is True
    assert response.payload["outcome"] == "proceed_always"


def test_message_bus_request_times_out_when_no_response_message_emitted() -> None:
    bus = MessageBus(policy_engine=PolicyEngine())

    try:
        bus.request(
            request_type=MessageBusType.UPDATE_POLICY,
            payload={"tool_name": "echo"},
            response_type=MessageBusType.ASK_USER_RESPONSE,
        )
        raise AssertionError("Expected TimeoutError to be raised.")
    except TimeoutError as exc:
        assert MessageBusType.ASK_USER_RESPONSE.value in str(exc)
