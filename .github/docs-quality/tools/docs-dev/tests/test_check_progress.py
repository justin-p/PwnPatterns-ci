"""Progress callback wiring for run_check."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from docs_dev.context import RepoContext
from docs_dev.models import StepResult, StepStatus
from docs_dev.runners.check import CheckOptions, run_check


def test_run_check_emits_progress_messages(tmp_path, monkeypatch) -> None:
    repo = tmp_path
    (repo / "docs").mkdir()
    (repo / "docs" / "sample.md").write_text("# Hi\n", encoding="utf-8")
    dq = repo / ".github" / "docs-quality"
    (dq / "config").mkdir(parents=True)
    manifest_src = Path(__file__).resolve().parents[3] / "config" / "manifest.env"
    if manifest_src.is_file():
        (dq / "config" / "manifest.env").write_text(
            manifest_src.read_text(encoding="utf-8"),
            encoding="utf-8",
        )

    install = tmp_path / "linters"
    install.mkdir()
    (install / "vale").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    (install / "vale").chmod(0o755)

    monkeypatch.setenv("REPO_ROOT", str(repo))
    monkeypatch.setenv("DOCS_QUALITY_DIR", str(dq))
    monkeypatch.setenv("DOC_LINT_INSTALL_DIR", str(install))

    ctx = RepoContext.from_env()
    messages: list[str] = []
    ok = StepResult(name="ok", status=StepStatus.PASS)

    with (
        patch("docs_dev.runners.check._setup_job", return_value=0),
        patch("docs_dev.runners.check._parallel_prose_lint", return_value=ok),
        patch("docs_dev.runners.check._run_prek", return_value=ok),
        patch("docs_dev.runners.check._run_metadata", return_value=ok),
        patch("docs_dev.runners.check._run_shell", return_value=ok),
        patch("docs_dev.runners.check.parse_all_lint_logs", return_value=[]),
        patch("docs_dev.runners.check._prose_failed", return_value=False),
    ):
        run_check(
            ctx,
            CheckOptions(skip_lychee=True, skip_actionlint=True),
            on_progress=messages.append,
        )

    assert any("Found" in m and "markdown" in m for m in messages)
    assert any("Collecting findings" in m for m in messages)
