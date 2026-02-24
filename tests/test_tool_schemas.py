from __future__ import annotations

from py_agent_runtime.llm.normalizer import build_openai_tool_schemas
from py_agent_runtime.tools.enter_plan_mode import EnterPlanModeTool
from py_agent_runtime.tools.exit_plan_mode import ExitPlanModeTool
from py_agent_runtime.tools.glob_search import GlobSearchTool
from py_agent_runtime.tools.grep_search import GrepSearchTool
from py_agent_runtime.tools.list_directory import ListDirectoryTool
from py_agent_runtime.tools.read_file import ReadFileTool
from py_agent_runtime.tools.read_todos import ReadTodosTool
from py_agent_runtime.tools.replace import ReplaceTool
from py_agent_runtime.tools.run_shell_command import RunShellCommandTool
from py_agent_runtime.tools.write_file import WriteFileTool
from py_agent_runtime.tools.write_todos import WriteTodosTool


def test_built_in_tools_expose_non_default_parameter_schemas() -> None:
    tools = [
        EnterPlanModeTool(),
        ExitPlanModeTool(),
        GlobSearchTool(),
        GrepSearchTool(),
        ListDirectoryTool(),
        ReadFileTool(),
        ReadTodosTool(),
        ReplaceTool(),
        RunShellCommandTool(),
        WriteFileTool(),
        WriteTodosTool(),
    ]

    schemas = build_openai_tool_schemas(tools)
    by_name = {schema["function"]["name"]: schema["function"]["parameters"] for schema in schemas}

    assert by_name["read_file"]["required"] == ["file_path"]
    assert by_name["write_file"]["required"] == ["file_path", "content"]
    assert by_name["replace"]["required"] == ["file_path", "old_text", "new_text"]
    assert by_name["run_shell_command"]["required"] == ["command"]
    assert by_name["write_todos"]["required"] == ["todos"]
    assert by_name["read_todos"]["type"] == "object"
