from __future__ import annotations

from typing import Any, Mapping

from py_agent_runtime.runtime.config import RuntimeConfig
from py_agent_runtime.tools.base import BaseTool, ToolResult

TODO_STATUSES = {"pending", "in_progress", "completed", "cancelled"}


class WriteTodosTool(BaseTool):
    name = "write_todos"
    description = "Overwrite the full todo list with validated statuses."

    def validate_params(self, params: Mapping[str, Any]) -> str | None:
        todos = params.get("todos")
        if not isinstance(todos, list):
            return "`todos` parameter must be an array"

        in_progress_count = 0
        for todo in todos:
            if not isinstance(todo, dict):
                return "Each todo item must be an object"
            description = todo.get("description")
            status = todo.get("status")
            if not isinstance(description, str) or not description.strip():
                return "Each todo must have a non-empty description string"
            if status not in TODO_STATUSES:
                return "Each todo must have a valid status (pending, in_progress, completed, cancelled)"
            if status == "in_progress":
                in_progress_count += 1

        if in_progress_count > 1:
            return "Invalid parameters: Only one task can be \"in_progress\" at a time."
        return None

    def execute(self, config: RuntimeConfig, params: Mapping[str, Any]) -> ToolResult:
        validation_error = self.validate_params(params)
        if validation_error:
            return ToolResult(llm_content=validation_error, return_display="Error", error=validation_error)

        todos = params.get("todos", [])
        if not todos:
            text = "Successfully cleared the todo list."
            return ToolResult(llm_content=text, return_display={"todos": []})

        lines = []
        for idx, todo in enumerate(todos, start=1):
            lines.append(f"{idx}. [{todo['status']}] {todo['description']}")
        text = "Successfully updated the todo list. The current list is now:\n" + "\n".join(lines)
        return ToolResult(llm_content=text, return_display={"todos": todos})
