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
        if item.get("type") != "typo":
            continue
        corrections = item.get("corrections") or []
        fix = corrections[0] if corrections else "?"
        findings.append(
            Finding(
                tool="typos",
                path=str(item.get("path") or ""),
                line=int(item.get("line_num") or 1),
                column=1,
                severity="error",
                message=f"typo `{item.get('typo')}` → {fix}",
                fixable=True,
            )
        )
    return findings
