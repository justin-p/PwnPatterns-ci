"""Tests for grammar tool routing by frontmatter language."""

from __future__ import annotations

from pathlib import Path

from route_grammar_paths import (
    grammar_tool_for_language,
    load_language_tools_config,
    merge_lint_paths,
    read_grammar_language,
    route_paths,
    spelling_tool_for_language,
    write_route_outputs,
)


def test_load_config_after_languagetool_codes_section(tmp_path: Path) -> None:
    cfg_path = tmp_path / "language-tools.yml"
    cfg_path.write_text(
        """default_language: en
grammar_tools:
  en: harper
languagetool_codes:
  en: en
languagetool_enabled: false
grammar_from_frontmatter: false
""",
        encoding="utf-8",
    )
    cfg = load_language_tools_config(cfg_path)
    assert cfg["languagetool_enabled"] is False
    assert cfg["grammar_from_frontmatter"] is False


def test_load_default_config(tmp_path: Path) -> None:
    cfg = load_language_tools_config(tmp_path / "missing.yml")
    assert cfg["default_language"] == "en"
    assert cfg["grammar_tools"]["en"] == "harper"
    assert cfg["grammar_tools"]["nl"] == "languagetool"
    assert cfg["spelling_tools"]["en"] == "typos"
    assert cfg["spelling_tools"]["nl"] == "textlint"
    assert ".github/tests/fixtures/nl-languagetool-smoke.md" in cfg["grammar_smoke_paths"]


def test_grammar_tool_for_language() -> None:
    cfg = load_language_tools_config(Path("/nonexistent"))
    assert grammar_tool_for_language("en", cfg) == "harper"
    assert grammar_tool_for_language("nl", cfg) == "languagetool"
    assert grammar_tool_for_language("fr", cfg) == "languagetool"


def test_spelling_tool_for_language() -> None:
    cfg = load_language_tools_config(Path("/nonexistent"))
    assert spelling_tool_for_language("en", cfg) == "typos"
    assert spelling_tool_for_language("nl", cfg) == "textlint"
    assert spelling_tool_for_language("fr", cfg) == "typos"


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
    assert routed["typos"] == ["docs/en.md"]
    assert routed["textlint"] == ["docs/nl.md"]
    assert routed["harper"] == ["docs/en.md"]
    assert len(routed["languagetool"]) == 1
    assert routed["languagetool"][0]["path"] == "docs/nl.md"
    assert routed["languagetool"][0]["lt_code"] == "nl"


def test_grammar_from_frontmatter_false_uses_default(tmp_path: Path) -> None:
    repo = tmp_path
    docs = repo / "docs"
    docs.mkdir()
    mislabeled = docs / "english-with-nl-tag.md"
    mislabeled.write_text(
        '---\nlanguage: "nl"\ntitle: "t"\n---\n\nEnglish body text.\n',
        encoding="utf-8",
    )
    cfg = load_language_tools_config(Path("/nonexistent"))
    cfg["grammar_from_frontmatter"] = False
    cfg["default_language"] = "en"
    routed = route_paths(["docs/english-with-nl-tag.md"], cfg, repo)
    assert routed["typos"] == ["docs/english-with-nl-tag.md"]
    assert routed["textlint"] == []
    assert routed["harper"] == ["docs/english-with-nl-tag.md"]
    assert routed["languagetool"] == []


def test_grammar_language_override_when_frontmatter_disabled(tmp_path: Path) -> None:
    repo = tmp_path
    docs = repo / "docs"
    docs.mkdir()
    nl_doc = docs / "dutch.md"
    nl_doc.write_text(
        '---\nlanguage: "en"\ngrammar_language: "nl"\n---\n\nNederlandse tekst.\n',
        encoding="utf-8",
    )
    cfg = load_language_tools_config(Path("/nonexistent"))
    cfg["grammar_from_frontmatter"] = False
    assert read_grammar_language(Path("docs/dutch.md"), repo, cfg) == "nl"
    routed = route_paths(["docs/dutch.md"], cfg, repo)
    assert routed["typos"] == []
    assert routed["textlint"] == ["docs/dutch.md"]
    assert len(routed["languagetool"]) == 1
