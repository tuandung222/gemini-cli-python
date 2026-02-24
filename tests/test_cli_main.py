from __future__ import annotations

import sys
import json

from py_agent_runtime.cli import main as cli_main
from py_agent_runtime.runtime.modes import ApprovalMode
from py_agent_runtime.agents.llm_runner import AgentRunResult
from py_agent_runtime.llm.types import LLMTurnResponse


class FakeProvider:
    def __init__(self, model: str = "gpt-4.1-mini") -> None:
        self.model = model

    def generate(self, messages, tools=None, *, model=None, temperature=None):  # noqa: ANN001, ANN201
        return LLMTurnResponse(content="pong", tool_calls=[], finish_reason="stop")


class FakeRunner:
    last_config = None

    def __init__(self, config, provider, **kwargs):  # noqa: ANN001, ANN003
        FakeRunner.last_config = config

    def run(self, user_prompt: str, system_prompt: str | None = None) -> AgentRunResult:
        return AgentRunResult(success=True, result="ok", error=None, turns=1)


def test_cli_chat_command(monkeypatch, capsys) -> None:  # noqa: ANN001
    monkeypatch.setattr(cli_main, "create_provider", lambda provider, model: FakeProvider(model))
    monkeypatch.setattr(sys, "argv", ["py-agent-runtime", "chat", "--prompt", "ping"])
    code = cli_main.main()
    captured = capsys.readouterr()
    assert code == 0
    assert "pong" in captured.out


def test_cli_without_command_shows_help(monkeypatch, capsys) -> None:  # noqa: ANN001
    monkeypatch.setattr(sys, "argv", ["py-agent-runtime"])
    code = cli_main.main()
    captured = capsys.readouterr()
    assert code == 1
    assert "usage:" in captured.out


def test_cli_run_command_wires_non_interactive_and_approval_mode(monkeypatch, capsys) -> None:  # noqa: ANN001
    monkeypatch.setattr(cli_main, "create_provider", lambda provider, model: FakeProvider(model))
    monkeypatch.setattr(cli_main, "LLMAgentRunner", FakeRunner)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "py-agent-runtime",
            "run",
            "--prompt",
            "Do work",
            "--non-interactive",
            "--approval-mode",
            "autoEdit",
        ],
    )
    code = cli_main.main()
    captured = capsys.readouterr()
    assert code == 0

    payload = json.loads(captured.out)
    assert payload["success"] is True
    assert payload["approval_mode"] == "autoEdit"
    assert payload["interactive"] is False

    assert FakeRunner.last_config is not None
    assert FakeRunner.last_config.interactive is False
    assert FakeRunner.last_config.get_approval_mode() == ApprovalMode.AUTO_EDIT
