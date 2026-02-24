from __future__ import annotations

import sys

from py_agent_runtime.cli import main as cli_main
from py_agent_runtime.llm.types import LLMTurnResponse


class FakeProvider:
    def __init__(self, model: str = "gpt-4.1-mini") -> None:
        self.model = model

    def generate(self, messages, tools=None, *, model=None, temperature=None):  # noqa: ANN001, ANN201
        return LLMTurnResponse(content="pong", tool_calls=[], finish_reason="stop")


def test_cli_chat_command(monkeypatch, capsys) -> None:  # noqa: ANN001
    monkeypatch.setattr(cli_main, "OpenAIChatProvider", FakeProvider)
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

