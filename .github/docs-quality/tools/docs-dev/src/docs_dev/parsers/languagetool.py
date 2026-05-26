"""Parse languagetool.json batch output into Finding objects."""

from __future__ import annotations

import json
from pathlib import Path

from docs_dev.models import Finding

BLOCKING_ISSUE_TYPES = frozenset({"misspelling", "grammar"})


def matched_text_from_match(match: dict) -> str:
    """Highlighted token within LanguageTool context (not the full context snippet)."""
    ctx = match.get("context") or {}
    text = str(ctx.get("text") or "")
    off = int(ctx.get("offset") or 0)
    length = int(ctx.get("length") or 0)
    if text and length > 0:
        return text[off : off + length].strip()
    return text.strip()


def _context_snippet(text: str, *, limit: int = 96) -> str:
    stripped = text.strip()
    if len(stripped) <= limit:
        return stripped
    return stripped[: limit - 1] + "…"


def format_match_message(match: dict) -> str:
    """Align with automation/filters/lib/languagetool-message.jq (reviewdog + TUI)."""
    rule = match.get("rule") or {}
    rule_id = str(rule.get("id") or rule.get("ruleId") or "?")
    issue_type = str(rule.get("issueType") or (match.get("type") or {}).get("typeName") or "")
    base = str(match.get("message") or "grammar/spelling issue")
    parts = [f"[languagetool] {rule_id}: {base}"]
    if issue_type:
        parts.append(f"Type: {issue_type}")
    if str(issue_type).lower() == "misspelling":
        token = matched_text_from_match(match)
        if token:
            parts.append(f"Matched: «{token}»")
    else:
        ctx_text = str((match.get("context") or {}).get("text") or "")
        if ctx_text.strip():
            parts.append(f"In text: «{_context_snippet(ctx_text)}»")
    replacements = match.get("replacements") or []
    if replacements:
        suggestion = str(replacements[0].get("value") or "")
        if suggestion:
            parts.append(f"Suggestion: «{suggestion}»")
    return " — ".join(parts)


def parse_file(path: Path) -> list[Finding]:
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []

    findings: list[Finding] = []
    for entry in data:
        file_path = str(entry.get("file") or "")
        for match in entry.get("matches") or []:
            rule = match.get("rule") or {}
            issue_type = str(rule.get("issueType") or "").lower()
            blocking = issue_type in BLOCKING_ISSUE_TYPES
            token = matched_text_from_match(match) if issue_type == "misspelling" else None
            findings.append(
                Finding(
                    path=file_path,
                    line=int(match.get("line") or 1),
                    column=int(match.get("column") or 1),
                    tool="languagetool",
                    rule=str(rule.get("id") or "languagetool"),
                    message=format_match_message(match),
                    severity="error" if blocking else "warning",
                    matched_text=token or None,
                )
            )
    return findings
