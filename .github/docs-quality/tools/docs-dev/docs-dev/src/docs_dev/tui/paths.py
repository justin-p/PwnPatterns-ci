from __future__ import annotations

from pathlib import Path


def display_path(path: str, repo_root: Path | None = None) -> str:
    """Shorten a repo path for table columns; keep full path in detail panel."""
    p = Path(path)
    if repo_root is not None:
        try:
            rel = p.resolve().relative_to(repo_root.resolve())
            text = rel.as_posix()
            if len(text) <= 72:
                return text
            return f"…/{rel.name}"
        except ValueError:
            pass
    name = p.name
    if len(path) <= 72:
        return path
    return f"…/{name}"
