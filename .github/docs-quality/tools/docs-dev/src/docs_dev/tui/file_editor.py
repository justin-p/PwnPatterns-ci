"""Load repo docs into the check-screen editor and jump to lint line/column."""

from __future__ import annotations

from pathlib import Path

from docs_dev.models import Finding


def resolve_doc_path(repo_root: Path, path: str) -> Path:
    """Return absolute path for a doc path relative to the repo (or pass-through)."""
    p = Path(path)
    if p.is_absolute():
        return p.resolve()
    return (repo_root / p).resolve()


def load_file_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def line_column_for_finding(
    finding: Finding | None,
    *,
    line_count: int | None = None,
) -> tuple[int, int]:
    """0-based (row, column) for TextArea.move_cursor; linters use 1-based positions."""
    if finding is None:
        return (0, 0)
    row = max(0, finding.line - 1)
    if line_count is not None:
        row = min(row, max(0, line_count - 1))
    col = max(0, (finding.column or 1) - 1)
    return (row, col)
