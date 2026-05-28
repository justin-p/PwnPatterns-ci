"""reviewdog overflow digest helpers."""

from __future__ import annotations

import json

from pwnpatterns_ci.reviewdog import (
    _format_overflow_digest,
    _parse_rdjsonl_lines,
    _split_rdjsonl_by_selection,
    _truncate_rdjsonl,
)


def test_truncate_does_not_add_synthetic_inline_comment() -> None:
    lines = [
        json.dumps(
            {
                "message": "[textlint] typo",
                "location": {
                    "path": "docs/a.md",
                    "range": {"start": {"line": 1, "column": 1}},
                },
                "severity": "ERROR",
            }
        )
        for _ in range(25)
    ]
    payload = "\n".join(lines) + "\n"
    truncated, omitted = _truncate_rdjsonl(payload, max_results=20)
    assert omitted == 5
    assert "review output truncated" not in truncated
    assert len(_parse_rdjsonl_lines(truncated)) == 20


def test_overflow_digest_includes_check_and_workflow_links() -> None:
    diag = {
        "message": "[languagetool] bad grammar",
        "location": {
            "path": "docs/smoke.md",
            "range": {"start": {"line": 24, "column": 1}},
        },
        "severity": "ERROR",
    }
    text = _format_overflow_digest(
        [diag],
        inline_shown=20,
        omitted=5,
        check_url="https://github.com/ocd-nl/PwnPatterns-nl/runs/78118224180",
        workflow_url="https://github.com/ocd-nl/PwnPatterns-nl/actions/runs/26522693735",
    )
    assert "78118224180" in text
    assert "26522693735" in text
    assert "[languagetool]" in text
    assert "docs/smoke.md:24:1" in text
    assert "<details>" in text
    assert "Remaining comments which cannot be posted as a review comment" in text


def test_split_selection_returns_only_omitted_diagnostics() -> None:
    lines = []
    for i in range(3):
        lines.append(
            json.dumps(
                {
                    "message": f"[textlint] issue-{i}",
                    "location": {
                        "path": "docs/a.md",
                        "range": {"start": {"line": i + 1, "column": 1}},
                    },
                    "severity": "ERROR",
                }
            )
        )
    payload = "\n".join(lines) + "\n"
    kept_payload, kept_diags, omitted_diags, omitted = _split_rdjsonl_by_selection(payload, max_results=2)
    assert omitted == 1
    assert len(_parse_rdjsonl_lines(kept_payload)) == 2
    assert len(kept_diags) == 2
    assert len(omitted_diags) == 1
