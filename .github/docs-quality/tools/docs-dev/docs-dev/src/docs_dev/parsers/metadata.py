from __future__ import annotations

import json
from pathlib import Path

from docs_dev.models import Finding


def parse_file(path: Path) -> list[Finding]:
    findings: list[Finding] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s:
            continue
        try:
            item = json.loads(s)
        except json.JSONDecodeError:
            continue
        loc = item.get("location") or {}
        rng = (loc.get("range") or {}).get("start") or {}
        findings.append(
            Finding(
                tool="metadata",
                path=str(loc.get("path") or ""),
                line=int(rng.get("line") or 1),
                column=int(rng.get("column") or 1),
                severity="error",
                message=str(item.get("message") or ""),
            )
        )
    return findings
