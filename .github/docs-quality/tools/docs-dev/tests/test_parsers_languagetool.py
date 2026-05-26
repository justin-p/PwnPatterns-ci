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
    assert "Matched: «fout»" in f.message
    assert "In text:" not in f.message
    assert f.matched_text == "fout"
    assert f.severity == "error"


def test_misspelling_message_uses_matched_token_not_full_context() -> None:
    ctx = "... verzamelde metrics worden opgeslagen in een tijdreeks-database met een multidimensionaal datamodel en kunne..."
    token = "kunne"
    off = ctx.index(token)
    payload = [
        {
            "file": "docs/x.md",
            "language": "nl",
            "matches": [
                {
                    "message": "Mogelijke spelfout gevonden.",
                    "line": 26,
                    "column": 1,
                    "context": {"text": ctx, "offset": off, "length": len(token)},
                    "rule": {"id": "MORFOLOGIK_RULE_NL_NL", "issueType": "misspelling"},
                    "replacements": [{"value": "kunnen"}],
                }
            ],
        }
    ]
    import json
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", encoding="utf-8") as tmp:
        json.dump(payload, tmp)
        tmp.flush()
        findings = languagetool.parse_file(Path(tmp.name))
    assert len(findings) == 1
    f = findings[0]
    assert f.matched_text == "kunne"
    assert "Matched: «kunne»" in f.message
    assert ctx not in f.message
