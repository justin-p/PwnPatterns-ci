from __future__ import annotations

from pathlib import Path

from docs_dev.parsers import languagetool

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_languagetool_sample() -> None:
    findings = languagetool.parse_file(FIXTURES / "languagetool_sample.json")
    assert len(findings) == 1
    f = findings[0]
    assert f.tool == "languagetool"
    assert "Type: misspelling" in f.message
    assert "In text: «fout »" in f.message
    assert f.matched_text == "fout"
    assert f.severity == "error"
