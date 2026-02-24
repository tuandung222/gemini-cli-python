from __future__ import annotations

from pathlib import Path

from py_agent_runtime.runtime.config import RuntimeConfig
from py_agent_runtime.tools.glob_search import GlobSearchTool
from py_agent_runtime.tools.grep_search import GrepSearchTool
from py_agent_runtime.tools.list_directory import ListDirectoryTool
from py_agent_runtime.tools.read_file import ReadFileTool
from py_agent_runtime.tools.replace import ReplaceTool
from py_agent_runtime.tools.write_file import WriteFileTool


def test_list_directory_tool_lists_entries(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("x", encoding="utf-8")
    (tmp_path / "dir").mkdir()
    config = RuntimeConfig(target_dir=tmp_path)
    tool = ListDirectoryTool()

    result = tool.execute(config, {"path": "."})

    assert result.error is None
    payload = result.return_display
    assert isinstance(payload, dict)
    names = [entry["name"] for entry in payload["entries"]]
    assert "a.txt" in names
    assert "dir" in names


def test_list_directory_tool_denies_path_escape(tmp_path: Path) -> None:
    config = RuntimeConfig(target_dir=tmp_path)
    tool = ListDirectoryTool()

    result = tool.execute(config, {"path": "../"})

    assert result.error is not None
    assert "Access denied" in result.error


def test_read_file_tool_reads_text(tmp_path: Path) -> None:
    file_path = tmp_path / "notes.txt"
    file_path.write_text("hello", encoding="utf-8")
    config = RuntimeConfig(target_dir=tmp_path)
    tool = ReadFileTool()

    result = tool.execute(config, {"file_path": "notes.txt"})

    assert result.error is None
    assert result.return_display == {"file_path": str(file_path.resolve()), "content": "hello"}


def test_write_and_replace_tools(tmp_path: Path) -> None:
    config = RuntimeConfig(target_dir=tmp_path)
    write_tool = WriteFileTool()
    replace_tool = ReplaceTool()

    write_result = write_tool.execute(
        config,
        {"file_path": "doc.txt", "content": "hello world\nhello world\n"},
    )
    assert write_result.error is None

    replace_result = replace_tool.execute(
        config,
        {
            "file_path": "doc.txt",
            "old_text": "hello",
            "new_text": "hi",
            "replace_all": False,
        },
    )
    assert replace_result.error is None
    updated = (tmp_path / "doc.txt").read_text(encoding="utf-8")
    assert updated == "hi world\nhello world\n"


def test_replace_tool_errors_when_old_text_missing(tmp_path: Path) -> None:
    file_path = tmp_path / "doc.txt"
    file_path.write_text("abc", encoding="utf-8")
    config = RuntimeConfig(target_dir=tmp_path)
    tool = ReplaceTool()

    result = tool.execute(
        config,
        {"file_path": "doc.txt", "old_text": "zzz", "new_text": "x"},
    )
    assert result.error is not None
    assert "not found" in result.error


def test_glob_tool_finds_matching_files(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("print(1)\n", encoding="utf-8")
    (tmp_path / "b.txt").write_text("x\n", encoding="utf-8")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "c.py").write_text("print(2)\n", encoding="utf-8")

    config = RuntimeConfig(target_dir=tmp_path)
    tool = GlobSearchTool()
    result = tool.execute(config, {"pattern": "**/*.py"})

    assert result.error is None
    payload = result.return_display
    assert isinstance(payload, dict)
    matches = payload["matches"]
    assert "a.py" in matches
    assert "sub/c.py" in matches


def test_grep_tool_returns_line_hits(tmp_path: Path) -> None:
    source = tmp_path / "app.py"
    source.write_text("alpha\nneedle line\nomega\n", encoding="utf-8")
    config = RuntimeConfig(target_dir=tmp_path)
    tool = GrepSearchTool()

    result = tool.execute(
        config,
        {"query": "needle", "path": ".", "file_pattern": "*.py", "max_results": 5},
    )

    assert result.error is None
    payload = result.return_display
    assert isinstance(payload, dict)
    hits = payload["matches"]
    assert len(hits) == 1
    assert hits[0]["file_path"] == "app.py"
    assert hits[0]["line_number"] == 2
