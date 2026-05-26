from __future__ import annotations

from pathlib import Path

from docs_dev.allowlist import (
    _split_canonical_casing_line,
    add_term,
    can_allowlist,
    canonical_casing_covers_term,
    dedupe_terms,
    dictionary_entries,
    dual_casing_needed,
    extract_allowlist_term,
    merge_patterns,
    foreign_latin_token_ignore,
    google_ordinal_token_ignore,
    microsoft_auto_token_ignore,
    vale_token_ignores,
    normalize_terms,
    parse_canonical_casing_file,
    parse_patterns_file,
    parse_terms_file,
    patterns_for_canonical_casing,
    read_terms,
    term_allowlist_status,
    terms_case_pair_from_finding,
    vale_accept_entries,
    without_allowlisted_term,
    write_patterns_file,
    write_terms_file,
)
from docs_dev.context import RepoContext
from docs_dev.manifest import Manifest
from docs_dev.models import Finding


def _finding(tool: str, message: str, rule: str | None = None) -> Finding:
    return Finding(
        tool=tool,
        path="docs/example.md",
        line=1,
        column=1,
        severity="error",
        message=message,
        rule=rule,
    )


def test_extract_vale_spelling_term() -> None:
    f = _finding("vale", "Did you really mean 'Traefik'?")
    assert extract_allowlist_term(f) == "Traefik"
    assert can_allowlist(f)


def test_extract_typos_term() -> None:
    f = _finding("typos", "typo `Identifing` → Identifying")
    assert extract_allowlist_term(f) == "Identifing"


def test_extract_languagetool_misspelling_term() -> None:
    f = _finding(
        "languagetool",
        "[languagetool] MORFOLOGIK_RULE_NL_NL: Mogelijke spelfout gevonden. "
        "— Type: misspelling — In text: «fout » — Suggestion: «fouten»",
        rule="MORFOLOGIK_RULE_NL_NL",
    )
    assert extract_allowlist_term(f) == "fout"
    assert can_allowlist(f)


def test_extract_languagetool_grammar_not_allowlisted() -> None:
    f = _finding(
        "languagetool",
        "[languagetool] RULE: Issue — Type: grammar — In text: «zijn»",
    )
    assert extract_allowlist_term(f) is None
    assert not can_allowlist(f)


def test_extract_vale_terms_use() -> None:
    f = _finding("vale", "Use 'prometheus' instead of 'Prometheus'.", rule="Vale.Terms")
    assert extract_allowlist_term(f) == "Prometheus"
    assert can_allowlist(f)


def test_extract_vale_terms_uses_canonical_casing() -> None:
    f = _finding("vale", "Use 'tiering' instead of 'Tiering'.", rule="Vale.Terms")
    casing = {"tiering": "Tiering"}
    assert extract_allowlist_term(f, casing=casing) == "Tiering"


def test_vale_accept_case_insensitive_for_canonical_casing() -> None:
    casing = {"tiering": "Tiering"}
    entries = vale_accept_entries(["Tiering"], casing=casing)
    assert "(?i)Tiering" in entries
    assert "tiering" not in entries


def test_vale_accept_includes_canonical_casing_without_terms_entry() -> None:
    pairs = [("adminAAsrv", "AdminAAsrv"), ("tiering", "Tiering")]
    casing = {a.casefold(): p for a, p in pairs}
    entries = vale_accept_entries([], casing=casing, casing_pairs=pairs)
    assert "(?i)AdminAAsrv" in entries
    assert "(?i)Tiering" in entries


def test_canonical_casing_covers_term() -> None:
    casing = {"adminaasrv": "AdminAAsrv", "tiering": "Tiering"}
    assert canonical_casing_covers_term("adminAAsrv", casing) == "AdminAAsrv"
    assert canonical_casing_covers_term("Tiering", casing) == "Tiering"
    assert canonical_casing_covers_term("svc_service", casing) is None


def test_patterns_for_canonical_casing() -> None:
    casing = {"certipy": "Certipy", "tiering": "Tiering"}
    assert patterns_for_canonical_casing(casing) == ["(?i)Certipy", "(?i)Tiering"]


def test_merge_patterns_adds_canonical_casing_patterns() -> None:
    casing = {"certipy": "Certipy"}
    merged = merge_patterns(["(?i)Traefik"], casing=casing)
    assert "(?i)Certipy" in merged
    assert "(?i)Traefik" in merged
    assert len(merged) == len(set(merged))


def test_merge_patterns_does_not_duplicate_existing() -> None:
    casing = {"certipy": "Certipy"}
    merged = merge_patterns(["(?i)Certipy", "(?i)Traefik"], casing=casing)
    assert merged.count("(?i)Certipy") == 1


def test_write_patterns_file_merges_canonical_casing(tmp_path: Path) -> None:
    patterns_file = tmp_path / "patterns.txt"
    patterns_file.write_text(
        "# header\n(?i)Traefik\n",
        encoding="utf-8",
    )
    header, raw = parse_patterns_file(patterns_file)
    casing = {"certipy": "Certipy"}
    changed = write_patterns_file(patterns_file, header, raw, casing=casing)
    assert changed
    body = patterns_file.read_text(encoding="utf-8")
    assert "(?i)Certipy" in body
    assert "(?i)Traefik" in body
    assert not write_patterns_file(
        patterns_file, header, merge_patterns(raw, casing=casing), casing=casing
    )


def test_vale_accept_collapses_case_variants() -> None:
    entries = vale_accept_entries(["prometheus", "Prometheus", "Traefik"])
    assert "(?i)Prometheus" in entries
    assert "prometheus" not in entries
    assert "Prometheus" not in entries
    assert "Traefik" in entries


def test_dictionary_entries_prefers_title_case() -> None:
    assert dictionary_entries(["prometheus", "Prometheus"]) == ["Prometheus"]


def test_dedupe_terms_merges_exact_duplicates() -> None:
    assert dedupe_terms(["Prometheus", "Prometheus", "Traefik"]) == [
        "Prometheus",
        "Traefik",
    ]


def test_normalize_terms_applies_canonical_casing() -> None:
    assert normalize_terms(
        ["kerberos", "kubernetes", "prek"],
        casing={"kerberos": "Kerberos", "kubernetes": "Kubernetes"},
    ) == ["Kerberos", "Kubernetes", "prek"]


def test_write_terms_file_dedupes_and_preserves_header(tmp_path: Path) -> None:
    terms_file = tmp_path / "terms.txt"
    terms_file.write_text(
        "# header\n"
        "# line two\n"
        "prometheus\n"
        "Prometheus\n"
        "Prometheus\n",
        encoding="utf-8",
    )
    header, raw = parse_terms_file(terms_file)
    assert header == ["# header", "# line two"]
    changed = write_terms_file(terms_file, header, raw)
    assert changed
    assert read_terms(terms_file) == ["Prometheus"]
    assert not write_terms_file(terms_file, header, read_terms(terms_file))


def test_extract_microsoft_auto_term() -> None:
    f = _finding(
        "vale",
        "In general, don't hyphenate 'Auto-Discovery'.",
        rule="Microsoft.Auto",
    )
    assert extract_allowlist_term(f) == "Auto-Discovery"
    assert can_allowlist(f)


def test_microsoft_auto_token_ignore() -> None:
    assert microsoft_auto_token_ignore("Auto-Discovery") == r"(?i)(\bAuto\-Discovery\b)"
    assert microsoft_auto_token_ignore("automated") is None


def test_microsoft_auto_token_ignores_from_terms() -> None:
    patterns = vale_token_ignores(["Auto-Discovery", "Traefik"])
    assert patterns == [r"(?i)(\bAuto\-Discovery\b)"]


def test_extract_foreign_latin_abbrev() -> None:
    for message in (
        "Use 'for example' instead of 'e.g.'.",
        "Use 'for example' instead of 'e.g.,'.",
    ):
        f = _finding("vale", message, rule="Microsoft.Foreign")
        assert extract_allowlist_term(f) == "e.g."
        assert can_allowlist(f)


def test_foreign_latin_token_ignore() -> None:
    assert foreign_latin_token_ignore("e.g.,") == r"(?i)(\b(?:e\.g\.|eg)[\s\x2c])"


def test_extract_google_ordinal() -> None:
    f = _finding(
        "vale",
        "Spell out all ordinal numbers ('4th') in text.",
        rule="Google.Ordinal",
    )
    assert extract_allowlist_term(f) == "4th"
    assert can_allowlist(f)


def test_google_ordinal_token_ignore() -> None:
    assert google_ordinal_token_ignore("4th") == r"(?i)(\b4th\b)"
    assert google_ordinal_token_ignore("Prometheus") is None


def test_vale_token_ignores_includes_ordinals() -> None:
    from docs_dev.allowlist import vale_token_ignores

    patterns = vale_token_ignores(["4th", "Traefik"])
    assert r"(?i)(\b4th\b)" in patterns


def test_dual_casing_not_needed_for_foreign_substitution(tmp_path: Path) -> None:
    docs_quality = tmp_path / "dq"
    allow_dir = docs_quality / "config" / "allowlists"
    allow_dir.mkdir(parents=True)
    (allow_dir / "canonical-casing.txt").write_text(
        "# header\nfor example For example\n",
        encoding="utf-8",
    )
    ctx = RepoContext(
        repo_root=tmp_path,
        docs_quality_dir=docs_quality,
        consumer_config_dir=docs_quality / "config",
        automation_dir=docs_quality / "automation",
        automation_bin=docs_quality / "automation" / "bin",
        automation_install=docs_quality / "automation" / "install",
        manifest_path=docs_quality / "config" / "manifest.env",
        manifest=Manifest(
            doc_lint_install_dir="/tmp",
            vale_version="3.9.1",
            typos_version="1.29.0",
            rumdl_version="0.1.78",
            harper_version="2.1.0",
            harper_user_dict="dict.txt",
            harper_ignore_rules_file="ignore",
            shellcheck_version="0.11.0",
            shfmt_version="3.12.0",
            reviewdog_version="0.20.3",
            lychee_version="0.24.2",
            actionlint_version="1.7.12",
            raw={},
        ),
        doc_lint_install_dir=tmp_path / "linters",
        lint_log_dir=tmp_path / "lint-logs",
        lychee_filter_jq=tmp_path / "filter.jq",
    )
    f = _finding(
        "vale",
        "Use 'for example' instead of 'e.g.'.",
        rule="Google.Latin",
    )
    assert not dual_casing_needed(ctx, f)


def test_extract_returns_none_for_contractions() -> None:
    f = _finding("vale", "Use 'it is' instead of 'it's'.", rule="PwnPatterns.Contractions")
    assert extract_allowlist_term(f) is None
    assert not can_allowlist(f)


def test_without_allowlisted_term_keeps_other_allowlistable_findings() -> None:
    prometheus = _finding(
        "vale", "Use 'prometheus' instead of 'Prometheus'.", rule="Vale.Terms"
    )
    traefik = _finding("vale", "Did you really mean 'Traefik'?")
    contraction = _finding(
        "vale", "Use 'it is' instead of 'it's'.", rule="PwnPatterns.Contractions"
    )
    findings = [prometheus, traefik, contraction]

    remaining = without_allowlisted_term(findings, "Prometheus")

    assert traefik in remaining
    assert contraction in remaining
    assert prometheus not in remaining
    assert len(remaining) == 2


def test_add_term_appends_and_dedupes(tmp_path: Path) -> None:
    allow_dir = tmp_path / "config" / "allowlists"
    allow_dir.mkdir(parents=True)
    terms_file = allow_dir / "terms.txt"
    terms_file.write_text("# header\nexisting\n", encoding="utf-8")

    repo = tmp_path
    (repo / ".github" / "docs-quality").mkdir(parents=True)
    docs_quality = repo / ".github" / "docs-quality"
    (docs_quality / "config" / "allowlists").mkdir(parents=True, exist_ok=True)
    terms_file = docs_quality / "config" / "allowlists" / "terms.txt"
    terms_file.write_text("# terms\nexisting\n", encoding="utf-8")

    ctx = RepoContext(
        repo_root=repo,
        docs_quality_dir=docs_quality,
        consumer_config_dir=docs_quality / "config",
        automation_dir=docs_quality / "automation",
        automation_bin=docs_quality / "automation" / "bin",
        automation_install=docs_quality / "automation" / "install",
        manifest_path=docs_quality / "config" / "manifest.env",
        manifest=Manifest(
            doc_lint_install_dir="/tmp",
            vale_version="3.9.1",
            typos_version="1.29.0",
            rumdl_version="0.1.78",
            harper_version="2.1.0",
            harper_user_dict=".github/docs-quality/generated/harper-dictionary.txt",
            harper_ignore_rules_file=".github/docs-quality/config/harper.ignore-rules",
            shellcheck_version="0.11.0",
            shfmt_version="3.12.0",
            reviewdog_version="0.20.3",
            lychee_version="0.24.2",
            actionlint_version="1.7.12",
            raw={},
        ),
        doc_lint_install_dir=tmp_path / "linters",
        lint_log_dir=tmp_path / "lint-logs",
        lychee_filter_jq=tmp_path / "filter.jq",
    )

    added, msg = add_term(ctx, "Traefik")
    assert added, msg
    assert "Traefik" in read_terms(terms_file)

    again, dup_msg = add_term(ctx, "Traefik")
    assert again
    assert "already allowlisted" in dup_msg.lower()


def _make_allowlist_ctx(tmp_path: Path, docs_quality: Path) -> RepoContext:
    return RepoContext(
        repo_root=tmp_path,
        docs_quality_dir=docs_quality,
        consumer_config_dir=docs_quality / "config",
        automation_dir=docs_quality / "automation",
        automation_bin=docs_quality / "automation" / "bin",
        automation_install=docs_quality / "automation" / "install",
        manifest_path=docs_quality / "config" / "manifest.env",
        manifest=Manifest(
            doc_lint_install_dir="/tmp",
            vale_version="3.9.1",
            typos_version="1.29.0",
            rumdl_version="0.1.78",
            harper_version="2.1.0",
            harper_user_dict=".github/docs-quality/generated/harper-dictionary.txt",
            harper_ignore_rules_file=".github/docs-quality/config/harper.ignore-rules",
            shellcheck_version="0.11.0",
            shfmt_version="3.12.0",
            reviewdog_version="0.20.3",
            lychee_version="0.24.2",
            actionlint_version="1.7.12",
            raw={},
        ),
        doc_lint_install_dir=tmp_path / "linters",
        lint_log_dir=tmp_path / "lint-logs",
        lychee_filter_jq=tmp_path / "filter.jq",
    )


def test_add_term_case_variant_already_covered(tmp_path: Path) -> None:
    docs_quality = tmp_path / ".github" / "docs-quality"
    allow_dir = docs_quality / "config" / "allowlists"
    allow_dir.mkdir(parents=True)
    terms_file = allow_dir / "terms.txt"
    terms_file.write_text("# terms\ntiering\n", encoding="utf-8")
    (allow_dir / "canonical-casing.txt").write_text("tiering Tiering\n", encoding="utf-8")

    ctx = _make_allowlist_ctx(tmp_path, docs_quality)

    assert term_allowlist_status(ctx, "tiering") == "Tiering"
    ok, msg = add_term(ctx, "tiering")
    assert ok
    assert (
        "already allowlisted" in msg.lower()
        or "updated" in msg.lower()
        or "normalized" in msg.lower()
    )
    assert read_terms(terms_file) == ["Tiering"]


def test_split_canonical_casing_rejects_odd_word_count() -> None:
    assert _split_canonical_casing_line("for example For") is None


def test_parse_canonical_casing_multiword_alias(tmp_path: Path) -> None:
    path = tmp_path / "canonical-casing.txt"
    path.write_text(
        "# header\nfor example For example\ncertipy Certipy\n",
        encoding="utf-8",
    )
    header, pairs = parse_canonical_casing_file(path)
    assert header == ["# header"]
    assert pairs == [("for example", "For example"), ("certipy", "Certipy")]
    casing = {a.casefold(): p for a, p in pairs}
    assert patterns_for_canonical_casing(casing) == [
        "(?i)Certipy",
        "(?i)For example",
    ]


def test_terms_case_pair_from_vale_terms_finding() -> None:
    f = _finding(
        "vale",
        "Use 'Prometheus' instead of 'prometheus'.",
        rule="Vale.Terms",
    )
    assert terms_case_pair_from_finding(f) == ("prometheus", "Prometheus")


def test_dual_casing_needed_when_term_exists_without_canonical_pair(
    tmp_path: Path,
) -> None:
    docs_quality = tmp_path / ".github" / "docs-quality"
    allow_dir = docs_quality / "config" / "allowlists"
    allow_dir.mkdir(parents=True)
    (allow_dir / "terms.txt").write_text("# terms\nPrometheus\n", encoding="utf-8")
    (allow_dir / "canonical-casing.txt").write_text("# casing\n", encoding="utf-8")

    ctx = _make_allowlist_ctx(tmp_path, docs_quality)
    f = _finding(
        "vale",
        "Use 'Prometheus' instead of 'prometheus'.",
        rule="Vale.Terms",
    )
    assert term_allowlist_status(ctx, "Prometheus") == "Prometheus"
    assert dual_casing_needed(ctx, f)


def test_dual_casing_needed_for_multiword_terms_finding(tmp_path: Path) -> None:
    docs_quality = tmp_path / ".github" / "docs-quality"
    allow_dir = docs_quality / "config" / "allowlists"
    allow_dir.mkdir(parents=True)
    (allow_dir / "terms.txt").write_text("# terms\nFor example\n", encoding="utf-8")
    (allow_dir / "canonical-casing.txt").write_text("# casing\n", encoding="utf-8")

    ctx = _make_allowlist_ctx(tmp_path, docs_quality)
    f = _finding(
        "vale",
        "Use 'For example' instead of 'for example'.",
        rule="Vale.Terms",
    )
    assert terms_case_pair_from_finding(f) == ("for example", "For example")
    assert dual_casing_needed(ctx, f)


def test_add_term_for_example_dual_casing(tmp_path: Path) -> None:
    docs_quality = tmp_path / ".github" / "docs-quality"
    allow_dir = docs_quality / "config" / "allowlists"
    allow_dir.mkdir(parents=True)
    terms_file = allow_dir / "terms.txt"
    terms_file.write_text("# terms\nFor example\n", encoding="utf-8")
    casing_file = allow_dir / "canonical-casing.txt"
    casing_file.write_text("# casing\n", encoding="utf-8")

    ctx = _make_allowlist_ctx(tmp_path, docs_quality)
    f = _finding(
        "vale",
        "Use 'For example' instead of 'for example'.",
        rule="Vale.Terms",
    )

    ok, msg = add_term(ctx, "For example", finding=f)
    assert ok
    assert "dual-valid casing" in msg
    _, pairs = parse_canonical_casing_file(casing_file)
    assert ("for example", "For example") in pairs
    entries = vale_accept_entries(
        read_terms(terms_file),
        casing={a.casefold(): p for a, p in pairs},
    )
    assert "(?i)For example" in entries
    assert not dual_casing_needed(ctx, f)


def test_add_term_from_terms_finding_adds_canonical_casing(tmp_path: Path) -> None:
    docs_quality = tmp_path / ".github" / "docs-quality"
    allow_dir = docs_quality / "config" / "allowlists"
    allow_dir.mkdir(parents=True)
    terms_file = allow_dir / "terms.txt"
    terms_file.write_text("# terms\nPrometheus\n", encoding="utf-8")
    casing_file = allow_dir / "canonical-casing.txt"
    casing_file.write_text("# casing\n", encoding="utf-8")

    ctx = _make_allowlist_ctx(tmp_path, docs_quality)
    f = _finding(
        "vale",
        "Use 'Prometheus' instead of 'prometheus'.",
        rule="Vale.Terms",
    )

    ok, msg = add_term(ctx, "Prometheus", finding=f)
    assert ok
    assert "dual-valid casing" in msg
    _, pairs = parse_canonical_casing_file(casing_file)
    assert ("prometheus", "Prometheus") in pairs
    entries = vale_accept_entries(
        read_terms(terms_file),
        casing={a.casefold(): p for a, p in pairs},
    )
    assert "(?i)Prometheus" in entries
    assert not dual_casing_needed(ctx, f)


def test_add_term_promotes_better_casing(tmp_path: Path) -> None:
    docs_quality = tmp_path / ".github" / "docs-quality"
    allow_dir = docs_quality / "config" / "allowlists"
    allow_dir.mkdir(parents=True)
    terms_file = allow_dir / "terms.txt"
    terms_file.write_text("# terms\ntiering\n", encoding="utf-8")
    (allow_dir / "canonical-casing.txt").write_text("tiering Tiering\n", encoding="utf-8")

    ctx = _make_allowlist_ctx(tmp_path, docs_quality)

    ok, msg = add_term(ctx, "Tiering")
    assert ok
    assert read_terms(terms_file) == ["Tiering"]
