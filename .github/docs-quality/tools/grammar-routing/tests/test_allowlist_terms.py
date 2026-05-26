from __future__ import annotations

from pathlib import Path

from allowlist_terms import (
    filter_languagetool_matches,
    load_consumer_allowlists,
    languagetool_match_allowlisted,
    read_canonical_casing,
    read_terms_file,
)


def _match(context_text: str) -> dict:
    return {
        "message": "Mogelijke spelfout gevonden.",
        "context": {"text": context_text, "offset": 0, "length": len(context_text)},
        "rule": {"id": "MORFOLOGIK_RULE_NL_NL", "issueType": "misspelling"},
    }


def test_read_terms_file(tmp_path: Path) -> None:
    path = tmp_path / "terms.txt"
    path.write_text("# comment\nPwnPatterns\nfoo\n", encoding="utf-8")
    assert read_terms_file(path) == {"pwnpatterns", "foo"}


def test_languagetool_match_allowlisted_by_term() -> None:
    terms = {"fout"}
    match = _match("fout ")
    assert languagetool_match_allowlisted(match, terms, {})


def test_languagetool_match_allowlisted_by_canonical_casing() -> None:
    terms: set[str] = set()
    casing = {"tiering": "Tiering"}
    match = _match("tiering")
    assert languagetool_match_allowlisted(match, terms, casing)


def test_filter_languagetool_matches(tmp_path: Path) -> None:
    cfg = tmp_path / ".github/docs-quality/config/allowlists"
    cfg.mkdir(parents=True)
    (cfg / "terms.txt").write_text("fout\n", encoding="utf-8")
    terms, casing = load_consumer_allowlists(tmp_path)
    matches = [_match("fout "), _match("ongeldig")]
    filtered = filter_languagetool_matches(matches, terms, casing)
    assert len(filtered) == 1
    assert filtered[0]["context"]["text"] == "ongeldig"
