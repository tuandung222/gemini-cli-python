from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

from py_agent_runtime.agents.llm_runner import LLMAgentRunner
from py_agent_runtime.llm.base_provider import LLMProvider
from py_agent_runtime.llm.types import LLMMessage, LLMToolCall, LLMTurnResponse
from py_agent_runtime.policy.types import PolicyDecision, PolicyRule
from py_agent_runtime.runtime.config import RuntimeConfig
from py_agent_runtime.tools.base import BaseTool, ToolResult


class EchoTool(BaseTool):
    name = "echo"
    description = "Echo text."

    def __init__(self) -> None:
        self.calls: list[str] = []

    def validate_params(self, params: Mapping[str, Any]) -> str | None:
        text = params.get("text")
        if not isinstance(text, str):
            return "text is required."
        return None

    def execute(self, config: RuntimeConfig, params: Mapping[str, Any]) -> ToolResult:
        text = str(params["text"])
        self.calls.append(text)
        return ToolResult(llm_content=text, return_display=text)


class FakeProvider(LLMProvider):
    def __init__(self, responses: Sequence[LLMTurnResponse]) -> None:
        self._responses = list(responses)
        self.calls: list[list[LLMMessage]] = []

    def generate(
        self,
        messages: Sequence[LLMMessage],
        tools: Sequence[dict[str, Any]] | None = None,
        *,
        model: str | None = None,
        temperature: float | None = None,
    ) -> LLMTurnResponse:
        self.calls.append(list(messages))
        if not self._responses:
            raise RuntimeError("No more fake responses.")
        return self._responses.pop(0)


def _allow_tool(config: RuntimeConfig, tool_name: str) -> None:
    config.policy_engine.add_rule(
        PolicyRule(
            tool_name=tool_name,
            decision=PolicyDecision.ALLOW,
            priority=9.0,
        )
    )


def test_llm_runner_success_flow() -> None:
    config = RuntimeConfig(target_dir=Path("."), interactive=True)
    echo = EchoTool()
    config.tool_registry.register_tool(echo)
    _allow_tool(config, "echo")

    provider = FakeProvider(
        responses=[
            LLMTurnResponse(
                content=None,
                tool_calls=[
                    LLMToolCall(name="echo", args={"text": "hello"}, call_id="call_echo_1")
                ],
            ),
            LLMTurnResponse(
                content=None,
                tool_calls=[
                    LLMToolCall(
                        name="complete_task",
                        args={"result": "final answer"},
                        call_id="call_done_1",
                    )
                ],
            ),
        ]
    )
    runner = LLMAgentRunner(config=config, provider=provider, max_turns=4)
    result = runner.run("do task")

    assert result.success is True
    assert result.result == "final answer"
    assert result.turns == 2
    assert echo.calls == ["hello"]
    # Second provider call should include prior tool response message.
    assert any(message.role == "tool" for message in provider.calls[1])


def test_llm_runner_rejects_unauthorized_tool_call() -> None:
    config = RuntimeConfig(target_dir=Path("."), interactive=True)
    provider = FakeProvider(
        responses=[
            LLMTurnResponse(
                content=None,
                tool_calls=[LLMToolCall(name="write_file", args={"path": "x"})],
            )
        ]
    )
    runner = LLMAgentRunner(config=config, provider=provider, max_turns=2)
    result = runner.run("do task")

    assert result.success is False
    assert result.error is not None
    assert "Unauthorized tool call: 'write_file'" in result.error


def test_llm_runner_requires_complete_task() -> None:
    config = RuntimeConfig(target_dir=Path("."), interactive=True)
    provider = FakeProvider(
        responses=[LLMTurnResponse(content="done", tool_calls=[])]
    )
    runner = LLMAgentRunner(config=config, provider=provider, max_turns=2)
    result = runner.run("do task")

    assert result.success is False
    assert result.error is not None
    assert "complete_task" in result.error


def test_llm_runner_uses_recovery_turn_on_protocol_violation() -> None:
    config = RuntimeConfig(target_dir=Path("."), interactive=True)
    provider = FakeProvider(
        responses=[
            LLMTurnResponse(content="stopped", tool_calls=[]),
            LLMTurnResponse(
                content=None,
                tool_calls=[
                    LLMToolCall(name="complete_task", args={"result": "recovered answer"})
                ],
            ),
        ]
    )
    runner = LLMAgentRunner(config=config, provider=provider, max_turns=1)
    result = runner.run("do task")

    assert result.success is True
    assert result.result == "recovered answer"
    assert result.turns == 2


def test_llm_runner_can_disable_recovery_turn() -> None:
    config = RuntimeConfig(target_dir=Path("."), interactive=True)
    echo = EchoTool()
    config.tool_registry.register_tool(echo)
    _allow_tool(config, "echo")
    provider = FakeProvider(
        responses=[
            LLMTurnResponse(
                content=None,
                tool_calls=[LLMToolCall(name="echo", args={"text": "work"})],
            )
        ]
    )
    runner = LLMAgentRunner(
        config=config,
        provider=provider,
        max_turns=1,
        enable_recovery_turn=False,
    )
    result = runner.run("do task")

    assert result.success is False
    assert result.error is not None
    assert "exceeded max turns" in result.error
