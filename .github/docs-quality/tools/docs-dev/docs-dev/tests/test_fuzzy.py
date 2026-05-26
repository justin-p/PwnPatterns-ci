"""Fuzzy file filter matching."""

from __future__ import annotations

from pathlib import Path

from docs_dev.models import FileFindings, Finding
from docs_dev.tui.fuzzy import filter_file_findings, fuzzy_score


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
                message="x",
            )
        ],
    )


def test_fuzzy_score_substring() -> None:
    assert fuzzy_score("prom", "docs/infra/prometheus/foo.md") is not None


def test_fuzzy_score_subsequence() -> None:
    assert fuzzy_score("prmths", "prometheus") is not None


def test_fuzzy_score_multi_token() -> None:
    assert fuzzy_score("prom exp", "docs/infra/prometheus_exporter.md") is not None
    assert fuzzy_score("prom xyz", "docs/infra/prometheus_exporter.md") is None


def test_filter_file_findings_empty_query_returns_all() -> None:
    files = [_ff("docs/a.md"), _ff("docs/b.md")]
    assert filter_file_findings(files, "") == files


def test_filter_file_findings_ranks_by_relevance() -> None:
    files = [
        _ff("docs/wifi/general/WPA2_Protocol_In_Use/WPA2_Protocol_In_Use.md"),
        _ff(
            "docs/infra/general/Inadequate_Prometheus_Exporter_Implementation/"
            "Inadequate_Prometheus_Exporter_Implementation.md"
        ),
    ]
    result = filter_file_findings(files, "prometheus", repo_root=Path("/repo"))
    assert len(result) == 1
    assert "Prometheus" in result[0].path
