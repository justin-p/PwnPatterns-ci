from __future__ import annotations

import json
from pathlib import Path

from docs_dev.models import Finding


def parse_file(path: Path) -> list[Finding]:
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return []
    data = json.loads(raw)
    if not isinstance(data, list):
        return []
    findings: list[Finding] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        findings.append(
            Finding(
                tool="rumdl",
                path=str(item.get("file") or ""),
                line=int(item.get("line") or 1),
                column=int(item.get("column") or 1),
                severity=str(item.get("severity") or "warning"),
                message=str(item.get("message") or "issue"),
                rule=str(item.get("rule") or "rumdl"),
                fixable=True,
            )
        )
    return findings
