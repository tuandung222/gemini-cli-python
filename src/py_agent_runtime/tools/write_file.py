from __future__ import annotations

from typing import Any, Mapping

from py_agent_runtime.runtime.config import RuntimeConfig
from py_agent_runtime.tools.base import BaseTool, ToolResult
from py_agent_runtime.tools.path_utils import resolve_path_under_target


class WriteFileTool(BaseTool):
    name = "write_file"
    description = "Write UTF-8 content to a file under the target directory."

    def validate_params(self, params: Mapping[str, Any]) -> str | None:
        file_path = params.get("file_path")
        content = params.get("content")
        if not isinstance(file_path, str) or not file_path.strip():
            return "`file_path` must be a non-empty string."
        if not isinstance(content, str):
            return "`content` must be a string."
        return None

    def execute(self, config: RuntimeConfig, params: Mapping[str, Any]) -> ToolResult:
        validation_error = self.validate_params(params)
        if validation_error:
            return ToolResult(llm_content=validation_error, return_display="Error", error=validation_error)

        file_path = str(params["file_path"])
        content = str(params["content"])
        resolved, path_error = resolve_path_under_target(config.target_dir, file_path)
        if path_error or resolved is None:
            error = path_error or "Invalid file path."
            return ToolResult(llm_content=error, return_display="Error", error=error)

        try:
            resolved.parent.mkdir(parents=True, exist_ok=True)
            resolved.write_text(content, encoding="utf-8")
        except Exception as exc:  # pragma: no cover
            error = f"Failed to write file: {exc}"
            return ToolResult(llm_content=error, return_display="Error", error=error)

        message = f"Wrote file: {resolved}"
        return ToolResult(
            llm_content=message,
            return_display={"file_path": str(resolved), "bytes_written": len(content.encode('utf-8'))},
        )
