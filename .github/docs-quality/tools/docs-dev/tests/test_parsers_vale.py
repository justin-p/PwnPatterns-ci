from pathlib import Path

from docs_dev.parsers import vale

FIXTURES = Path(__file__).parent / "fixtures"


def test_vale_errors_only():
    findings = vale.parse_file(FIXTURES / "vale_sample.json")
    assert findings
    assert all(f.tool == "vale" for f in findings)
    assert all(f.severity == "error" for f in findings)


def test_vale_empty_log_returns_no_findings(tmp_path: Path) -> None:
    empty = tmp_path / "vale.json"
    empty.write_text("", encoding="utf-8")
    assert vale.parse_file(empty) == []
