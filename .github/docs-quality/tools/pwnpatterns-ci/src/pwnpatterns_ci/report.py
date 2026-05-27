"""Lint exit recording and failure reporting."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from pwnpatterns_ci.rdjsonl.convert import prose_to_rdjsonl

HARPER_BLOCKING = int(os.environ.get("HARPER_BLOCKING_PRIORITY", "127"))
_CONTENT_LINTERS = ("vale", "typos", "textlint", "rumdl", "harper", "languagetool", "metadata")


def _jq(expr: str, path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["jq", expr, str(path)],
        capture_output=True,
        text=True,
        check=False,
    )


def _write_exit(log_dir: Path, tool: str, code: int, detail: str) -> None:
    (log_dir / f"{tool}.exit").write_text(str(code), encoding="utf-8")
    print(f"{tool}: {detail} ({tool}.exit={code})", flush=True)


def record_lint_exits(log_dir: Path) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)

    vale_json = log_dir / "vale.json"
    if vale_json.is_file() and vale_json.stat().st_size:
        r = _jq(
            '[to_entries[] | .value[]? | select((.Severity // "") | ascii_downcase == "error")] | length',
            vale_json,
        )
        count = int(r.stdout.strip() or "0")
        _write_exit(log_dir, "vale", 1 if count else 0, f"{count} error(s) in JSON")
    else:
        _write_exit(log_dir, "vale", 0, "no vale.json")

    typos_json = log_dir / "typos.json"
    if typos_json.is_file() and typos_json.stat().st_size:
        r = subprocess.run(
            [
                "bash",
                "-c",
                f"jq -c -R 'fromjson | select(.type == \"typo\")' {typos_json} | jq -s 'length'",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        count = int(r.stdout.strip() or "0")
        _write_exit(log_dir, "typos", 1 if count else 0, f"{count} typo(s) in JSON")
    else:
        _write_exit(log_dir, "typos", 0, "no typos.json")

    textlint_json = log_dir / "textlint.json"
    if textlint_json.is_file() and textlint_json.stat().st_size:
        count = int(_jq("[.[]? | .messages[]?] | length", textlint_json).stdout.strip() or "0")
        _write_exit(log_dir, "textlint", 1 if count else 0, f"{count} message(s) in JSON")
    else:
        _write_exit(log_dir, "textlint", 0, "no textlint.json")

    rumdl_json = log_dir / "rumdl.json"
    if rumdl_json.is_file() and rumdl_json.stat().st_size:
        count = int(_jq("length", rumdl_json).stdout.strip() or "0")
        _write_exit(log_dir, "rumdl", 1 if count else 0, f"{count} issue(s) in JSON")
    else:
        _write_exit(log_dir, "rumdl", 0, "no rumdl.json")

    harper_json = log_dir / "harper.json"
    if harper_json.is_file() and harper_json.stat().st_size:
        r = _jq(
            f"[.[] | .lints[]? | select((.priority // 0) >= {HARPER_BLOCKING})] | length",
            harper_json,
        )
        blocking = int(r.stdout.strip() or "0")
        total = int(_jq("[.[] | .lints[]?] | length", harper_json).stdout.strip() or "0")
        _write_exit(
            log_dir,
            "harper",
            1 if blocking else 0,
            f"{blocking} blocking (priority >= {HARPER_BLOCKING}), {total} total",
        )
    else:
        _write_exit(log_dir, "harper", 0, "no harper.json")

    lt_json = log_dir / "languagetool.json"
    if lt_json.is_file() and lt_json.stat().st_size:
        count = int(_jq("[.[]? | .matches[]?] | length", lt_json).stdout.strip() or "0")
        _write_exit(log_dir, "languagetool", 1 if count else 0, f"{count} match(es) in JSON")
    else:
        _write_exit(log_dir, "languagetool", 0, "no languagetool.json")

    rdjsonl = log_dir / "metadata.rdjsonl"
    cli_exit = 0
    meta_exit = log_dir / "metadata.exit"
    if meta_exit.is_file():
        cli_exit = int(meta_exit.read_text(encoding="utf-8").strip() or "0")
    count = sum(1 for _ in rdjsonl.open(encoding="utf-8")) if rdjsonl.is_file() and rdjsonl.stat().st_size else 0
    _write_exit(
        log_dir,
        "metadata",
        1 if cli_exit or count else 0,
        f"verify exit={cli_exit}, {count} rdjsonl diagnostic(s)",
    )


def _format_diagnostic_line(diagnostic: dict) -> str:
    location = diagnostic.get("location") or {}
    path = location.get("path") or "?"
    start = (location.get("range") or {}).get("start") or {}
    line = start.get("line") or 1
    column = start.get("column") or 1
    message = diagnostic.get("message") or "issue"
    return f"{path}:{line}:{column}: {message}"


def _tool_failure_lines(log_dir: Path, tool: str, max_lines: int) -> list[str]:
    lines: list[str] = []

    if tool == "metadata":
        rdjsonl = log_dir / "metadata.rdjsonl"
        if rdjsonl.is_file() and rdjsonl.stat().st_size:
            for raw in rdjsonl.read_text(encoding="utf-8").splitlines():
                if raw.strip():
                    lines.append(_format_diagnostic_line(json.loads(raw)))
    else:
        json_path = log_dir / f"{tool}.json"
        if json_path.is_file() and json_path.stat().st_size:
            try:
                chunk = prose_to_rdjsonl(tool, log_dir)
            except (ValueError, json.JSONDecodeError, OSError):
                chunk = ""
            for raw in chunk.splitlines():
                if raw.strip():
                    lines.append(_format_diagnostic_line(json.loads(raw)))

    if not lines:
        stderr = log_dir / f"{tool}.stderr"
        if stderr.is_file() and stderr.stat().st_size:
            lines.extend(stderr.read_text(encoding="utf-8").splitlines())

    if not lines:
        log_file = log_dir / f"{tool}.log"
        if log_file.is_file() and log_file.stat().st_size:
            lines.extend(log_file.read_text(encoding="utf-8").splitlines())

    if not lines:
        exit_f = log_dir / f"{tool}.exit"
        code = exit_f.read_text(encoding="utf-8").strip() if exit_f.is_file() else "?"
        lines.append(
            f"{tool} exited {code} with no parseable diagnostics "
            f"(checked {log_dir / f'{tool}.json'}, stderr, and log)"
        )

    if len(lines) > max_lines:
        omitted = len(lines) - max_lines
        lines = lines[:max_lines]
        lines.append(f"... {omitted} more {tool} issue(s); see {log_dir}/")
    return lines


def report_failures(log_dir: Path, max_lines: int = 60) -> int:
    fail = 0
    for tool in _CONTENT_LINTERS:
        exit_f = log_dir / f"{tool}.exit"
        if not exit_f.is_file():
            continue
        if int(exit_f.read_text(encoding="utf-8").strip() or "0") == 0:
            continue
        print(f"::error title={tool}::{tool} reported issues (details below)")
        print(f"::group::{tool} lint log summary")
        print("\n".join(_tool_failure_lines(log_dir, tool, max_lines)))
        fail = 1
        print("::endgroup::")
    if fail:
        print(f"\nOne or more content linters failed. Full artifacts under {log_dir}/")
    return fail
