#!/usr/bin/env python3
"""Run LanguageTool on routed non-English docs and write lint-logs/languagetool.json."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def offset_to_line_column(text: str, offset: int) -> tuple[int, int]:
    if offset < 0:
        offset = 0
    if offset > len(text):
        offset = len(text)
    line = text.count("\n", 0, offset) + 1
    last_nl = text.rfind("\n", 0, offset)
    column = offset - last_nl if last_nl >= 0 else offset + 1
    return line, column


def prose_body_and_line_offset(text: str) -> tuple[str, int]:
    """Return markdown body (no YAML frontmatter) and 1-based line offset for diagnostics."""
    match = FRONTMATTER_RE.match(text)
    if not match:
        return text, 0
    prefix = text[: match.end()]
    line_offset = prefix.count("\n")
    return text[match.end() :], line_offset


def extract_json(stdout: str) -> dict | None:
    for line in reversed(stdout.splitlines()):
        stripped = line.strip()
        if stripped.startswith("{") and stripped.endswith("}"):
            try:
                return json.loads(stripped)
            except json.JSONDecodeError:
                continue
    return None


def run_languagetool(
    jar: Path,
    file_path: Path,
    lt_code: str,
    repo_root: Path,
) -> dict:
    full_text = file_path.read_text(encoding="utf-8")
    body, line_offset = prose_body_and_line_offset(full_text)
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".md",
        encoding="utf-8",
        delete=False,
    ) as tmp:
        tmp.write(body)
        tmp_path = Path(tmp.name)

    try:
        cmd = [
            "java",
            "-jar",
            str(jar),
            "-l",
            lt_code,
            "--json",
            str(tmp_path),
        ]
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    finally:
        tmp_path.unlink(missing_ok=True)

    payload = extract_json(proc.stdout or "") or {}
    matches = []
    for match in payload.get("matches") or []:
        off = int(match.get("offset") or 0)
        length = int(match.get("length") or 0)
        line, column = offset_to_line_column(body, off)
        end_line, end_column = offset_to_line_column(body, off + length)
        enriched = dict(match)
        enriched["line"] = line + line_offset
        enriched["column"] = column
        enriched["end_line"] = end_line + line_offset
        enriched["end_column"] = end_column
        matches.append(enriched)
    try:
        rel = str(file_path.relative_to(repo_root))
    except ValueError:
        rel = str(file_path)
    return {
        "file": rel,
        "language": lt_code,
        "matches": matches,
        "stderr": (proc.stderr or "").strip() or None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Batch LanguageTool for routed docs")
    parser.add_argument("--log-dir", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=None)
    parser.add_argument(
        "--jar",
        type=Path,
        default=None,
        help="languagetool-commandline.jar (default: LANGUAGETOOL_HOME env)",
    )
    args = parser.parse_args()

    root = args.repo_root or repo_root()
    log_dir = args.log_dir
    if not log_dir.is_absolute():
        log_dir = (root / log_dir).resolve()
    log_dir.mkdir(parents=True, exist_ok=True)

    tsv = log_dir / "grammar-languagetool.tsv"
    if not tsv.is_file() or tsv.stat().st_size == 0:
        (log_dir / "languagetool.json").write_text("[]\n", encoding="utf-8")
        return 0

    lt_home = os.environ.get("LANGUAGETOOL_HOME")
    jar = args.jar
    if jar is None and lt_home:
        jar = Path(lt_home) / "languagetool-commandline.jar"
    if jar is None or not jar.is_file():
        print("run_languagetool_batch: languagetool-commandline.jar not found", file=sys.stderr)
        return 2

    results: list[dict] = []
    for line in tsv.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split("\t", 1)
        rel = parts[0]
        lt_code = parts[1] if len(parts) > 1 else "auto"
        full = root / rel
        if not full.is_file():
            continue
        try:
            results.append(run_languagetool(jar, full, lt_code, root))
        except OSError as exc:
            results.append(
                {
                    "file": rel,
                    "language": lt_code,
                    "matches": [],
                    "error": str(exc),
                }
            )

    out = log_dir / "languagetool.json"
    out.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    total = sum(len(r.get("matches") or []) for r in results)
    print(f"languagetool: {len(results)} file(s), {total} match(es)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
