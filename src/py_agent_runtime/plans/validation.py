from __future__ import annotations

from pathlib import Path


class PlanErrorMessages:
    PATH_ACCESS_DENIED = "Access denied: plan path must be within the designated plans directory."
    FILE_EMPTY = "Plan file is empty. You must write content before requesting approval."

    @staticmethod
    def file_not_found(path: str) -> str:
        return f"Plan file does not exist: {path}."

    @staticmethod
    def read_failure(detail: str) -> str:
        return f"Failed to read plan file: {detail}"


def _is_subpath(parent: Path, child: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def validate_plan_path(plan_path: str, plans_dir: Path, target_dir: Path) -> str | None:
    resolved_path = (target_dir / plan_path).resolve(strict=False)
    real_path = resolved_path.resolve(strict=False)
    real_plans_dir = plans_dir.resolve(strict=False)

    if not _is_subpath(real_plans_dir, real_path):
        return PlanErrorMessages.PATH_ACCESS_DENIED

    if not resolved_path.exists() or not resolved_path.is_file():
        return PlanErrorMessages.file_not_found(plan_path)

    return None


def validate_plan_content(plan_path: Path) -> str | None:
    try:
        if not plan_path.exists():
            return PlanErrorMessages.FILE_EMPTY
        content = plan_path.read_text(encoding="utf-8")
        if not content.strip():
            return PlanErrorMessages.FILE_EMPTY
        return None
    except Exception as exc:  # pragma: no cover
        return PlanErrorMessages.read_failure(str(exc))

