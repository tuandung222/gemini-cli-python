from __future__ import annotations

import sys
from pathlib import Path

from py_agent_runtime.runtime.config import RuntimeConfig
from py_agent_runtime.tools.run_shell_command import RunShellCommandTool


def test_run_shell_command_success(tmp_path: Path) -> None:
    config = RuntimeConfig(target_dir=tmp_path)
    tool = RunShellCommandTool()

    command = f'"{sys.executable}" -c "print(\'hello\')"'
    result = tool.execute(config, {"command": command})

    assert result.error is None
    payload = result.return_display
    assert isinstance(payload, dict)
    assert payload["exit_code"] == 0
    assert "hello" in payload["stdout"]


def test_run_shell_command_non_zero_exit_is_error(tmp_path: Path) -> None:
    config = RuntimeConfig(target_dir=tmp_path)
    tool = RunShellCommandTool()

    command = f'"{sys.executable}" -c "import sys; sys.exit(3)"'
    result = tool.execute(config, {"command": command})

    assert result.error is not None
    assert "exit code 3" in result.error.lower()
    payload = result.return_display
    assert isinstance(payload, dict)
    assert payload["exit_code"] == 3


def test_run_shell_command_timeout(tmp_path: Path) -> None:
    config = RuntimeConfig(target_dir=tmp_path)
    tool = RunShellCommandTool()

    command = f'"{sys.executable}" -c "import time; time.sleep(2)"'
    result = tool.execute(config, {"command": command, "timeout_seconds": 1})

    assert result.error is not None
    assert "timed out" in result.error.lower()
    payload = result.return_display
    assert isinstance(payload, dict)
    assert payload["timed_out"] is True


def test_run_shell_command_denies_cwd_escape(tmp_path: Path) -> None:
    config = RuntimeConfig(target_dir=tmp_path)
    tool = RunShellCommandTool()
    result = tool.execute(
        config,
        {
            "command": f'"{sys.executable}" -c "print(1)"',
            "cwd": "../",
        },
    )
    assert result.error is not None
    assert "access denied" in result.error.lower()
