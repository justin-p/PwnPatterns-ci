from pathlib import Path

from docs_dev.parsers import vale
from docs_dev.vale_fix import apply_vale_line_fixes, collect_contraction_fixes, load_vale_json

FIXTURES = Path(__file__).parent / "fixtures"


def test_collect_contraction_fixes_from_fixture() -> None:
    data = load_vale_json(FIXTURES / "vale_contractions_sample.json")
    fixes = collect_contraction_fixes(data)
    assert len(fixes) == 2
    assert fixes[0].replacement == "was not"


def test_apply_contraction_fixes(tmp_path: Path) -> None:
    md = tmp_path / "docs" / "example" / "contractions.md"
    md.parent.mkdir(parents=True)
    md.write_text("They wasn't sure.\nWe don't know.\n", encoding="utf-8")
    data = load_vale_json(FIXTURES / "vale_contractions_sample.json")
    fixes = collect_contraction_fixes(data)
    assert apply_vale_line_fixes(tmp_path, fixes) == 2
    assert md.read_text(encoding="utf-8") == "They was not sure.\nWe do not know.\n"


def test_vale_parser_marks_contractions_fixable() -> None:
    findings = vale.parse_file(FIXTURES / "vale_contractions_sample.json")
    assert len(findings) == 2
    assert all(f.fixable for f in findings)
    assert findings[0].column == 6


def test_vale_fixture_contains_replace_actions() -> None:
    data = load_vale_json(FIXTURES / "vale_contractions_sample.json")
    fixes = collect_contraction_fixes(data)
    first = fixes[0]
    assert first.path == "docs/example/contractions.md"
    assert first.line == 1
    assert first.span_start == 6
    assert first.span_end == 11
    assert first.replacement == "was not"
