"""File editor path resolution and cursor positioning."""

from __future__ import annotations

from pathlib import Path

from docs_dev.models import Finding
from docs_dev.tui.file_editor import (
    line_column_for_finding,
    load_file_text,
    resolve_doc_path,
)


def test_resolve_doc_path_relative(tmp_path: Path) -> None:
    doc = tmp_path / "docs" / "foo.md"
    doc.parent.mkdir(parents=True)
    doc.write_text("hello", encoding="utf-8")
    assert resolve_doc_path(tmp_path, "docs/foo.md") == doc.resolve()


def test_line_column_for_finding_one_based() -> None:
    f = Finding(
        tool="vale",
        path="docs/x.md",
        line=23,
        column=5,
        severity="error",
        message="x",
    )
    assert line_column_for_finding(f) == (22, 4)


def test_line_column_clamps_to_file_length() -> None:
    f = Finding(
        tool="vale",
        path="docs/x.md",
        line=99,
        column=1,
        severity="error",
        message="x",
    )
    assert line_column_for_finding(f, line_count=10) == (9, 0)


def test_load_file_text(tmp_path: Path) -> None:
    p = tmp_path / "a.md"
    p.write_text("# Title\n", encoding="utf-8")
    assert "Title" in load_file_text(p)
