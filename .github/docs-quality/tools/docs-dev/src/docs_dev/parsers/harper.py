from __future__ import annotations

import json
from pathlib import Path

from docs_dev.models import Finding

BLOCKING_PRIORITY = 127


def _basename_index(paths: list[str]) -> dict[str, str]:
    index: dict[str, str] = {}
    for p in paths:
        index[Path(p).name] = p
    return index


def parse_file(path: Path, lint_paths: list[str]) -> list[Finding]:
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return []
    data = json.loads(raw)
    if not isinstance(data, list):
        return []
    index = _basename_index(lint_paths)
    findings: list[Finding] = []
    for entry in data:
        if not isinstance(entry, dict):
            continue
        base = str(entry.get("file") or "")
        full = index.get(base, base)
        for lint in entry.get("lints") or []:
            if not isinstance(lint, dict):
                continue
            if int(lint.get("priority") or 0) < BLOCKING_PRIORITY:
                continue
            findings.append(
                Finding(
                    tool="harper",
                    path=full,
                    line=int(lint.get("line") or 1),
                    column=int(lint.get("column") or 1),
                    severity="error",
                    message=str(lint.get("message") or "Harper lint"),
                    rule=str(lint.get("rule") or ""),
                )
            )
    return findings
