"""Apply Vale ``replace`` actions (PwnPatterns.Contractions) from ``vale --output=JSON``."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

CONTRACTIONS_CHECK = "PwnPatterns.Contractions"


@dataclass(frozen=True)
class ValeLineFix:
    path: str
    line: int
    span_start: int
    span_end: int
    replacement: str


def load_vale_json(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def collect_contraction_fixes(
    data: dict,
    *,
    check: str = CONTRACTIONS_CHECK,
) -> list[ValeLineFix]:
    fixes: list[ValeLineFix] = []
    for file_path, items in data.items():
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            if (item.get("Severity") or "").lower() != "error":
                continue
            if str(item.get("Check") or "") != check:
                continue
            action = item.get("Action")
            if not isinstance(action, dict):
                continue
            if (action.get("Name") or "").lower() != "replace":
                continue
            params = action.get("Params")
            if not isinstance(params, list) or not params:
                continue
            span = item.get("Span")
            if not isinstance(span, list) or len(span) < 2:
                continue
            line = int(item.get("Line") or 1)
            start, end = int(span[0]), int(span[1])
            fixes.append(
                ValeLineFix(
                    path=file_path,
                    line=line,
                    span_start=start,
                    span_end=end,
                    replacement=str(params[0]),
                )
            )
    return fixes


def apply_vale_line_fixes(repo_root: Path, fixes: list[ValeLineFix]) -> int:
    """Apply fixes in-place. Returns number of substitutions applied."""
    if not fixes:
        return 0
    by_path: dict[str, list[ValeLineFix]] = {}
    for fix in fixes:
        by_path.setdefault(fix.path, []).append(fix)

    applied = 0
    for rel_path, file_fixes in by_path.items():
        path = repo_root / rel_path
        if not path.is_file():
            continue
        raw = path.read_text(encoding="utf-8")
        ends_with_nl = raw.endswith("\n")
        lines = raw.splitlines()
        by_line: dict[int, list[ValeLineFix]] = {}
        for fix in file_fixes:
            by_line.setdefault(fix.line, []).append(fix)

        for line_no, line_fixes in by_line.items():
            if line_no < 1 or line_no > len(lines):
                continue
            line = lines[line_no - 1]
            for fix in sorted(line_fixes, key=lambda f: f.span_start, reverse=True):
                start = fix.span_start - 1
                end = fix.span_end
                if start < 0 or end <= start or end > len(line):
                    continue
                line = line[:start] + fix.replacement + line[end:]
                applied += 1
            lines[line_no - 1] = line

        new_content = "\n".join(lines)
        if ends_with_nl:
            new_content += "\n"
        path.write_text(new_content, encoding="utf-8")
    return applied
