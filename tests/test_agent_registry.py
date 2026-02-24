from pathlib import Path

from py_agent_runtime.agents.registry import (
    DYNAMIC_POLICY_SOURCE,
    PRIORITY_SUBAGENT_TOOL,
    AgentRegistry,
)
from py_agent_runtime.agents.types import AgentDefinition, AgentKind
from py_agent_runtime.policy.types import PolicyDecision, PolicyRule
from py_agent_runtime.runtime.config import RuntimeConfig


def _dynamic_rules(config: RuntimeConfig, tool_name: str) -> list[PolicyRule]:
    return [
        rule
        for rule in config.policy_engine.get_rules()
        if rule.tool_name == tool_name and rule.source == DYNAMIC_POLICY_SOURCE
    ]


def test_register_local_agent_adds_dynamic_allow_policy() -> None:
    config = RuntimeConfig(target_dir=Path("."), interactive=True)
    registry = AgentRegistry(config)

    ok = registry.register_agent(
        AgentDefinition(
            kind=AgentKind.LOCAL,
            name="codebase_investigator",
            description="Investigate codebase",
        )
    )

    assert ok is True
    assert registry.get_definition("codebase_investigator") is not None
    dynamic_rules = _dynamic_rules(config, "codebase_investigator")
    assert len(dynamic_rules) == 1
    assert dynamic_rules[0].decision == PolicyDecision.ALLOW
    assert dynamic_rules[0].priority == PRIORITY_SUBAGENT_TOOL


def test_register_remote_agent_adds_dynamic_ask_user_policy() -> None:
    config = RuntimeConfig(target_dir=Path("."), interactive=True)
    registry = AgentRegistry(config)

    ok = registry.register_agent(
        AgentDefinition(
            kind=AgentKind.REMOTE,
            name="remote_triage",
            description="Remote triage agent",
        )
    )

    assert ok is True
    dynamic_rules = _dynamic_rules(config, "remote_triage")
    assert len(dynamic_rules) == 1
    assert dynamic_rules[0].decision == PolicyDecision.ASK_USER


def test_user_policy_prevents_dynamic_policy_registration() -> None:
    config = RuntimeConfig(target_dir=Path("."), interactive=True)
    config.policy_engine.add_rule(
        PolicyRule(
            tool_name="custom_agent",
            decision=PolicyDecision.DENY,
            priority=10.0,
            source="user.policy.toml",
        )
    )
    registry = AgentRegistry(config)

    ok = registry.register_agent(
        AgentDefinition(
            kind=AgentKind.LOCAL,
            name="custom_agent",
            description="User-defined agent",
        )
    )

    assert ok is True
    assert _dynamic_rules(config, "custom_agent") == []


def test_overwriting_agent_replaces_existing_dynamic_policy() -> None:
    config = RuntimeConfig(target_dir=Path("."), interactive=True)
    registry = AgentRegistry(config)

    first = AgentDefinition(
        kind=AgentKind.LOCAL,
        name="overwritten_agent",
        description="Local variant",
    )
    second = AgentDefinition(
        kind=AgentKind.REMOTE,
        name="overwritten_agent",
        description="Remote variant",
    )

    assert registry.register_agent(first) is True
    assert registry.register_agent(second) is True

    dynamic_rules = _dynamic_rules(config, "overwritten_agent")
    assert len(dynamic_rules) == 1
    assert dynamic_rules[0].decision == PolicyDecision.ASK_USER


def test_invalid_agent_definition_is_rejected() -> None:
    config = RuntimeConfig(target_dir=Path("."), interactive=True)
    registry = AgentRegistry(config)

    ok = registry.register_agent(
        AgentDefinition(
            kind=AgentKind.LOCAL,
            name="",
            description="",
        )
    )

    assert ok is False
    assert registry.get_all_definitions() == []

