from __future__ import annotations

import subprocess
from typing import Any, Mapping

from py_agent_runtime.runtime.config import RuntimeConfig
from py_agent_runtime.tools.base import BaseTool, ToolResult
from py_agent_runtime.tools.path_utils import resolve_path_under_target


class RunShellCommandTool(BaseTool):
    name = "run_shell_command"
    description = "Run a shell command in a constrained working directory."
    parameters_json_schema = {
        "type": "object",
        "properties": {
            "command": {"type": "string"},
            "cwd": {"type": "string", "default": "."},
            "timeout_seconds": {"type": "integer", "minimum": 1, "default": 120},
        },
        "required": ["command"],
        "additionalProperties": False,
    }

    def validate_params(self, params: Mapping[str, Any]) -> str | None:
        command = params.get("command")
        if not isinstance(command, str) or not command.strip():
            return "`command` must be a non-empty string."

        cwd = params.get("cwd", ".")
        if not isinstance(cwd, str) or not cwd.strip():
            return "`cwd` must be a non-empty string."

        timeout_seconds = params.get("timeout_seconds", 120)
        if not isinstance(timeout_seconds, int) or timeout_seconds <= 0:
            return "`timeout_seconds` must be a positive integer."
        return None

    def execute(self, config: RuntimeConfig, params: Mapping[str, Any]) -> ToolResult:
        validation_error = self.validate_params(params)
        if validation_error:
            return ToolResult(llm_content=validation_error, return_display="Error", error=validation_error)

        command = str(params["command"])
        cwd_value = str(params.get("cwd", "."))
        timeout_seconds = int(params.get("timeout_seconds", 120))

        cwd, cwd_error = resolve_path_under_target(config.target_dir, cwd_value)
        if cwd_error or cwd is None:
            error = cwd_error or "Invalid working directory."
            return ToolResult(llm_content=error, return_display="Error", error=error)

        try:
            completed = subprocess.run(
                command,
                cwd=str(cwd),
                shell=True,
                text=True,
                capture_output=True,
                timeout=timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout if isinstance(exc.stdout, str) else ""
            stderr = exc.stderr if isinstance(exc.stderr, str) else ""
            error = f"Command timed out after {timeout_seconds} second(s)."
            return ToolResult(
                llm_content=error,
                return_display={
                    "command": command,
                    "cwd": str(cwd),
                    "timed_out": True,
                    "stdout": stdout,
                    "stderr": stderr,
                    "exit_code": None,
                },
                error=error,
            )
        except Exception as exc:  # pragma: no cover
            error = f"Failed to run command: {exc}"
            return ToolResult(llm_content=error, return_display="Error", error=error)

        payload = {
            "command": command,
            "cwd": str(cwd),
            "timed_out": False,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "exit_code": completed.returncode,
        }
        if completed.returncode != 0:
            error = f"Command failed with exit code {completed.returncode}."
            return ToolResult(llm_content=error, return_display=payload, error=error)

        return ToolResult(
            llm_content=f"Command completed successfully (exit code {completed.returncode}).",
            return_display=payload,
        )
