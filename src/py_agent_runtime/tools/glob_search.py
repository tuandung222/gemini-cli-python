from __future__ import annotations

from typing import Any, Mapping

from py_agent_runtime.runtime.config import RuntimeConfig
from py_agent_runtime.tools.base import BaseTool, ToolResult
from py_agent_runtime.tools.path_utils import resolve_path_under_target


class GlobSearchTool(BaseTool):
    name = "glob"
    description = "Find files with a glob pattern under the target directory."

    def validate_params(self, params: Mapping[str, Any]) -> str | None:
        pattern = params.get("pattern")
        if not isinstance(pattern, str) or not pattern.strip():
            return "`pattern` must be a non-empty string."
        path = params.get("path", ".")
        if not isinstance(path, str) or not path.strip():
            return "`path` must be a non-empty string."
        return None

    def execute(self, config: RuntimeConfig, params: Mapping[str, Any]) -> ToolResult:
        validation_error = self.validate_params(params)
        if validation_error:
            return ToolResult(llm_content=validation_error, return_display="Error", error=validation_error)

        pattern = str(params["pattern"])
        base_path = str(params.get("path", "."))
        resolved_base, path_error = resolve_path_under_target(config.target_dir, base_path)
        if path_error or resolved_base is None:
            error = path_error or "Invalid base path."
            return ToolResult(llm_content=error, return_display="Error", error=error)

        if not resolved_base.exists() or not resolved_base.is_dir():
            error = f"Directory does not exist: {base_path}"
            return ToolResult(llm_content=error, return_display="Error", error=error)

        matches: list[str] = []
        for item in sorted(resolved_base.glob(pattern)):
            if not item.exists():
                continue
            try:
                rel = item.resolve(strict=False).relative_to(config.target_dir.resolve(strict=False))
            except ValueError:
                continue
            matches.append(rel.as_posix())

        lines = "\n".join(f"- {path}" for path in matches) if matches else "(no matches)"
        return ToolResult(
            llm_content=f"Glob matches for pattern `{pattern}`:\n{lines}",
            return_display={"base_path": str(resolved_base), "pattern": pattern, "matches": matches},
        )
