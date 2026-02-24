from __future__ import annotations

from typing import Any, Mapping

from py_agent_runtime.runtime.config import RuntimeConfig
from py_agent_runtime.tools.base import BaseTool, ToolResult
from py_agent_runtime.tools.path_utils import resolve_path_under_target


class ReadFileTool(BaseTool):
    name = "read_file"
    description = "Read UTF-8 file content under the target directory."

    def validate_params(self, params: Mapping[str, Any]) -> str | None:
        file_path = params.get("file_path")
        if not isinstance(file_path, str) or not file_path.strip():
            return "`file_path` must be a non-empty string."
        return None

    def execute(self, config: RuntimeConfig, params: Mapping[str, Any]) -> ToolResult:
        validation_error = self.validate_params(params)
        if validation_error:
            return ToolResult(llm_content=validation_error, return_display="Error", error=validation_error)

        file_path = str(params["file_path"])
        resolved, path_error = resolve_path_under_target(config.target_dir, file_path)
        if path_error or resolved is None:
            error = path_error or "Invalid file path."
            return ToolResult(llm_content=error, return_display="Error", error=error)

        if not resolved.exists() or not resolved.is_file():
            error = f"File does not exist: {file_path}"
            return ToolResult(llm_content=error, return_display="Error", error=error)

        try:
            content = resolved.read_text(encoding="utf-8")
        except Exception as exc:  # pragma: no cover
            error = f"Failed to read file: {exc}"
            return ToolResult(llm_content=error, return_display="Error", error=error)

        return ToolResult(
            llm_content=content,
            return_display={"file_path": str(resolved), "content": content},
        )
