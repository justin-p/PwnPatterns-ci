from pathlib import Path

from docs_dev.parsers import typos

FIXTURES = Path(__file__).parent / "fixtures"


def test_typos_jsonl():
    findings = typos.parse_file(FIXTURES / "typos_sample.jsonl")
    assert len(findings) == 2
    assert findings[0].tool == "typos"
    assert "typo" in findings[0].message
