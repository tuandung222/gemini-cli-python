from __future__ import annotations

import re
from typing import Any, Mapping

from py_agent_runtime.runtime.config import RuntimeConfig
from py_agent_runtime.tools.base import BaseTool, ToolResult
from py_agent_runtime.tools.path_utils import resolve_path_under_target


class GrepSearchTool(BaseTool):
    name = "grep_search"
    description = "Search text in files under the target directory."

    def validate_params(self, params: Mapping[str, Any]) -> str | None:
        query = params.get("query")
        if not isinstance(query, str) or not query.strip():
            return "`query` must be a non-empty string."
        path = params.get("path", ".")
        if not isinstance(path, str) or not path.strip():
            return "`path` must be a non-empty string."
        file_pattern = params.get("file_pattern", "**/*")
        if not isinstance(file_pattern, str) or not file_pattern.strip():
            return "`file_pattern` must be a non-empty string."
        max_results = params.get("max_results", 100)
        if not isinstance(max_results, int) or max_results <= 0:
            return "`max_results` must be a positive integer."
        return None

    def execute(self, config: RuntimeConfig, params: Mapping[str, Any]) -> ToolResult:
        validation_error = self.validate_params(params)
        if validation_error:
            return ToolResult(llm_content=validation_error, return_display="Error", error=validation_error)

        query = str(params["query"])
        base_path = str(params.get("path", "."))
        file_pattern = str(params.get("file_pattern", "**/*"))
        max_results = int(params.get("max_results", 100))
        case_sensitive = bool(params.get("case_sensitive", False))
        use_regex = bool(params.get("use_regex", False))

        resolved_base, path_error = resolve_path_under_target(config.target_dir, base_path)
        if path_error or resolved_base is None:
            error = path_error or "Invalid base path."
            return ToolResult(llm_content=error, return_display="Error", error=error)

        if not resolved_base.exists() or not resolved_base.is_dir():
            error = f"Directory does not exist: {base_path}"
            return ToolResult(llm_content=error, return_display="Error", error=error)

        flags = 0 if case_sensitive else re.IGNORECASE
        try:
            pattern = re.compile(query if use_regex else re.escape(query), flags=flags)
        except re.error as exc:
            error = f"Invalid regex query: {exc}"
            return ToolResult(llm_content=error, return_display="Error", error=error)

        matches: list[dict[str, Any]] = []
        for path in sorted(resolved_base.glob(file_pattern)):
            if len(matches) >= max_results:
                break
            if not path.is_file():
                continue

            resolved_file = path.resolve(strict=False)
            try:
                rel = resolved_file.relative_to(config.target_dir.resolve(strict=False))
            except ValueError:
                continue

            try:
                text = resolved_file.read_text(encoding="utf-8")
            except Exception:
                continue

            for line_no, line in enumerate(text.splitlines(), start=1):
                if pattern.search(line) is None:
                    continue
                matches.append(
                    {
                        "file_path": rel.as_posix(),
                        "line_number": line_no,
                        "line": line,
                    }
                )
                if len(matches) >= max_results:
                    break

        lines = [
            f"- {item['file_path']}:{item['line_number']}: {item['line']}"
            for item in matches
        ]
        text = "\n".join(lines) if lines else "(no matches)"
        return ToolResult(
            llm_content=f"Search results for `{query}`:\n{text}",
            return_display={
                "query": query,
                "path": str(resolved_base),
                "matches": matches,
                "max_results": max_results,
            },
        )
