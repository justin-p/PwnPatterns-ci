"""Read consumer allowlists and filter LanguageTool matches."""

from __future__ import annotations

from pathlib import Path


def _split_canonical_casing_line(stripped: str) -> tuple[str, str] | None:
    words = stripped.split()
    if len(words) < 2:
        return None
    if len(words) == 2:
        return words[0], words[1]
    if len(words) % 2 != 0:
        return None
    mid = len(words) // 2
    return " ".join(words[:mid]), " ".join(words[mid:])


def read_terms_file(path: Path) -> set[str]:
    if not path.is_file():
        return set()
    out: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            out.add(stripped.casefold())
    return out


def read_canonical_casing(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    casing: dict[str, str] = {}
    in_header = True
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if in_header and (not stripped or stripped.startswith("#")):
            continue
        in_header = False
        if not stripped or stripped.startswith("#"):
            continue
        split = _split_canonical_casing_line(stripped)
        if split is None:
            continue
        alias, preferred = split
        casing[alias.casefold()] = preferred
    return casing


def load_consumer_allowlists(repo_root: Path) -> tuple[set[str], dict[str, str]]:
    cfg = repo_root / ".github/docs-quality/config/allowlists"
    return (
        read_terms_file(cfg / "terms.txt"),
        read_canonical_casing(cfg / "canonical-casing.txt"),
    )


def token_allowlisted(token: str, terms: set[str], casing: dict[str, str]) -> bool:
    cleaned = token.strip()
    if not cleaned:
        return False
    key = cleaned.casefold()
    if key in terms:
        return True
    if key in casing or key in {v.casefold() for v in casing.values()}:
        return True
    return False


def languagetool_matched_text(match: dict) -> str:
    """Token LanguageTool flagged within context.text (offset/length), not the whole snippet."""
    ctx = match.get("context") or {}
    text = str(ctx.get("text") or "")
    off = int(ctx.get("offset") or 0)
    length = int(ctx.get("length") or 0)
    if text and length > 0:
        return text[off : off + length].strip()
    return text.strip()


def languagetool_match_allowlisted(
    match: dict,
    terms: set[str],
    casing: dict[str, str],
) -> bool:
    token = languagetool_matched_text(match)
    return bool(token and token_allowlisted(token, terms, casing))


def filter_languagetool_matches(
    matches: list[dict],
    terms: set[str],
    casing: dict[str, str],
) -> list[dict]:
    if not terms and not casing:
        return matches
    return [m for m in matches if not languagetool_match_allowlisted(m, terms, casing)]
