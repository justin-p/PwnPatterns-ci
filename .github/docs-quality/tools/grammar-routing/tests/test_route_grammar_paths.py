"""Tests for grammar tool routing by frontmatter language."""

from __future__ import annotations

from pathlib import Path

from route_grammar_paths import (
    grammar_tool_for_language,
    load_language_tools_config,
    merge_lint_paths,
    route_paths,
    write_route_outputs,
)


def test_load_default_config(tmp_path: Path) -> None:
    cfg = load_language_tools_config(tmp_path / "missing.yml")
    assert cfg["default_language"] == "en"
    assert cfg["grammar_tools"]["en"] == "harper"
    assert cfg["grammar_tools"]["nl"] == "languagetool"
    assert ".github/tests/fixtures/nl-languagetool-smoke.md" in cfg["grammar_smoke_paths"]


def test_grammar_tool_for_language() -> None:
    cfg = load_language_tools_config(Path("/nonexistent"))
    assert grammar_tool_for_language("en", cfg) == "harper"
    assert grammar_tool_for_language("nl", cfg) == "languagetool"
    assert grammar_tool_for_language("fr", cfg) == "languagetool"


def test_merge_lint_paths_includes_smoke_fixture(tmp_path: Path) -> None:
    smoke = tmp_path / ".github/tests/fixtures/nl-languagetool-smoke.md"
    smoke.parent.mkdir(parents=True)
    smoke.write_text('---\nlanguage: "nl"\n---\n', encoding="utf-8")
    cfg = load_language_tools_config(Path("/nonexistent"))
    cfg["grammar_smoke_paths"] = [".github/tests/fixtures/nl-languagetool-smoke.md"]
    merged = merge_lint_paths([], cfg, tmp_path)
    assert merged == [".github/tests/fixtures/nl-languagetool-smoke.md"]


def test_write_route_outputs_relative_log_dir(tmp_path: Path) -> None:
    repo = tmp_path
    log_dir = repo / "lint-logs"
    cfg = load_language_tools_config(Path("/nonexistent"))
    routed = route_paths(["docs/en.md"], cfg, repo)
    write_route_outputs(log_dir, routed)
    assert (repo / "lint-logs" / "grammar-route.json").is_file()


def test_route_paths_by_language(tmp_path: Path) -> None:
    repo = tmp_path
    docs = repo / "docs"
    docs.mkdir()
    en_doc = docs / "en.md"
    nl_doc = docs / "nl.md"
    en_doc.write_text(
        '---\nlanguage: "en"\ntitle: "t"\n---\n\nEnglish text.\n',
        encoding="utf-8",
    )
    nl_doc.write_text(
        '---\nlanguage: "nl"\ntitle: "t"\n---\n\nNederlandse tekst.\n',
        encoding="utf-8",
    )
    cfg = load_language_tools_config(Path("/nonexistent"))
    routed = route_paths(["docs/en.md", "docs/nl.md"], cfg, repo)
    assert routed["harper"] == ["docs/en.md"]
    assert len(routed["languagetool"]) == 1
    assert routed["languagetool"][0]["path"] == "docs/nl.md"
    assert routed["languagetool"][0]["lt_code"] == "nl"
