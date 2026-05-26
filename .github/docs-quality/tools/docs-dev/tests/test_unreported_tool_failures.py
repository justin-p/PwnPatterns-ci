"""Synthetic findings when linters exit non-zero without parseable JSON."""

from __future__ import annotations

from pathlib import Path

from docs_dev.context import RepoContext
from docs_dev.models import CheckReport, StepResult, StepStatus
from docs_dev.runners.check import _findings_for_unreported_tool_failures


def test_rumdl_exit_without_json_yields_finding(tmp_path, monkeypatch) -> None:
    repo = tmp_path
    (repo / "docs").mkdir()
    sample = "docs/sample.md"
    (repo / sample).write_text("# Hi\n", encoding="utf-8")
    dq = repo / ".github" / "docs-quality"
    (dq / "config").mkdir(parents=True)
    manifest_src = Path(__file__).resolve().parents[3] / "config" / "manifest.env"
    if manifest_src.is_file():
        (dq / "config" / "manifest.env").write_text(
            manifest_src.read_text(encoding="utf-8"),
            encoding="utf-8",
        )

    lint_dir = repo / ".lint-logs"
    lint_dir.mkdir()
    (lint_dir / "rumdl.exit").write_text("1\n", encoding="utf-8")
    (lint_dir / "rumdl.stderr").write_text("rumdl: invalid config\n", encoding="utf-8")
    (lint_dir / "rumdl.json").write_text("[]", encoding="utf-8")

    monkeypatch.setenv("REPO_ROOT", str(repo))
    monkeypatch.setenv("DOCS_QUALITY_DIR", str(dq))
    monkeypatch.setenv("DOC_LINT_INSTALL_DIR", str(repo / "linters"))

    ctx = RepoContext.from_env()
    ctx.lint_log_dir = lint_dir

    extra = _findings_for_unreported_tool_failures(ctx, [sample], [])
    assert len(extra) == 1
    assert extra[0].tool == "rumdl"
    assert "exited 1" in extra[0].message


def test_lychee_filter_success_log_does_not_yield_finding(tmp_path, monkeypatch) -> None:
    repo = tmp_path
    (repo / "docs").mkdir()
    sample = "docs/page.md"
    (repo / sample).write_text("# Hi\n", encoding="utf-8")
    dq = repo / ".github" / "docs-quality"
    (dq / "config").mkdir(parents=True)
    manifest_src = Path(__file__).resolve().parents[3] / "config" / "manifest.env"
    if manifest_src.is_file():
        (dq / "config" / "manifest.env").write_text(
            manifest_src.read_text(encoding="utf-8"),
            encoding="utf-8",
        )

    lint_dir = repo / ".lint-logs"
    lint_dir.mkdir()
    (lint_dir / "lychee-filter.exit").write_text("0\n", encoding="utf-8")
    (lint_dir / "lychee.log").write_text(
        "Filtered datacenter 403: suppressed=1, remaining errors=0\n",
        encoding="utf-8",
    )

    monkeypatch.setenv("REPO_ROOT", str(repo))
    monkeypatch.setenv("DOCS_QUALITY_DIR", str(dq))
    monkeypatch.setenv("DOC_LINT_INSTALL_DIR", str(repo / "linters"))

    ctx = RepoContext.from_env()
    ctx.lint_log_dir = lint_dir

    extra = _findings_for_unreported_tool_failures(ctx, [sample], [])
    assert extra == []


def test_failure_summary_lists_failed_steps() -> None:
    report = CheckReport(
        steps=[
            StepResult(name="prose lint", status=StepStatus.FAIL),
            StepResult(
                name="lychee",
                status=StepStatus.FAIL,
                detail="3 broken link(s)",
            ),
        ]
    )
    assert report.passed is False
    assert report.failure_summary() == "prose lint, lychee (3 broken link(s))"
