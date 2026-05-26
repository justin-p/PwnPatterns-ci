from pathlib import Path

from docs_dev.template_list_contractions import apply_fixes, scan_file


def test_detects_it_is_in_yaml_list_block(tmp_path: Path) -> None:
    rel = "docs/example/finding.md"
    md = tmp_path / rel
    md.parent.mkdir(parents=True)
    md.write_text(
        "## Solution\n\n```YAML\n[list]\n"
        "[*]Recent Usage: indicating it's being used.\n"
        "[/list]\n```\n",
        encoding="utf-8",
    )
    findings = scan_file(tmp_path, rel)
    assert len(findings) == 1
    assert findings[0].rule == "PwnPatterns.Contractions"
    assert findings[0].fixable
    assert "it is" in findings[0].message


def test_ignores_plain_prose_outside_fence(tmp_path: Path) -> None:
    rel = "docs/example/plain.md"
    md = tmp_path / rel
    md.parent.mkdir(parents=True)
    md.write_text("Plain it's here.\n", encoding="utf-8")
    assert scan_file(tmp_path, rel) == []


def test_apply_fix_in_list_block(tmp_path: Path) -> None:
    rel = "docs/example/fix.md"
    md = tmp_path / rel
    md.parent.mkdir(parents=True)
    md.write_text(
        "```YAML\n[list]\n[*]Line with it's inside.\n[/list]\n```\n",
        encoding="utf-8",
    )
    assert apply_fixes(tmp_path, [rel]) == 1
    assert "it is" in md.read_text(encoding="utf-8")
    assert "it's" not in md.read_text(encoding="utf-8")
