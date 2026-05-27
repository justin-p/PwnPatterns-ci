"""report_failures CI summary output."""

from __future__ import annotations

import json
from pathlib import Path

from pwnpatterns_ci.report import report_failures

FIXTURES = (
    Path(__file__).resolve().parents[3]
    / "docs-dev"
    / "tests"
    / "fixtures"
)


def test_report_failures_prints_vale_diagnostics(capsys, tmp_path: Path) -> None:
    sample = FIXTURES / "vale_sample.json"
    if not sample.is_file():
        return
    log_dir = tmp_path / "lint-logs"
    log_dir.mkdir()
    (log_dir / "vale.json").write_text(sample.read_text(encoding="utf-8"), encoding="utf-8")
    (log_dir / "vale.exit").write_text("1", encoding="utf-8")

    assert report_failures(log_dir) == 1

    out = capsys.readouterr().out
    assert "vale lint log summary" in out
    assert "[vale] Vale.Terms:" in out
    assert "docs/example/sample.md:10:" in out
    assert out.count("write-good.Weasel") == 0


def test_report_failures_falls_back_when_json_missing(capsys, tmp_path: Path) -> None:
    log_dir = tmp_path / "lint-logs"
    log_dir.mkdir()
    (log_dir / "rumdl.exit").write_text("1", encoding="utf-8")
    (log_dir / "rumdl.stderr").write_text("rumdl: invalid config\n", encoding="utf-8")

    assert report_failures(log_dir) == 1

    out = capsys.readouterr().out
    assert "rumdl: invalid config" in out


def test_report_failures_prints_metadata_rdjsonl(capsys, tmp_path: Path) -> None:
    log_dir = tmp_path / "lint-logs"
    log_dir.mkdir()
    diagnostic = {
        "message": "[metadata] invalid frontmatter",
        "location": {
            "path": "docs/example/bad.md",
            "range": {"start": {"line": 1, "column": 1}, "end": {"line": 1, "column": 1}},
        },
        "severity": "ERROR",
    }
    (log_dir / "metadata.rdjsonl").write_text(
        json.dumps(diagnostic) + "\n",
        encoding="utf-8",
    )
    (log_dir / "metadata.exit").write_text("1", encoding="utf-8")

    assert report_failures(log_dir) == 1

    out = capsys.readouterr().out
    assert "docs/example/bad.md:1:1: [metadata] invalid frontmatter" in out
