from __future__ import annotations

import json
from pathlib import Path

from docs_dev.models import Finding


def _link_message(body: dict) -> str:
    url = body.get("url") or body.get("uri") or "unknown URL"
    status = body.get("status") or {}
    text = status.get("text") or status.get("details") or "link check failed"
    return f"{url}: {text}"


def parse_report(path: Path) -> list[Finding]:
    data = json.loads(path.read_text(encoding="utf-8"))
    findings: list[Finding] = []
    for key in ("error_map", "fail_map", "timeout_map"):
        block = data.get(key) or {}
        if not isinstance(block, dict):
            continue
        for file_path, bodies in block.items():
            if not isinstance(bodies, list):
                bodies = [bodies]
            for body in bodies:
                if not isinstance(body, dict):
                    continue
                span = body.get("span") or {}
                findings.append(
                    Finding(
                        tool="lychee",
                        path=str(file_path),
                        line=int(span.get("line") or 1),
                        column=int(span.get("column") or 1),
                        severity="error",
                        message=_link_message(body),
                    )
                )
    return findings
