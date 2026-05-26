"""Parse languagetool.json batch output into Finding objects."""

from __future__ import annotations

import json
from pathlib import Path

from docs_dev.models import Finding

BLOCKING_ISSUE_TYPES = frozenset({"misspelling", "grammar"})


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
            priority = 127 if issue_type in BLOCKING_ISSUE_TYPES else 64
            findings.append(
                Finding(
                    path=file_path,
                    line=int(match.get("line") or 1),
                    column=int(match.get("column") or 1),
                    tool="languagetool",
                    rule=str(rule.get("id") or "languagetool"),
                    message=str(match.get("message") or "LanguageTool issue"),
                    severity="error" if priority >= 127 else "warning",
                    priority=priority,
                )
            )
    return findings
