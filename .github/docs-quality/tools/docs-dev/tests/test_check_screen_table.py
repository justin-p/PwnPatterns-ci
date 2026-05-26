"""Check screen table helpers and rescan cursor behavior."""

from __future__ import annotations

from docs_dev.models import FileFindings, Finding
from docs_dev.tui.screens.check_screen import file_list_row_index


def _ff(path: str) -> FileFindings:
    return FileFindings(
        path=path,
        findings=[
            Finding(
                tool="vale",
                path=path,
                line=1,
                column=1,
                severity="error",
                message="test",
            )
        ],
    )


def test_file_list_row_index_finds_path_after_sort() -> None:
    files = [
        _ff("docs/z-last.md"),
        _ff("docs/a-first.md"),
        _ff("docs/m-middle.md"),
    ]
    files.sort(key=lambda ff: (-ff.count, ff.path))

    assert file_list_row_index(files, "docs/a-first.md") == 0
    assert file_list_row_index(files, "docs/m-middle.md") == 1
    assert file_list_row_index(files, "docs/z-last.md") == 2
    assert file_list_row_index(files, "docs/missing.md") is None
