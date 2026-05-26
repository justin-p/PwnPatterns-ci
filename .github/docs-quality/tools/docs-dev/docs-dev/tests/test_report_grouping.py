from docs_dev.models import Finding, group_findings_by_file


def test_group_by_file_sorted_by_count():
    findings = [
        Finding("typos", "docs/a.md", 1, 1, "error", "one"),
        Finding("vale", "docs/b.md", 2, 1, "error", "two"),
        Finding("vale", "docs/b.md", 3, 1, "error", "three"),
        Finding("harper", "docs/b.md", 4, 1, "error", "four"),
        Finding("harper", "docs/a.md", 5, 1, "error", "five"),
    ]
    grouped = group_findings_by_file(findings)
    assert grouped[0].path == "docs/b.md"
    assert grouped[0].count == 3
    assert grouped[1].path == "docs/a.md"
    assert grouped[1].count == 2
