from __future__ import annotations

from typing import Any, Mapping

from py_agent_runtime.runtime.config import RuntimeConfig
from py_agent_runtime.tools.base import BaseTool, ToolResult
from py_agent_runtime.tools.path_utils import resolve_path_under_target


class ReplaceTool(BaseTool):
    name = "replace"
    description = "Replace text in a UTF-8 file under the target directory."
    parameters_json_schema = {
        "type": "object",
        "properties": {
            "file_path": {"type": "string"},
            "old_text": {"type": "string"},
            "new_text": {"type": "string"},
            "replace_all": {"type": "boolean", "default": True},
        },
        "required": ["file_path", "old_text", "new_text"],
        "additionalProperties": False,
    }

    def validate_params(self, params: Mapping[str, Any]) -> str | None:
        file_path = params.get("file_path")
        old_text = params.get("old_text")
        new_text = params.get("new_text")
        if not isinstance(file_path, str) or not file_path.strip():
            return "`file_path` must be a non-empty string."
        if not isinstance(old_text, str) or old_text == "":
            return "`old_text` must be a non-empty string."
        if not isinstance(new_text, str):
            return "`new_text` must be a string."
        replace_all = params.get("replace_all", True)
        if not isinstance(replace_all, bool):
            return "`replace_all` must be a boolean."
        return None

    def execute(self, config: RuntimeConfig, params: Mapping[str, Any]) -> ToolResult:
        validation_error = self.validate_params(params)
        if validation_error:
            return ToolResult(llm_content=validation_error, return_display="Error", error=validation_error)

        file_path = str(params["file_path"])
        old_text = str(params["old_text"])
        new_text = str(params["new_text"])
        replace_all = bool(params.get("replace_all", True))

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

        if old_text not in content:
            error = f"Target text not found in file: {file_path}"
            return ToolResult(llm_content=error, return_display="Error", error=error)

        if replace_all:
            updated = content.replace(old_text, new_text)
            replaced_count = content.count(old_text)
        else:
            updated = content.replace(old_text, new_text, 1)
            replaced_count = 1

        try:
            resolved.write_text(updated, encoding="utf-8")
        except Exception as exc:  # pragma: no cover
            error = f"Failed to write file: {exc}"
            return ToolResult(llm_content=error, return_display="Error", error=error)

        return ToolResult(
            llm_content=f"Updated file: {resolved}",
            return_display={"file_path": str(resolved), "replaced_count": replaced_count},
        )
