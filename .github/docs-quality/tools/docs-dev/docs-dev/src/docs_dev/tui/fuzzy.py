"""Lightweight fuzzy matching for TUI file filters (no extra dependencies)."""

from __future__ import annotations

from pathlib import Path

from docs_dev.models import FileFindings
from docs_dev.tui.paths import display_path


def _subsequence_score(needle: str, haystack: str) -> float | None:
    """Score how well *needle* matches as a subsequence of *haystack* (casefolded)."""
    if not needle:
        return 1.0
    if needle in haystack:
        return 1.0 + len(needle) / max(len(haystack), 1)

    positions: list[int] = []
    start = 0
    for ch in needle:
        idx = haystack.find(ch, start)
        if idx < 0:
            return None
        positions.append(idx)
        start = idx + 1

    gaps = sum(
        positions[i + 1] - positions[i] - 1 for i in range(len(positions) - 1)
    )
    contiguous = all(
        positions[i + 1] == positions[i] + 1 for i in range(len(positions) - 1)
    )
    tightness = 1.0 / (1 + gaps)
    bonus = 0.4 if contiguous else 0.0
    return tightness + bonus


def fuzzy_score(query: str, target: str) -> float | None:
    """Return a match score (higher is better), or None if *query* does not match."""
    q = query.strip().casefold()
    if not q:
        return 0.0
    hay = target.casefold()
    tokens = q.split()
    scores: list[float] = []
    for token in tokens:
        s = _subsequence_score(token, hay)
        if s is None:
            return None
        scores.append(s)
    return sum(scores) / len(scores)


def file_search_haystacks(path: str, repo_root: Path | None) -> list[str]:
    """Strings to match against when filtering the files table."""
    label = display_path(path, repo_root)
    stem = Path(path).stem
    return [path, label, stem.replace("_", " ")]


def filter_file_findings(
    files: list[FileFindings],
    query: str,
    *,
    repo_root: Path | None = None,
) -> list[FileFindings]:
    """Return files best matching *query*, sorted by relevance then issue count."""
    q = query.strip()
    if not q:
        return list(files)

    scored: list[tuple[float, FileFindings]] = []
    for ff in files:
        best = max(
            (fuzzy_score(q, hay) or -1.0 for hay in file_search_haystacks(ff.path, repo_root)),
            default=-1.0,
        )
        if best >= 0:
            scored.append((best, ff))

    scored.sort(key=lambda item: (-item[0], -item[1].count, item[1].path))
    return [ff for _, ff in scored]
