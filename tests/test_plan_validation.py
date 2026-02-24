from pathlib import Path

from py_agent_runtime.plans.validation import validate_plan_content, validate_plan_path


def test_valid_plan_path_and_content(tmp_path: Path) -> None:
    plans_dir = tmp_path / "plans"
    plans_dir.mkdir()
    plan_file = plans_dir / "ok.md"
    plan_file.write_text("# plan", encoding="utf-8")

    assert validate_plan_path("plans/ok.md", plans_dir, tmp_path) is None
    assert validate_plan_content(plan_file) is None


def test_plan_path_traversal_rejected(tmp_path: Path) -> None:
    plans_dir = tmp_path / "plans"
    plans_dir.mkdir()
    assert validate_plan_path("../secret.md", plans_dir, tmp_path) is not None


def test_symlink_escape_rejected(tmp_path: Path) -> None:
    plans_dir = tmp_path / "plans"
    plans_dir.mkdir()
    outside_file = tmp_path / "outside.md"
    outside_file.write_text("# secret", encoding="utf-8")
    (plans_dir / "link.md").symlink_to(outside_file)

    result = validate_plan_path("plans/link.md", plans_dir, tmp_path)
    assert result is not None
    assert "Access denied" in result


def test_empty_plan_content_rejected(tmp_path: Path) -> None:
    plan = tmp_path / "empty.md"
    plan.write_text("   ", encoding="utf-8")
    result = validate_plan_content(plan)
    assert result is not None
    assert "empty" in result.lower()

