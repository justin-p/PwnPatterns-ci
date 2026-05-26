from __future__ import annotations

import json
import re
from pathlib import Path

from docs_dev.models import Finding

_SPELLING_MSG_RE = re.compile(r"^(.+?) -> ")


def parse_file(path: Path) -> list[Finding]:
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return []
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(payload, list):
        return []
    findings: list[Finding] = []
    for entry in payload:
        if not isinstance(entry, dict):
            continue
        file_path = str(entry.get("filePath") or "")
        for msg in entry.get("messages") or []:
            if not isinstance(msg, dict):
                continue
            rule = str(msg.get("ruleId") or "textlint")
            message = str(msg.get("message") or "textlint issue")
            fix = msg.get("fix") or {}
            fix_text = fix.get("text") if isinstance(fix, dict) else None
            if fix_text:
                message = f"{message} (suggested: {fix_text})"
            findings.append(
                Finding(
                    tool="textlint",
                    path=file_path,
                    line=int(msg.get("line") or 1),
                    column=int(msg.get("column") or 1),
                    severity="error",
                    message=message,
                    rule=rule,
                    fixable=bool(fix_text),
                )
            )
    return findings


def spelling_word(message: str) -> str | None:
    match = _SPELLING_MSG_RE.match(message.strip())
    return match.group(1).strip() if match else None
