from __future__ import annotations

import os
from pathlib import Path

import pytest

from docs_dev.models import CheckReport, StepResult, StepStatus


@pytest.fixture(scope="session", autouse=True)
def _docs_dev_test_repo_env() -> None:
    """Pin REPO_ROOT/DOCS_QUALITY_DIR for the whole run (TUI e2e opens CheckScreen without repo_root fixture)."""
    root = Path(__file__).resolve().parents[5]
    docs_quality = root / ".github" / "docs-quality"
    os.environ["REPO_ROOT"] = str(root)
    os.environ["DOCS_QUALITY_DIR"] = str(docs_quality)


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return Path(os.environ["REPO_ROOT"])


@pytest.fixture(autouse=True)
def _mock_heavy_runners(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep TUI e2e tests offline and fast."""

    def _noop_setup(ctx, **kwargs):
        if on_line := kwargs.get("on_line"):
            on_line("setup (mock)")
        return 0

    def _noop_line(on_line):
        on_line("ok (mock)")
        return 0

    monkeypatch.setattr(
        "docs_dev.tui.screens.home.setup.run_setup",
        _noop_setup,
    )
    monkeypatch.setattr(
        "docs_dev.tui.screens.tools_screen.doctor.run_doctor",
        lambda ctx: (True, []),
    )
    monkeypatch.setattr(
        "docs_dev.tui.screens.tools_screen.maintenance.run_sync",
        lambda ctx, on_line: _noop_line(on_line),
    )
    monkeypatch.setattr(
        "docs_dev.tui.screens.tools_screen.maintenance.run_vale_sync",
        lambda ctx, on_line: _noop_line(on_line),
    )
    monkeypatch.setattr(
        "docs_dev.tui.screens.tools_screen.maintenance.run_checksums",
        lambda ctx, on_line: _noop_line(on_line),
    )
    def _mock_e2e(ctx, extra, *, on_line=None):
        if on_line:
            on_line("e2e (mock)")
        return 0

    monkeypatch.setattr(
        "docs_dev.tui.screens.tools_screen.e2e.run_e2e",
        _mock_e2e,
    )

    def _mock_check(ctx, opts):
        return CheckReport(
            command="check",
            options={"changed": opts.changed},
            steps=[StepResult("prose lint", StepStatus.PASS)],
            files=[],
        )

    monkeypatch.setattr(
        "docs_dev.tui.screens.check_screen.run_check",
        _mock_check,
    )
    monkeypatch.setattr(
        "docs_dev.tui.screens.check_screen.run_prose_lint",
        lambda ctx, paths: [],
    )
    monkeypatch.setattr(
        "docs_dev.tui.screens.check_screen.sync_allowlists",
        lambda ctx: 0,
    )
    monkeypatch.setattr(
        "docs_dev.tui.screens.check_screen.add_term",
        lambda ctx, term, *, finding=None: (True, f"Added '{term}'"),
    )
