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
    last_kwargs = None

    def __init__(self, config, provider, **kwargs):  # noqa: ANN001, ANN003
        FakeRunner.last_config = config
        FakeRunner.last_kwargs = dict(kwargs)

    def run(self, user_prompt: str, system_prompt: str | None = None) -> AgentRunResult:
        return AgentRunResult(success=True, result="ok", error=None, turns=1)


def test_cli_chat_command(monkeypatch, capsys) -> None:  # noqa: ANN001
    monkeypatch.setattr(
        cli_main,
        "create_provider",
        lambda provider, model, **kwargs: FakeProvider(model),  # noqa: ARG005
    )
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
    monkeypatch.setattr(
        cli_main,
        "create_provider",
        lambda provider, model, **kwargs: FakeProvider(model),  # noqa: ARG005
    )
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


def test_cli_run_command_loads_completion_schema_file(monkeypatch, capsys, tmp_path) -> None:  # noqa: ANN001
    monkeypatch.setattr(
        cli_main,
        "create_provider",
        lambda provider, model, **kwargs: FakeProvider(model),  # noqa: ARG005
    )
    monkeypatch.setattr(cli_main, "LLMAgentRunner", FakeRunner)

    schema_file = tmp_path / "schema.json"
    schema_file.write_text('{"type":"object","required":["summary"]}', encoding="utf-8")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "py-agent-runtime",
            "run",
            "--prompt",
            "Do work",
            "--completion-schema-file",
            str(schema_file),
        ],
    )
    code = cli_main.main()
    _ = capsys.readouterr()
    assert code == 0
    assert FakeRunner.last_kwargs is not None
    assert FakeRunner.last_kwargs.get("completion_schema") == {
        "type": "object",
        "required": ["summary"],
    }


def test_cli_run_command_rejects_invalid_schema_file(monkeypatch, capsys, tmp_path) -> None:  # noqa: ANN001
    monkeypatch.setattr(
        cli_main,
        "create_provider",
        lambda provider, model, **kwargs: FakeProvider(model),  # noqa: ARG005
    )
    monkeypatch.setattr(cli_main, "LLMAgentRunner", FakeRunner)

    schema_file = tmp_path / "schema.json"
    schema_file.write_text("{", encoding="utf-8")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "py-agent-runtime",
            "run",
            "--prompt",
            "Do work",
            "--completion-schema-file",
            str(schema_file),
        ],
    )
    code = cli_main.main()
    captured = capsys.readouterr()
    assert code == 2
    assert "Invalid completion schema JSON file" in captured.out


def test_cli_mode_command_sets_approval_mode(monkeypatch, capsys) -> None:  # noqa: ANN001
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "py-agent-runtime",
            "mode",
            "--approval-mode",
            "yolo",
            "--non-interactive",
        ],
    )
    code = cli_main.main()
    captured = capsys.readouterr()
    assert code == 0

    payload = json.loads(captured.out)
    assert payload["approval_mode"] == "yolo"
    assert payload["interactive"] is False


def test_cli_plan_enter_command_switches_to_plan_mode(monkeypatch, capsys, tmp_path) -> None:  # noqa: ANN001
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "py-agent-runtime",
            "plan",
            "enter",
            "--reason",
            "Draft implementation steps",
        ],
    )
    code = cli_main.main()
    captured = capsys.readouterr()
    assert code == 0

    payload = json.loads(captured.out)
    assert payload["success"] is True
    assert payload["approval_mode"] == "plan"
    assert "Switching to Plan mode" in payload["result_display"]


def test_cli_plan_exit_command_approves_plan(monkeypatch, capsys, tmp_path) -> None:  # noqa: ANN001
    monkeypatch.chdir(tmp_path)
    plan_dir = tmp_path / ".gemini" / "tmp" / "plans"
    plan_dir.mkdir(parents=True, exist_ok=True)
    plan_file = plan_dir / "implementation.md"
    plan_file.write_text("# Plan\n- Build feature\n", encoding="utf-8")

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "py-agent-runtime",
            "plan",
            "exit",
            "--plan-path",
            ".gemini/tmp/plans/implementation.md",
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
    assert payload["approved_plan_path"] == str(plan_file.resolve())


def test_cli_run_command_forwards_retry_settings_to_provider(monkeypatch, capsys) -> None:  # noqa: ANN001
    captured: dict[str, object] = {}

    def _create_provider(provider: str, model: str, **kwargs: object) -> FakeProvider:
        captured["provider"] = provider
        captured["model"] = model
        captured.update(kwargs)
        return FakeProvider(model)

    monkeypatch.setattr(cli_main, "create_provider", _create_provider)
    monkeypatch.setattr(cli_main, "LLMAgentRunner", FakeRunner)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "py-agent-runtime",
            "run",
            "--prompt",
            "Do work",
            "--max-retries",
            "4",
            "--retry-base-delay-seconds",
            "0.2",
            "--retry-max-delay-seconds",
            "1.1",
        ],
    )
    code = cli_main.main()
    _ = capsys.readouterr()

    assert code == 0
    assert captured["provider"] == "openai"
    assert captured["model"] == "gpt-4.1-mini"
    assert captured["max_retries"] == 4
    assert captured["retry_base_delay_seconds"] == 0.2
    assert captured["retry_max_delay_seconds"] == 1.1


def test_cli_run_command_respects_target_dir(monkeypatch, capsys, tmp_path) -> None:  # noqa: ANN001
    monkeypatch.setattr(
        cli_main,
        "create_provider",
        lambda provider, model, **kwargs: FakeProvider(model),  # noqa: ARG005
    )
    monkeypatch.setattr(cli_main, "LLMAgentRunner", FakeRunner)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "py-agent-runtime",
            "run",
            "--prompt",
            "Do work",
            "--target-dir",
            str(tmp_path),
        ],
    )
    code = cli_main.main()
    _ = capsys.readouterr()
    assert code == 0
    assert FakeRunner.last_config is not None
    assert FakeRunner.last_config.target_dir == tmp_path.resolve()


def test_cli_policies_list_command_outputs_grouped_policies(monkeypatch, capsys) -> None:  # noqa: ANN001
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "py-agent-runtime",
            "policies",
            "list",
        ],
    )
    code = cli_main.main()
    captured = capsys.readouterr()
    assert code == 0

    payload = json.loads(captured.out)
    assert payload["success"] is True
    assert "default" in payload["policies"]
    assert "autoEdit" in payload["policies"]
    assert "yolo" in payload["policies"]
    assert "plan" in payload["policies"]

    default_rules = payload["policies"]["default"]
    assert any(rule.get("tool_name") == "read_file" and rule.get("decision") == "allow" for rule in default_rules)


def test_cli_tools_list_command_outputs_registered_tools(monkeypatch, capsys) -> None:  # noqa: ANN001
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "py-agent-runtime",
            "tools",
            "list",
        ],
    )
    code = cli_main.main()
    captured = capsys.readouterr()
    assert code == 0

    payload = json.loads(captured.out)
    assert payload["success"] is True
    tools = payload["tools"]
    names = [item["name"] for item in tools]
    assert "read_file" in names
    assert "write_file" in names
    assert "run_shell_command" in names
