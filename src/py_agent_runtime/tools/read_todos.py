from __future__ import annotations

from typing import Any, Mapping

from py_agent_runtime.runtime.config import RuntimeConfig
from py_agent_runtime.tools.base import BaseTool, ToolResult


class ReadTodosTool(BaseTool):
    name = "read_todos"
    description = "Read current runtime todo list state."
    parameters_json_schema = {
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False,
    }

    def validate_params(self, params: Mapping[str, Any]) -> str | None:
        return None

    def execute(self, config: RuntimeConfig, params: Mapping[str, Any]) -> ToolResult:
        todos = [dict(todo) for todo in config.todos]
        text = "Current todos:\n" + (
            "\n".join(f"- [{item.get('status', '?')}] {item.get('description', '')}" for item in todos)
            if todos
            else "(empty)"
        )
        return ToolResult(llm_content=text, return_display={"todos": todos})
