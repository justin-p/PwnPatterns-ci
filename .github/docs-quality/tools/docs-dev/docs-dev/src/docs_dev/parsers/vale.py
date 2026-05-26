from __future__ import annotations

import json
from pathlib import Path

from docs_dev.models import Finding
from docs_dev.vale_fix import CONTRACTIONS_CHECK


def _fixable(item: dict) -> bool:
    if str(item.get("Check") or "") != CONTRACTIONS_CHECK:
        return False
    action = item.get("Action")
    if not isinstance(action, dict):
        return False
    if (action.get("Name") or "").lower() != "replace":
        return False
    params = action.get("Params")
    return isinstance(params, list) and bool(params)


def parse_file(path: Path) -> list[Finding]:
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return []
    data = json.loads(raw)
    if not isinstance(data, dict):
        return []
    seen: set[tuple[str, int, str, str]] = set()
    findings: list[Finding] = []
    for file_path, items in data.items():
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            if (item.get("Severity") or "").lower() != "error":
                continue
            line = int(item.get("Line") or 1)
            check = str(item.get("Check") or "vale")
            msg = str(item.get("Message") or "")
            span = item.get("Span")
            column = int(span[0]) if isinstance(span, list) and span else 1
            key = (file_path, line, check, msg)
            if key in seen:
                continue
            seen.add(key)
            findings.append(
                Finding(
                    tool="vale",
                    path=file_path,
                    line=line,
                    column=column,
                    severity="error",
                    message=msg,
                    rule=check,
                    fixable=_fixable(item),
                )
            )
    return findings
