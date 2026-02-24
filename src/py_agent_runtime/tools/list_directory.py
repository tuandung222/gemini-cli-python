from __future__ import annotations

from typing import Any, Mapping

from py_agent_runtime.runtime.config import RuntimeConfig
from py_agent_runtime.tools.base import BaseTool, ToolResult
from py_agent_runtime.tools.path_utils import resolve_path_under_target


class ListDirectoryTool(BaseTool):
    name = "list_directory"
    description = "List files and folders for a path under the target directory."
    parameters_json_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "default": "."},
        },
        "required": [],
        "additionalProperties": False,
    }

    def validate_params(self, params: Mapping[str, Any]) -> str | None:
        path = params.get("path", ".")
        if not isinstance(path, str) or not path.strip():
            return "`path` must be a non-empty string."
        return None

    def execute(self, config: RuntimeConfig, params: Mapping[str, Any]) -> ToolResult:
        validation_error = self.validate_params(params)
        if validation_error:
            return ToolResult(llm_content=validation_error, return_display="Error", error=validation_error)

        path = str(params.get("path", "."))
        resolved, path_error = resolve_path_under_target(config.target_dir, path)
        if path_error or resolved is None:
            error = path_error or "Invalid path."
            return ToolResult(llm_content=error, return_display="Error", error=error)

        if not resolved.exists() or not resolved.is_dir():
            error = f"Directory does not exist: {path}"
            return ToolResult(llm_content=error, return_display="Error", error=error)

        entries = []
        for child in sorted(resolved.iterdir(), key=lambda item: item.name.lower()):
            entries.append(
                {
                    "name": child.name,
                    "path": str(child.relative_to(config.target_dir)),
                    "is_dir": child.is_dir(),
                    "size": child.stat().st_size if child.is_file() else None,
                }
            )

        lines = [f"- {'[DIR]' if item['is_dir'] else '[FILE]'} {item['path']}" for item in entries]
        content = "Directory listing:\n" + ("\n".join(lines) if lines else "(empty)")
        return ToolResult(
            llm_content=content,
            return_display={"path": str(resolved), "entries": entries},
        )
