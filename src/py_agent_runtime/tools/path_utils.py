from __future__ import annotations

from pathlib import Path


def resolve_path_under_target(target_dir: Path, user_path: str) -> tuple[Path | None, str | None]:
    resolved = (target_dir / user_path).resolve(strict=False)
    target = target_dir.resolve(strict=False)
    try:
        resolved.relative_to(target)
    except ValueError:
        return None, "Access denied: path must be within the target directory."
    return resolved, None
