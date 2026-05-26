from __future__ import annotations

from pathlib import Path

from allowlist_terms import (
    filter_languagetool_matches,
    load_consumer_allowlists,
    languagetool_match_allowlisted,
    languagetool_matched_text,
    read_canonical_casing,
    read_terms_file,
)


def _match(context_text: str, *, offset: int = 0, length: int | None = None) -> dict:
    span = length if length is not None else len(context_text)
    return {
        "message": "Mogelijke spelfout gevonden.",
        "context": {"text": context_text, "offset": offset, "length": span},
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


def test_languagetool_matched_text_uses_context_span() -> None:
    ctx = "## Description  Er is een Prometheus exporter"
    match = _match(ctx, offset=3, length=11)
    assert languagetool_matched_text(match) == "Description"


def test_languagetool_match_allowlisted_long_context_token() -> None:
    ctx = "## Description  Er is een Prometheus exporter"
    match = _match(ctx, offset=3, length=11)
    assert languagetool_match_allowlisted(match, {"description"}, {})


def test_filter_languagetool_matches(tmp_path: Path) -> None:
    cfg = tmp_path / ".github/docs-quality/config/allowlists"
    cfg.mkdir(parents=True)
    (cfg / "terms.txt").write_text("fout\n", encoding="utf-8")
    terms, casing = load_consumer_allowlists(tmp_path)
    matches = [_match("fout "), _match("ongeldig")]
    filtered = filter_languagetool_matches(matches, terms, casing)
    assert len(filtered) == 1
    assert filtered[0]["context"]["text"] == "ongeldig"
