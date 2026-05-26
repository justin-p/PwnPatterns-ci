from __future__ import annotations

from pathlib import Path

from docs_dev.parsers import textlint


def test_parse_textlint_json() -> None:
    sample = Path(__file__).parent / "fixtures" / "textlint_sample.json"
    findings = textlint.parse_file(sample)
    assert len(findings) == 1
    f = findings[0]
    assert f.tool == "textlint"
    assert f.path == "docs/nl/sample.md"
    assert f.line == 3
    assert "foutwoord" in f.message
    assert textlint.spelling_word(f.message) == "foutwoord"
