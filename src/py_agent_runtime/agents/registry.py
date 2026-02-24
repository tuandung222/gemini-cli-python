from __future__ import annotations

from py_agent_runtime.agents.types import AgentDefinition, AgentKind
from py_agent_runtime.policy.types import PolicyDecision, PolicyRule
from py_agent_runtime.runtime.config import RuntimeConfig

DYNAMIC_POLICY_SOURCE = "AgentRegistry (Dynamic)"
PRIORITY_SUBAGENT_TOOL = 1.05


def get_model_config_alias(definition: AgentDefinition) -> str:
    return f"{definition.name}-config"


class AgentRegistry:
    def __init__(self, config: RuntimeConfig) -> None:
        self._config = config
        self._agents: dict[str, AgentDefinition] = {}
        self._all_definitions: dict[str, AgentDefinition] = {}

    def register_agent(self, definition: AgentDefinition) -> bool:
        if not definition.name.strip() or not definition.description.strip():
            return False

        self._all_definitions[definition.name] = definition
        if not definition.enabled:
            return False

        self._agents[definition.name] = definition
        self._add_agent_policy(definition)
        return True

    def get_definition(self, name: str) -> AgentDefinition | None:
        return self._agents.get(name)

    def get_discovered_definition(self, name: str) -> AgentDefinition | None:
        return self._all_definitions.get(name)

    def get_all_definitions(self) -> list[AgentDefinition]:
        return list(self._agents.values())

    def get_all_discovered_definitions(self) -> list[AgentDefinition]:
        return list(self._all_definitions.values())

    def get_all_agent_names(self) -> list[str]:
        return sorted(self._agents.keys())

    def clear(self) -> None:
        self._agents.clear()
        self._all_definitions.clear()

    def _add_agent_policy(self, definition: AgentDefinition) -> None:
        policy_engine = self._config.policy_engine

        # Respect user-authored policies for this tool and skip dynamic registration.
        if policy_engine.has_rule_for_tool(definition.name, ignore_dynamic=True):
            return

        policy_engine.remove_rules_for_tool(
            definition.name,
            source=DYNAMIC_POLICY_SOURCE,
        )
        policy_engine.add_rule(
            PolicyRule(
                tool_name=definition.name,
                decision=(
                    PolicyDecision.ALLOW
                    if definition.kind == AgentKind.LOCAL
                    else PolicyDecision.ASK_USER
                ),
                priority=PRIORITY_SUBAGENT_TOOL,
                source=DYNAMIC_POLICY_SOURCE,
            )
        )

