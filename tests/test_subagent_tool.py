from pathlib import Path
from typing import Any, Mapping

from py_agent_runtime.agents.subagent_tool import SubagentToolWrapper
from py_agent_runtime.agents.types import AgentDefinition, AgentKind
from py_agent_runtime.policy.types import PolicyDecision, PolicyRule
from py_agent_runtime.runtime.config import RuntimeConfig
from py_agent_runtime.scheduler.scheduler import Scheduler
from py_agent_runtime.scheduler.types import CoreToolCallStatus, ToolCallRequestInfo
from py_agent_runtime.tools.base import BaseTool, ToolResult


class EchoTool(BaseTool):
    name = "echo"
    description = "Return the input text."

    def __init__(self) -> None:
        self.calls: list[str] = []

    def validate_params(self, params: Mapping[str, Any]) -> str | None:
        text = params.get("text")
        if not isinstance(text, str) or not text.strip():
            return "text is required."
        return None

    def execute(self, config: RuntimeConfig, params: Mapping[str, Any]) -> ToolResult:
        text = str(params["text"])
        self.calls.append(text)
        return ToolResult(llm_content=text, return_display={"text": text})


class UppercaseTool(BaseTool):
    name = "uppercase"
    description = "Upper-case a string."

    def validate_params(self, params: Mapping[str, Any]) -> str | None:
        text = params.get("text")
        if not isinstance(text, str):
            return "text is required."
        return None

    def execute(self, config: RuntimeConfig, params: Mapping[str, Any]) -> ToolResult:
        return ToolResult(llm_content=str(params["text"]).upper(), return_display="ok")


def _allow_tool(config: RuntimeConfig, tool_name: str) -> None:
    config.policy_engine.add_rule(
        PolicyRule(tool_name=tool_name, decision=PolicyDecision.ALLOW, priority=9.0)
    )


def test_subagent_tool_executes_turns_and_completes_task() -> None:
    config = RuntimeConfig(target_dir=Path("."), interactive=True)
    echo = EchoTool()
    config.tool_registry.register_tool(echo)
    _allow_tool(config, "echo")

    definition = AgentDefinition(
        kind=AgentKind.LOCAL,
        name="research_agent",
        description="Research assistant",
        tool_names=("echo",),
    )
    assert config.get_agent_registry().register_agent(definition) is True
    subagent_tool = SubagentToolWrapper(definition).build()
    config.tool_registry.register_tool(subagent_tool)

    scheduler = Scheduler(config)
    calls = [
        ToolCallRequestInfo(
            name="research_agent",
            args={
                "turns": [
                    [{"name": "echo", "args": {"text": "first"}}],
                    [{"name": "complete_task", "args": {"result": "done"}}],
                ]
            },
        )
    ]
    result = scheduler.schedule(calls)[0]

    assert result.status == CoreToolCallStatus.SUCCESS
    assert result.response.result_display == {"agent": "research_agent", "turn": 2, "result": "done"}
    assert echo.calls == ["first"]


def test_subagent_tool_blocks_recursive_self_call() -> None:
    config = RuntimeConfig(target_dir=Path("."), interactive=True)
    definition = AgentDefinition(
        kind=AgentKind.LOCAL,
        name="research_agent",
        description="Research assistant",
    )
    assert config.get_agent_registry().register_agent(definition) is True
    subagent_tool = SubagentToolWrapper(definition).build()
    config.tool_registry.register_tool(subagent_tool)

    scheduler = Scheduler(config)
    call = ToolCallRequestInfo(
        name="research_agent",
        args={"turns": [[{"name": "research_agent", "args": {}}]]},
    )
    result = scheduler.schedule([call])[0]

    assert result.status == CoreToolCallStatus.ERROR
    assert result.response.error_type == "execution_failed"
    assert "Unauthorized tool call: 'research_agent'" in str(result.response.error)


def test_subagent_tool_respects_configured_tool_allowlist() -> None:
    config = RuntimeConfig(target_dir=Path("."), interactive=True)
    config.tool_registry.register_tool(EchoTool())
    config.tool_registry.register_tool(UppercaseTool())
    _allow_tool(config, "echo")
    _allow_tool(config, "uppercase")

    definition = AgentDefinition(
        kind=AgentKind.LOCAL,
        name="research_agent",
        description="Research assistant",
        tool_names=("echo",),
    )
    assert config.get_agent_registry().register_agent(definition) is True
    subagent_tool = SubagentToolWrapper(definition).build()
    config.tool_registry.register_tool(subagent_tool)

    scheduler = Scheduler(config)
    call = ToolCallRequestInfo(
        name="research_agent",
        args={"turns": [[{"name": "uppercase", "args": {"text": "x"}}]]},
    )
    result = scheduler.schedule([call])[0]

    assert result.status == CoreToolCallStatus.ERROR
    assert result.response.error_type == "execution_failed"
    assert "Unauthorized tool call: 'uppercase'" in str(result.response.error)


def test_subagent_tool_requires_complete_task() -> None:
    config = RuntimeConfig(target_dir=Path("."), interactive=True)
    config.tool_registry.register_tool(EchoTool())
    _allow_tool(config, "echo")

    definition = AgentDefinition(
        kind=AgentKind.LOCAL,
        name="research_agent",
        description="Research assistant",
        tool_names=("echo",),
    )
    assert config.get_agent_registry().register_agent(definition) is True
    subagent_tool = SubagentToolWrapper(definition).build()
    config.tool_registry.register_tool(subagent_tool)

    scheduler = Scheduler(config)
    call = ToolCallRequestInfo(
        name="research_agent",
        args={"turns": [[{"name": "echo", "args": {"text": "still working"}}]]},
    )
    result = scheduler.schedule([call])[0]

    assert result.status == CoreToolCallStatus.ERROR
    assert result.response.error_type == "execution_failed"
    assert "stopped without calling 'complete_task'" in str(result.response.error)


def test_subagent_tool_enforces_completion_schema() -> None:
    config = RuntimeConfig(target_dir=Path("."), interactive=True)
    config.tool_registry.register_tool(EchoTool())
    _allow_tool(config, "echo")

    definition = AgentDefinition(
        kind=AgentKind.LOCAL,
        name="research_agent",
        description="Research assistant",
        tool_names=("echo",),
        completion_schema={
            "type": "object",
            "required": ["summary"],
            "properties": {"summary": {"type": "string"}},
        },
    )
    assert config.get_agent_registry().register_agent(definition) is True
    subagent_tool = SubagentToolWrapper(definition).build()
    config.tool_registry.register_tool(subagent_tool)

    scheduler = Scheduler(config)
    call = ToolCallRequestInfo(
        name="research_agent",
        args={
            "turns": [
                [{"name": "complete_task", "args": {"result": "plain result"}}],
            ]
        },
    )
    result = scheduler.schedule([call])[0]

    assert result.status == CoreToolCallStatus.ERROR
    assert result.response.error_type == "execution_failed"
    assert "Completion output does not satisfy schema" in str(result.response.error)


def test_subagent_tool_completion_schema_success_with_structured_output() -> None:
    config = RuntimeConfig(target_dir=Path("."), interactive=True)
    definition = AgentDefinition(
        kind=AgentKind.LOCAL,
        name="research_agent",
        description="Research assistant",
        completion_schema={
            "type": "object",
            "required": ["summary", "score"],
            "properties": {
                "summary": {"type": "string"},
                "score": {"type": "integer"},
            },
        },
    )
    assert config.get_agent_registry().register_agent(definition) is True
    subagent_tool = SubagentToolWrapper(definition).build()
    config.tool_registry.register_tool(subagent_tool)

    scheduler = Scheduler(config)
    call = ToolCallRequestInfo(
        name="research_agent",
        args={
            "turns": [
                [
                    {
                        "name": "complete_task",
                        "args": {"result": {"summary": "ok", "score": 1}},
                    }
                ],
            ]
        },
    )
    result = scheduler.schedule([call])[0]

    assert result.status == CoreToolCallStatus.SUCCESS
