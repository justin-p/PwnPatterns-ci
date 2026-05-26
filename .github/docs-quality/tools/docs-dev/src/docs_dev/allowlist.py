"""Canonical allowlist (terms.txt) read/write and term extraction from lint findings."""

from __future__ import annotations

import re
from pathlib import Path

from docs_dev.context import RepoContext
from docs_dev.models import Finding
from docs_dev.runners import maintenance

_SPELLING_RE = re.compile(
    r"Did you really mean ['\"]([^'\"]+)['\"]\??",
    re.IGNORECASE,
)
_TERMS_USE_RE = re.compile(
    r"Use ['\"]([^'\"]+)['\"] instead of ['\"]([^'\"]+)",
    re.IGNORECASE,
)
_MICROSOFT_AUTO_RE = re.compile(
    r"don'?t hyphenate ['\"]([^'\"]+)['\"]",
    re.IGNORECASE,
)
_TYPO_RE = re.compile(r"typo `([^`]+)` →", re.IGNORECASE)
_GOOGLE_ORDINAL_RE = re.compile(
    r"Spell out all ordinal numbers \('([^']+)'\)",
    re.IGNORECASE,
)
_ORDINAL_TOKEN_RE = re.compile(r"^\d+(?:st|nd|rd|th)$", re.IGNORECASE)
_VALE_REGEX_MARKERS = ("(?i)", "(?-i)", "\\b", "[", "(")


def terms_path(ctx: RepoContext) -> Path:
    return ctx.docs_quality_dir / "config" / "allowlists" / "terms.txt"


def canonical_casing_path(docs_quality_dir: Path) -> Path:
    return docs_quality_dir / "config" / "allowlists" / "canonical-casing.txt"


def read_canonical_casing(path: Path) -> dict[str, str]:
    """Map casefolded term -> preferred spelling (from canonical-casing.txt)."""
    if not path.is_file():
        return {}
    _, pairs = parse_canonical_casing_file(path)
    return {alias.casefold(): preferred for alias, preferred in pairs}


def _split_canonical_casing_line(stripped: str) -> tuple[str, str] | None:
    """Split a line into alias and preferred; both may contain spaces.

    Lines list the lowercase/CLI form first, then the prose form. For multi-word
    pairs (e.g. ``for example For example``), the word count is even and we split
    in half. Single-word pairs use the only valid split.
    """
    words = stripped.split()
    if len(words) < 2:
        return None
    if len(words) == 2:
        return words[0], words[1]
    if len(words) % 2 != 0:
        return None
    mid = len(words) // 2
    return " ".join(words[:mid]), " ".join(words[mid:])


def parse_canonical_casing_file(path: Path) -> tuple[list[str], list[tuple[str, str]]]:
    """Return (header comment lines, alias/preferred pairs) from canonical-casing.txt."""
    header: list[str] = []
    pairs: list[tuple[str, str]] = []
    in_header = True
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if in_header and (not stripped or stripped.startswith("#")):
            header.append(line.rstrip("\n"))
            continue
        in_header = False
        if not stripped or stripped.startswith("#"):
            continue
        split = _split_canonical_casing_line(stripped)
        if split is None:
            continue
        pairs.append(split)
    return header, pairs


def write_canonical_casing_file(
    path: Path,
    header: list[str],
    pairs: list[tuple[str, str]],
) -> bool:
    """Write canonical-casing.txt. Returns True if the file content changed."""
    merged: dict[str, tuple[str, str]] = {}
    for alias, preferred in pairs:
        merged[alias.casefold()] = (alias, preferred)
    body_lines = [
        f"{alias} {preferred}"
        for alias, preferred in sorted(
            merged.values(), key=lambda t: (t[1].casefold(), t[0].casefold())
        )
    ]
    body = "\n".join(body_lines) + ("\n" if body_lines else "")
    new_text = "\n".join(header) + ("\n" if header else "") + body
    if path.is_file() and path.read_text(encoding="utf-8") == new_text:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(new_text, encoding="utf-8")
    return True


def terms_case_pair_from_finding(finding: Finding) -> tuple[str, str] | None:
    """Return (alias, preferred) when a Vale.Terms message lists two casings."""
    match = _TERMS_USE_RE.search(finding.message)
    if not match:
        return None
    wanted = match.group(1).strip()
    found = match.group(2).strip()
    if wanted == found:
        return None
    preferred = _preferred_casing([wanted, found])
    alias = found if preferred == wanted else wanted
    return alias, preferred


def canonical_casing_covers_case_variants(
    casing: dict[str, str], a: str, b: str
) -> bool:
    """True when canonical-casing.txt already enables dual-valid casing for a/b."""
    if a == b or not casing:
        return False
    preferred = _preferred_casing([a, b])
    return _use_case_insensitive_vale_accept(preferred, casing)


def _are_case_variants(a: str, b: str) -> bool:
    return a.casefold() == b.casefold()


def _normalize_foreign_abbrev(term: str) -> str:
    """Collapse e.g./e.g., style variants to one terms.txt entry."""
    cleaned = term.strip()
    if re.fullmatch(r"e\.g\.?,?", cleaned, re.IGNORECASE):
        return "e.g."
    if re.fullmatch(r"i\.e\.?,?", cleaned, re.IGNORECASE):
        return "i.e."
    if cleaned.casefold().rstrip(",") == "viz.":
        return "viz."
    return cleaned


def foreign_latin_token_ignore(term: str) -> str | None:
    """TokenIgnores regex for Microsoft.Foreign / Google.Latin allowlist entries."""
    key = _normalize_foreign_abbrev(term).casefold().rstrip(",")
    return _FOREIGN_LATIN_IGNORES.get(key)


def google_ordinal_token_ignore(term: str) -> str | None:
    """TokenIgnores regex for Google.Ordinal when an ordinal is allowlisted in terms.txt."""
    cleaned = term.strip()
    if not _ORDINAL_TOKEN_RE.fullmatch(cleaned):
        return None
    return f"(?i)(\\b{re.escape(cleaned)}\\b)"


def google_ordinal_token_ignores(
    terms: list[str], *, casing: dict[str, str] | None = None
) -> list[str]:
    rules = casing if casing is not None else {}
    seen: set[str] = set()
    patterns: list[str] = []
    for term in normalize_terms(terms, casing=rules):
        pattern = google_ordinal_token_ignore(term)
        if pattern is None or pattern in seen:
            continue
        seen.add(pattern)
        patterns.append(pattern)
    return sorted(patterns, key=lambda s: s.casefold())


def foreign_latin_token_ignores(
    terms: list[str], *, casing: dict[str, str] | None = None
) -> list[str]:
    rules = casing if casing is not None else {}
    seen: set[str] = set()
    patterns: list[str] = []
    for term in normalize_terms(terms, casing=rules):
        pattern = foreign_latin_token_ignore(term)
        if pattern is None or pattern in seen:
            continue
        seen.add(pattern)
        patterns.append(pattern)
    return sorted(patterns, key=lambda s: s.casefold())


def vale_token_ignores(
    terms: list[str], *, casing: dict[str, str] | None = None
) -> list[str]:
    """All Vale TokenIgnores patterns derived from terms.txt."""
    rules = casing if casing is not None else {}
    seen: set[str] = set()
    merged: list[str] = []
    for pattern in (
        *microsoft_auto_token_ignores(terms, casing=rules),
        *foreign_latin_token_ignores(terms, casing=rules),
        *google_ordinal_token_ignores(terms, casing=rules),
    ):
        if pattern not in seen:
            seen.add(pattern)
            merged.append(pattern)
    return sorted(merged, key=lambda s: s.casefold())


def dual_casing_needed(ctx: RepoContext, finding: Finding) -> bool:
    """True when the finding needs a canonical-casing pair not yet on disk."""
    pair = terms_case_pair_from_finding(finding)
    if pair is None:
        return False
    if not _are_case_variants(pair[0], pair[1]):
        return False
    casing = allowlist_casing(ctx)
    return not canonical_casing_covers_case_variants(casing, pair[0], pair[1])


def ensure_canonical_casing_pair(
    ctx: RepoContext, alias: str, preferred: str
) -> bool:
    """Add alias→preferred to canonical-casing.txt if missing. Returns True if changed."""
    path = canonical_casing_path(ctx.docs_quality_dir)
    header: list[str] = []
    pairs: list[tuple[str, str]] = []
    if path.is_file():
        header, pairs = parse_canonical_casing_file(path)
    casing = {a.casefold(): p for a, p in pairs}
    if canonical_casing_covers_case_variants(casing, alias, preferred):
        return False
    if alias.casefold() in casing and casing[alias.casefold()].casefold() == preferred.casefold():
        return False
    pairs.append((alias, preferred))
    return write_canonical_casing_file(path, header, pairs)


def read_terms(path: Path) -> list[str]:
    lines = [
        ln.strip()
        for ln in path.read_text(encoding="utf-8").splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    ]
    return sorted(set(lines), key=lambda s: (s.casefold(), s))


def _is_vale_regex(term: str) -> bool:
    return any(marker in term for marker in _VALE_REGEX_MARKERS)


def _preferred_casing(variants: list[str]) -> str:
    """Pick one spelling when terms.txt has multiple case variants of the same word."""

    def score(word: str) -> tuple[int, int, str]:
        upper = sum(1 for ch in word if ch.isupper())
        return (upper, len(word), word)

    return max(variants, key=score)


def _group_terms(terms: list[str]) -> tuple[list[str], dict[str, list[str]]]:
    passthrough: list[str] = []
    groups: dict[str, list[str]] = {}
    for term in terms:
        if _is_vale_regex(term):
            passthrough.append(term)
            continue
        groups.setdefault(term.casefold(), []).append(term)
    return passthrough, groups


def _apply_canonical_casing(term: str, casing: dict[str, str]) -> str:
    if _is_vale_regex(term):
        return term
    return casing.get(term.casefold(), term)


def normalize_terms(
    terms: list[str], *, casing: dict[str, str] | None = None
) -> list[str]:
    """Dedupe terms.txt and apply canonical-casing.txt overrides."""
    passthrough, groups = _group_terms(terms)
    merged = passthrough + [_preferred_casing(v) for v in groups.values()]
    rules = casing if casing is not None else {}
    normalized = [_apply_canonical_casing(t, rules) for t in merged]
    return sorted(set(normalized), key=lambda s: (s.casefold(), s))


def dedupe_terms(terms: list[str]) -> list[str]:
    """Canonical terms.txt entries: drop exact dupes and merge case variants."""
    return normalize_terms(terms)


def canonical_casing_vale_accepts(
    pairs: list[tuple[str, str]],
) -> list[str]:
    """Vale accept.txt lines for canonical-casing.txt (dual-valid / alias forms)."""
    entries: list[str] = []
    seen: set[str] = set()
    for alias, preferred in pairs:
        if alias == preferred:
            token = preferred
        else:
            token = f"(?i){preferred}"
        key = token.casefold()
        if key in seen:
            continue
        seen.add(key)
        entries.append(token)
    return entries


def canonical_casing_covers_term(
    term: str, casing: dict[str, str]
) -> str | None:
    """Return preferred spelling when *term* matches canonical-casing.txt."""
    key = term.strip().casefold()
    if not key or not casing:
        return None
    for alias_fold, preferred in casing.items():
        if key == alias_fold or key == preferred.casefold():
            return preferred
    return None


def dictionary_entries(
    terms: list[str],
    *,
    casing_pairs: list[tuple[str, str]] | None = None,
) -> list[str]:
    """Plain-text dictionary lines (Harper): one preferred spelling per word."""
    extra: list[str] = []
    if casing_pairs:
        for alias, preferred in casing_pairs:
            extra.extend([alias, preferred])
    return dedupe_terms([*terms, *extra])


def _use_case_insensitive_vale_accept(term: str, casing: dict[str, str]) -> bool:
    """Terms listed in canonical-casing.txt accept any casing in docs (Vale.Terms)."""
    if not casing:
        return False
    key = term.casefold()
    keys = {k.casefold() for k in casing}
    values = {v.casefold() for v in casing.values()}
    return key in keys or key in values


def patterns_for_canonical_casing(casing: dict[str, str]) -> list[str]:
    """Typos extend-ignore-re patterns: one (?i)Preferred per canonical-casing entry."""
    preferred = sorted({v for v in casing.values()}, key=lambda s: (s.casefold(), s))
    return [f"(?i){p}" for p in preferred]


def merge_patterns(existing: list[str], *, casing: dict[str, str]) -> list[str]:
    """Merge manual patterns with auto-generated (?i)Preferred from canonical-casing."""
    required = patterns_for_canonical_casing(casing)
    return sorted(set(existing) | set(required), key=lambda s: (s.casefold(), s))


def parse_patterns_file(path: Path) -> tuple[list[str], list[str]]:
    """Return (header comment lines, pattern lines) from patterns.txt."""
    header: list[str] = []
    patterns: list[str] = []
    in_header = True
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if in_header and (not stripped or stripped.startswith("#")):
            header.append(line.rstrip("\n"))
            continue
        in_header = False
        if stripped and not stripped.startswith("#"):
            patterns.append(stripped)
    return header, patterns


def write_patterns_file(
    path: Path,
    header: list[str],
    patterns: list[str],
    *,
    casing: dict[str, str] | None = None,
) -> bool:
    """Write merged patterns to path. Returns True if the file content changed."""
    merged = merge_patterns(patterns, casing=casing or {})
    body = "\n".join(merged) + ("\n" if merged else "")
    new_text = "\n".join(header) + ("\n" if header else "") + body
    if path.is_file() and path.read_text(encoding="utf-8") == new_text:
        return False
    path.write_text(new_text, encoding="utf-8")
    return True


def microsoft_auto_token_ignore(term: str) -> str | None:
    """Vale TokenIgnores entry for Microsoft.Auto when *term* contains auto-."""
    cleaned = term.strip()
    if not cleaned or "auto-" not in cleaned.casefold():
        return None
    return f"(?i)(\\b{re.escape(cleaned)}\\b)"


def microsoft_auto_token_ignores(
    terms: list[str], *, casing: dict[str, str] | None = None
) -> list[str]:
    """TokenIgnores regexes synced to .vale.ini for allowlisted auto- hyphenation."""
    rules = casing if casing is not None else {}
    seen: set[str] = set()
    patterns: list[str] = []
    for term in normalize_terms(terms, casing=rules):
        pattern = microsoft_auto_token_ignore(term)
        if pattern is None or pattern in seen:
            continue
        seen.add(pattern)
        patterns.append(pattern)
    return sorted(patterns, key=lambda s: s.casefold())


def vale_accept_entries(
    terms: list[str],
    *,
    casing: dict[str, str] | None = None,
    casing_pairs: list[tuple[str, str]] | None = None,
) -> list[str]:
    """Vale accept.txt: terms.txt plus canonical-casing.txt alias/preferred forms."""
    rules = casing if casing is not None else {}
    passthrough, groups = _group_terms(terms)
    merged = list(passthrough)
    for variants in groups.values():
        if len(variants) > 1:
            base = _apply_canonical_casing(_preferred_casing(variants), rules)
            merged.append(f"(?i){base}")
            continue
        term = _apply_canonical_casing(variants[0], rules)
        if _use_case_insensitive_vale_accept(term, rules):
            merged.append(f"(?i){term}")
        else:
            merged.append(term)
    if casing_pairs:
        merged.extend(canonical_casing_vale_accepts(casing_pairs))
    return sorted(set(merged), key=lambda s: (s.casefold(), s))


def parse_terms_file(path: Path) -> tuple[list[str], list[str]]:
    """Return (header comment lines, term lines) from terms.txt."""
    header: list[str] = []
    terms: list[str] = []
    in_header = True
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if in_header and (not stripped or stripped.startswith("#")):
            header.append(line.rstrip("\n"))
            continue
        in_header = False
        if stripped and not stripped.startswith("#"):
            terms.append(stripped)
    return header, terms


def write_terms_file(
    path: Path,
    header: list[str],
    terms: list[str],
    *,
    casing: dict[str, str] | None = None,
) -> bool:
    """Write normalized terms to path. Returns True if the file content changed."""
    deduped = normalize_terms(terms, casing=casing)
    body = "\n".join(deduped) + ("\n" if deduped else "")
    new_text = "\n".join(header) + ("\n" if header else "") + body
    if path.is_file() and path.read_text(encoding="utf-8") == new_text:
        return False
    path.write_text(new_text, encoding="utf-8")
    return True


_CONTRACTION_RULES = frozenset(
    {
        "PwnPatterns.Contractions",
        "Google.Contractions",
        "Microsoft.Contractions",
    }
)

# Vale substitution rules: message suggests a replacement; allowlist the source phrase.
_SUBSTITUTION_SOURCE_RULES = frozenset(
    {
        "Microsoft.Foreign",
        "Google.Latin",
    }
)

# Use \x2c for comma: TokenIgnores in .vale.ini is comma-separated.
_FOREIGN_LATIN_IGNORES: dict[str, str] = {
    "e.g.": r"(?i)(\b(?:e\.g\.|eg)[\s\x2c])",
    "eg": r"(?i)(\b(?:e\.g\.|eg)[\s\x2c])",
    "i.e.": r"(?i)(\b(?:i\.e\.|ie)[\s\x2c])",
    "ie": r"(?i)(\b(?:i\.e\.|ie)[\s\x2c])",
    "viz.": r"(?i)(\bviz\.[\s\x2c])",
    "ergo": r"(?i)(\berg[\s\x2c])",
}


def extract_allowlist_term(
    finding: Finding, *, casing: dict[str, str] | None = None
) -> str | None:
    """Return a vocabulary term to add to terms.txt, if this finding supports it."""
    rules = casing if casing is not None else {}
    if finding.rule in _CONTRACTION_RULES:
        return None
    if finding.tool != "vale":
        if finding.tool == "typos":
            match = _TYPO_RE.search(finding.message)
            if match:
                return match.group(1).strip()
        return None

    match = _SPELLING_RE.search(finding.message)
    if match:
        return _apply_canonical_casing(match.group(1).strip(), rules)
    match = _TERMS_USE_RE.search(finding.message)
    if match:
        suggested = match.group(1).strip()
        source = match.group(2).strip()
        if finding.rule in _SUBSTITUTION_SOURCE_RULES:
            term = _normalize_foreign_abbrev(source)
            return _apply_canonical_casing(term, rules)
        if _are_case_variants(suggested, source):
            return _apply_canonical_casing(_preferred_casing([suggested, source]), rules)
        return None
    match = _MICROSOFT_AUTO_RE.search(finding.message)
    if match:
        return _apply_canonical_casing(match.group(1).strip(), rules)
    match = _GOOGLE_ORDINAL_RE.search(finding.message)
    if match:
        return match.group(1).strip()
    return None


def allowlist_hint(
    finding: Finding, *, casing: dict[str, str] | None = None
) -> str | None:
    """Short explanation when allowlist is not available, or None if allowlist applies."""
    term = extract_allowlist_term(finding, casing=casing)
    if term is not None:
        return None
    if finding.tool == "vale" and _TERMS_USE_RE.search(finding.message):
        return (
            "Vale Terms style rules are not allowlisted here. "
            "Fix the wording in the doc, or add terms in "
            "config/allowlists/terms.txt and sync."
        )
    if finding.tool == "harper":
        return "Harper findings use harper.ignore-rules, not terms.txt."
    return (
        "This Vale rule is not allowlisted from the TUI. "
        "Edit terms.txt or harper.ignore-rules manually."
    )


def can_allowlist(finding: Finding, *, casing: dict[str, str] | None = None) -> bool:
    return extract_allowlist_term(finding, casing=casing) is not None


def allowlist_casing(ctx: RepoContext) -> dict[str, str]:
    return read_canonical_casing(canonical_casing_path(ctx.docs_quality_dir))


def normalized_allowlist_terms(
    raw_terms: list[str], *, casing: dict[str, str] | None = None
) -> list[str]:
    return normalize_terms(raw_terms, casing=casing or {})


def find_allowlisted_match(
    term: str, existing: list[str], *, casing: dict[str, str] | None = None
) -> str | None:
    """Return the normalized allowlist entry for *term*, if already covered."""
    key = _apply_canonical_casing(term.strip(), casing or {}).casefold()
    for entry in existing:
        if entry.casefold() == key:
            return entry
    return None


def term_allowlist_status(ctx: RepoContext, term: str) -> str | None:
    """If *term* is already on the normalized allowlist, return that entry."""
    casing = allowlist_casing(ctx)
    via_casing = canonical_casing_covers_term(term, casing)
    path = terms_path(ctx)
    if path.is_file():
        existing = normalized_allowlist_terms(read_terms(path), casing=casing)
        match = find_allowlisted_match(term, existing, casing=casing)
        if match is not None:
            return match
    return via_casing


def without_allowlisted_term(
    findings: list[Finding],
    term: str,
    *,
    existing_allowlist: list[str] | None = None,
    casing: dict[str, str] | None = None,
) -> list[Finding]:
    """Drop findings whose extracted allowlist term matches *term* (case-insensitive)."""
    keys = {term.casefold()}
    if existing_allowlist:
        keys.update(t.casefold() for t in existing_allowlist)

    def keep(finding: Finding) -> bool:
        extracted = extract_allowlist_term(finding, casing=casing)
        if extracted is None:
            return True
        return extracted.casefold() not in keys

    return [f for f in findings if keep(f)]


def _append_dual_casing_note(msg: str, *, casing_changed: bool) -> str:
    if casing_changed:
        return f"{msg}; enabled dual-valid casing in canonical-casing.txt"
    return msg


def add_term(
    ctx: RepoContext, term: str, *, finding: Finding | None = None
) -> tuple[bool, str]:
    """Add or merge *term* into terms.txt; update canonical-casing when needed."""
    cleaned = term.strip()
    if not cleaned:
        return False, "No term to add"

    path = terms_path(ctx)
    if not path.is_file():
        return False, f"Missing allowlist file: {path}"

    casing = allowlist_casing(ctx)
    header, raw = parse_terms_file(path)
    existing = normalized_allowlist_terms(raw, casing=casing)
    canonical = _apply_canonical_casing(cleaned, casing)
    match = find_allowlisted_match(cleaned, existing, casing=casing)
    pair = terms_case_pair_from_finding(finding) if finding else None

    def finish(ok: bool, message: str) -> tuple[bool, str]:
        if not ok or pair is None:
            return ok, message
        alias, preferred = pair
        changed = ensure_canonical_casing_pair(ctx, alias, preferred)
        return ok, _append_dual_casing_note(message, casing_changed=changed)

    if match is not None:
        preferred = _preferred_casing([match, canonical])
        key = cleaned.casefold()
        updated_raw = [t for t in raw if t.casefold() != key]
        if not any(t.casefold() == preferred.casefold() for t in updated_raw):
            updated_raw.append(preferred)
        changed = write_terms_file(path, header, updated_raw, casing=casing)
        if preferred != match:
            return finish(
                True, f"Updated allowlist spelling to '{preferred}' (was '{match}')"
            )
        if changed:
            return finish(True, f"Normalized allowlist entry to '{preferred}'")
        return finish(True, f"'{cleaned}' already allowlisted as '{preferred}'")

    write_terms_file(path, header, [*raw, canonical], casing=casing)
    stored = find_allowlisted_match(
        canonical,
        normalized_allowlist_terms(read_terms(path), casing=casing),
        casing=casing,
    )
    label = stored or canonical
    return finish(True, f"Added '{label}' to {path.name}")


def sync_allowlists(ctx: RepoContext) -> int:
    """Regenerate Vale accept, Harper dict, and typos blocks from terms.txt."""
    return maintenance.run_sync(ctx)
