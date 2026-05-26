from pathlib import Path

from docs_dev.parsers import harper

FIXTURES = Path(__file__).parent / "fixtures"


def test_harper_resolves_full_path():
    paths = [
        ln.strip()
        for ln in (FIXTURES / "lint-paths.lst").read_text().splitlines()
        if ln.strip()
    ]
    findings = harper.parse_file(FIXTURES / "harper_sample.json", paths)
    assert findings
    assert findings[0].path.startswith("docs/")
    assert findings[0].tool == "harper"
