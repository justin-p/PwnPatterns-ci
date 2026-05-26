"""Detect and fix contractions in ```YAML [list] template blocks (Vale skips fenced code)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from docs_dev.models import Finding
from docs_dev.vale_fix import CONTRACTIONS_CHECK, ValeLineFix, apply_vale_line_fixes

YAML_LIST_BLOCK = re.compile(r"```YAML\s*\n(\[list\][\s\S]*?)\n```", re.MULTILINE)

# Mirrors styles/PwnPatterns/Contractions.yml (word-boundary / it's. exceptions).
_CONTRACTION_RULES: list[tuple[re.Pattern[str], str, str]] = [
    (re.compile(r"\baren't\b", re.I), "are not", "aren't"),
    (re.compile(r"\bcan't\b", re.I), "cannot", "can't"),
    (re.compile(r"\bcouldn't\b", re.I), "could not", "couldn't"),
    (re.compile(r"\bdidn't\b", re.I), "did not", "didn't"),
    (re.compile(r"\bdon't\b", re.I), "do not", "don't"),
    (re.compile(r"\bdoesn't\b", re.I), "does not", "doesn't"),
    (re.compile(r"\bhasn't\b", re.I), "has not", "hasn't"),
    (re.compile(r"\bhaven't\b", re.I), "have not", "haven't"),
    (re.compile(r"\bhow's\b", re.I), "how is", "how's"),
    (re.compile(r"\bisn't\b", re.I), "is not", "isn't"),
    (re.compile(r"\bshouldn't\b", re.I), "should not", "shouldn't"),
    (re.compile(r"\bwasn't\b", re.I), "was not", "wasn't"),
    (re.compile(r"\bweren't\b", re.I), "were not", "weren't"),
    (re.compile(r"\bwon't\b", re.I), "will not", "won't"),
    (re.compile(r"(?i)\bit's(?!\.)"), "it is", "it's"),
    (re.compile(r"(?i)\bthat's(?![.,])"), "that is", "that's"),
    (re.compile(r"(?i)\bthey're(?!\.)"), "they are", "they're"),
    (re.compile(r"(?i)\bwe're(?!\.)"), "we are", "we're"),
    (re.compile(r"(?i)\bwe've(?!\.)"), "we have", "we've"),
    (re.compile(r"(?i)\bwhat's(?!\.)"), "what is", "what's"),
    (re.compile(r"(?i)\bwhen's(?!\.)"), "when is", "when's"),
    (re.compile(r"(?i)\bwhere's(?!\.)"), "where is", "where's"),
]


@dataclass(frozen=True)
class _TemplateHit:
    path: str
    line: int
    span_start: int
    span_end: int
    match: str
    replacement: str


def _line_number(text: str, index: int) -> int:
    return text[:index].count("\n") + 1


def _scan_block(
    rel_path: str,
    file_text: str,
    block_start: int,
    block_body: str,
) -> list[_TemplateHit]:
    hits: list[_TemplateHit] = []
    for offset, line in enumerate(block_body.splitlines()):
        if not line.startswith("[*]"):
            continue
        for pattern, replacement, label in _CONTRACTION_RULES:
            for match in pattern.finditer(line):
                line_no = _line_number(file_text, block_start) + offset
                hits.append(
                    _TemplateHit(
                        path=rel_path,
                        line=line_no,
                        span_start=match.start() + 1,
                        span_end=match.end(),
                        match=match.group(0),
                        replacement=replacement,
                    )
                )
    return hits


def scan_file(repo_root: Path, rel_path: str) -> list[Finding]:
    path = repo_root / rel_path
    if not path.is_file():
        return []
    text = path.read_text(encoding="utf-8")
    findings: list[Finding] = []
    for block in YAML_LIST_BLOCK.finditer(text):
        for hit in _scan_block(rel_path, text, block.start(1), block.group(1)):
            findings.append(
                Finding(
                    tool="vale",
                    path=hit.path,
                    line=hit.line,
                    column=hit.span_start,
                    severity="error",
                    message=f"Use '{hit.replacement}' instead of '{hit.match}'.",
                    rule=CONTRACTIONS_CHECK,
                    fixable=True,
                )
            )
    return findings


def scan_paths(repo_root: Path, paths: list[str]) -> list[Finding]:
    out: list[Finding] = []
    for rel in paths:
        if rel.endswith(".md"):
            out.extend(scan_file(repo_root, rel))
    return out


def hits_to_vale_alerts(hits: list[_TemplateHit]) -> dict[str, list[dict]]:
    by_path: dict[str, list[dict]] = {}
    for hit in hits:
        by_path.setdefault(hit.path, []).append(
            {
                "Severity": "error",
                "Check": CONTRACTIONS_CHECK,
                "Message": f"Use '{hit.replacement}' instead of '{hit.match}'.",
                "Line": hit.line,
                "Span": [hit.span_start, hit.span_end],
                "Match": hit.match,
                "Action": {"Name": "replace", "Params": [hit.replacement]},
            }
        )
    return by_path


def merge_into_vale_json(repo_root: Path, paths: list[str], vale_json: Path) -> bool:
    """Append template-list contraction alerts to *vale_json*. Return True if any errors."""
    hits: list[_TemplateHit] = []
    for rel in paths:
        if not rel.endswith(".md"):
            continue
        path = repo_root / rel
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        for block in YAML_LIST_BLOCK.finditer(text):
            hits.extend(_scan_block(rel, text, block.start(1), block.group(1)))

    data: dict = {}
    if vale_json.is_file():
        raw = vale_json.read_text(encoding="utf-8").strip()
        if raw:
            try:
                loaded = json.loads(raw)
            except json.JSONDecodeError:
                loaded = None
            if isinstance(loaded, dict):
                data = loaded

    for file_path, alerts in hits_to_vale_alerts(hits).items():
        existing = data.setdefault(file_path, [])
        if not isinstance(existing, list):
            existing = []
            data[file_path] = existing
        existing.extend(alerts)

    vale_json.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return bool(hits)


def apply_fixes(repo_root: Path, paths: list[str]) -> int:
    fixes: list[ValeLineFix] = []
    for rel in paths:
        if not rel.endswith(".md"):
            continue
        path = repo_root / rel
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        for block in YAML_LIST_BLOCK.finditer(text):
            for hit in _scan_block(rel, text, block.start(1), block.group(1)):
                fixes.append(
                    ValeLineFix(
                        path=hit.path,
                        line=hit.line,
                        span_start=hit.span_start,
                        span_end=hit.span_end,
                        replacement=hit.replacement,
                    )
                )
    return apply_vale_line_fixes(repo_root, fixes)
