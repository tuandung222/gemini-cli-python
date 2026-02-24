from __future__ import annotations

from pathlib import Path

from py_agent_runtime.runtime.config import RuntimeConfig
from py_agent_runtime.tools.read_todos import ReadTodosTool
from py_agent_runtime.tools.write_todos import WriteTodosTool


def test_write_todos_persists_to_runtime_and_read_todos_returns_state(tmp_path: Path) -> None:
    config = RuntimeConfig(target_dir=tmp_path)
    write_tool = WriteTodosTool()
    read_tool = ReadTodosTool()

    write_result = write_tool.execute(
        config,
        {
            "todos": [
                {"description": "task A", "status": "in_progress"},
                {"description": "task B", "status": "pending"},
            ]
        },
    )
    assert write_result.error is None

    read_result = read_tool.execute(config, {})
    assert read_result.error is None
    payload = read_result.return_display
    assert isinstance(payload, dict)
    assert payload["todos"] == [
        {"description": "task A", "status": "in_progress"},
        {"description": "task B", "status": "pending"},
    ]


def test_write_todos_empty_clears_runtime_state(tmp_path: Path) -> None:
    config = RuntimeConfig(target_dir=tmp_path)
    write_tool = WriteTodosTool()
    read_tool = ReadTodosTool()

    _ = write_tool.execute(
        config,
        {"todos": [{"description": "task A", "status": "pending"}]},
    )
    clear_result = write_tool.execute(config, {"todos": []})
    assert clear_result.error is None

    read_result = read_tool.execute(config, {})
    assert read_result.error is None
    payload = read_result.return_display
    assert isinstance(payload, dict)
    assert payload["todos"] == []
