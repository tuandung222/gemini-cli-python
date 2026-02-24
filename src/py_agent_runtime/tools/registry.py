from __future__ import annotations

from typing import Iterable

from py_agent_runtime.tools.base import BaseTool


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register_tool(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool

    def unregister_tool(self, name: str) -> None:
        self._tools.pop(name, None)

    def get_tool(self, name: str) -> BaseTool | None:
        return self._tools.get(name)

    def get_all_tool_names(self) -> list[str]:
        return sorted(self._tools.keys())

    def get_all_tools(self) -> Iterable[BaseTool]:
        return self._tools.values()

