"""Convert prose linter JSON logs to rdjsonl lines."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Iterator

from pwnpatterns_ci.paths_util import build_path_index, load_path_index, resolve_path
from pwnpatterns_ci.rdjsonl import messages as msg


def _range(line: int, start_col: int, end_col: int | None = None) -> dict:
    end = end_col if end_col is not None else start_col
    return {
        "start": {"line": line, "column": start_col},
        "end": {"line": line, "column": end},
    }


def _emit(diagnostic: dict) -> str:
    return json.dumps(diagnostic, ensure_ascii=False)


def _repo_root() -> str:
    return os.environ.get("GITHUB_WORKSPACE") or os.environ.get("REPO_ROOT") or ""


def convert_vale(data: dict, path_index: dict[str, str]) -> Iterator[str]:
    root = _repo_root()
    for raw_path, alerts in data.items():
        path = resolve_path(raw_path, path_index, repo_root=root)
        for alert in alerts or []:
            if (alert.get("Severity") or "").lower() != "error":
                continue
            line = alert.get("Line") or 1
            start_col = alert.get("Span", [1])[0] if alert.get("Span") else 1
            end_col = (alert.get("Span", [0, 0])[1] if len(alert.get("Span", [])) > 1 else 0) + 1
            action = alert.get("Action") or {}
            params = action.get("Params") or []
            suggestions: list[dict] = []
            if (action.get("Name") or "").lower() == "replace" and params:
                suggestions = [
                    {
                        "range": _range(line, start_col, end_col),
                        "text": params[0],
                    }
                ]
            yield _emit(
                {
                    "message": msg.vale_message(alert),
                    "location": {"path": path, "range": _range(line, start_col, end_col)},
                    "suggestions": suggestions,
                    "severity": "ERROR",
                }
            )


def convert_typos(records: list[dict], path_index: dict[str, str]) -> Iterator[str]:
    root = _repo_root()
    for rec in records:
        if rec.get("type") != "typo":
            continue
        path = resolve_path(rec.get("path") or "", path_index, repo_root=root)
        if not path:
            continue
        line = rec.get("line_num") or 1
        start_col = (rec.get("byte_offset") or 0) + 1
        typo = rec.get("typo") or ""
        end_col = start_col + len(typo)
        corrections = rec.get("corrections") or []
        suggestions: list[dict] = []
        if corrections:
            suggestions = [
                {"range": _range(line, start_col, end_col), "text": corrections[0]}
            ]
        yield _emit(
            {
                "message": msg.typos_message(rec),
                "location": {"path": path, "range": _range(line, start_col, end_col)},
                "suggestions": suggestions,
                "severity": "ERROR",
            }
        )


def convert_textlint(data: list, path_index: dict[str, str]) -> Iterator[str]:
    root = _repo_root()
    for file_rec in data:
        raw = file_rec.get("filePath") or ""
        path = resolve_path(raw, path_index, repo_root=root)
        for m in file_rec.get("messages") or []:
            line = m.get("line") or 1
            col = m.get("column") or 1
            fix = m.get("fix") or {}
            fr = fix.get("range") or [col, col]
            end_col = (fr[1] if len(fr) > 1 else fr[0]) if fr else col + 1
            span = max(1, (end_col - (fr[0] if fr else col)) or 1)
            suggestions: list[dict] = []
            if fix.get("text"):
                suggestions = [
                    {"range": _range(line, col, col + span), "text": fix["text"]}
                ]
            yield _emit(
                {
                    "message": msg.textlint_message(m),
                    "location": {"path": path, "range": _range(line, col, col + span)},
                    "suggestions": suggestions,
                    "severity": "ERROR",
                }
            )


def convert_rumdl(data: list, path_index: dict[str, str]) -> Iterator[str]:
    root = _repo_root()
    for diag in data:
        path = resolve_path(diag.get("file") or "", path_index, repo_root=root)
        if not path:
            continue
        line = diag.get("line") or 1
        col = diag.get("column") or 1
        sev = "ERROR" if diag.get("severity") == "error" else "WARNING"
        yield _emit(
            {
                "message": msg.rumdl_message(diag),
                "location": {
                    "path": path,
                    "range": {"start": {"line": line, "column": col}},
                },
                "severity": sev,
            }
        )


def convert_harper(data: list, path_index: dict[str, str], blocking: int) -> Iterator[str]:
    root = _repo_root()
    for file_rec in data:
        base = file_rec.get("file") or ""
        path = resolve_path(base, path_index, repo_root=root)
        for lint in file_rec.get("lints") or []:
            if (lint.get("priority") or 0) < blocking:
                continue
            line = lint.get("line") or 1
            col = lint.get("column") or 1
            matched = lint.get("matched_text") or ""
            end_col = col + len(matched)
            repl = msg.harper_replace_text(lint.get("suggestions") or [])
            suggestions: list[dict] = []
            if repl:
                suggestions = [
                    {"range": _range(line, col, end_col), "text": repl}
                ]
            yield _emit(
                {
                    "message": msg.harper_message(lint),
                    "location": {"path": path, "range": _range(line, col, end_col)},
                    "suggestions": suggestions,
                    "severity": "ERROR",
                }
            )


def convert_languagetool(data: list, path_index: dict[str, str]) -> Iterator[str]:
    root = _repo_root()
    for file_rec in data:
        path = resolve_path(file_rec.get("file") or "", path_index, repo_root=root)
        for match in file_rec.get("matches") or []:
            line = match.get("line") or 1
            col = match.get("column") or 1
            end_line = match.get("end_line") or line
            end_col = match.get("end_column") or (col + (match.get("length") or 0))
            rule = match.get("rule") or {}
            issue = (rule.get("issueType") or "").lower()
            if issue in ("misspelling", "grammar"):
                sev = "ERROR"
            else:
                sev = "WARNING"
            replacements = match.get("replacements") or []
            suggestions: list[dict] = []
            if replacements and replacements[0].get("value"):
                suggestions = [{"text": replacements[0]["value"]}]
            yield _emit(
                {
                    "message": msg.languagetool_message(match),
                    "location": {
                        "path": path,
                        "range": {
                            "start": {"line": line, "column": col},
                            "end": {"line": end_line, "column": end_col},
                        },
                    },
                    "suggestions": suggestions,
                    "severity": sev,
                }
            )


def _load_json(path: Path) -> Any:
    if not path.is_file() or path.stat().st_size == 0:
        return None
    text = path.read_text(encoding="utf-8")
    if path.name == "typos.json":
        records = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            if rec.get("type") == "typo":
                records.append(rec)
        return records
    return json.loads(text)


def prose_to_rdjsonl(tool: str, log_dir: Path, paths: list[str] | None = None) -> str:
    """Return combined rdjsonl text for one tool (may be empty)."""
    input_path = log_dir / f"{tool}.json"
    data = _load_json(input_path)
    if data is None:
        return ""

    if paths:
        build_path_index(log_dir, paths)
    elif not (log_dir / "path-index.json").is_file():
        lst = log_dir / "lint-paths.lst"
        if lst.is_file():
            path_lines = [
                ln.strip() for ln in lst.read_text(encoding="utf-8").splitlines() if ln.strip()
            ]
            build_path_index(log_dir, path_lines)
        else:
            build_path_index(log_dir, [])

    path_index = load_path_index(log_dir)
    blocking = int(os.environ.get("HARPER_BLOCKING_PRIORITY", "127"))

    lines: list[str] = []
    if tool == "vale" and isinstance(data, dict):
        lines.extend(convert_vale(data, path_index))
    elif tool == "typos" and isinstance(data, list):
        lines.extend(convert_typos(data, path_index))
    elif tool == "textlint" and isinstance(data, list):
        lines.extend(convert_textlint(data, path_index))
    elif tool == "rumdl" and isinstance(data, list):
        lines.extend(convert_rumdl(data, path_index))
    elif tool == "harper" and isinstance(data, list):
        lines.extend(convert_harper(data, path_index, blocking))
    elif tool == "languagetool" and isinstance(data, list):
        lines.extend(convert_languagetool(data, path_index))
    else:
        raise ValueError(f"unknown or invalid tool data: {tool}")

    return "\n".join(lines) + ("\n" if lines else "")


def report_docs_quality_combined(log_dir: Path, paths: list[str] | None = None) -> str:
    combined: list[str] = []
    for tool in ("vale", "typos", "textlint", "rumdl", "harper", "languagetool"):
        chunk = prose_to_rdjsonl(tool, log_dir, paths)
        if chunk:
            combined.append(chunk.rstrip("\n"))
    meta = log_dir / "metadata.rdjsonl"
    if meta.is_file() and meta.stat().st_size > 0:
        combined.append(meta.read_text(encoding="utf-8").rstrip("\n"))
    if not combined:
        return ""
    return "\n".join(combined) + "\n"
