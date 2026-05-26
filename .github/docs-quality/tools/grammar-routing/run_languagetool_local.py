#!/usr/bin/env python3
"""Run LanguageTool on a single markdown file with the same preprocessing as CI.

This is intended to make local LanguageTool investigations comparable to the
docs-quality CI lane. Standalone LanguageTool GUI scans raw files (including
frontmatter and markup), which is much noisier for PwnPatterns docs.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from allowlist_terms import filter_languagetool_matches, load_consumer_allowlists
from lt_preprocess import prepare_md_for_languagetool


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


def extract_json(stdout: str) -> dict | None:
    for line in reversed(stdout.splitlines()):
        stripped = line.strip()
        if stripped.startswith("{") and stripped.endswith("}"):
            try:
                return json.loads(stripped)
            except json.JSONDecodeError:
                continue
    return None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="LanguageTool on a single markdown file (CI-equivalent preprocessing)"
    )
    parser.add_argument("path", type=Path, help="Path to a markdown file")
    parser.add_argument(
        "-l",
        "--language",
        default="auto",
        help="LanguageTool -l code (default: auto)",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="Repository root for allowlists and relative paths",
    )
    parser.add_argument(
        "--jar",
        type=Path,
        default=None,
        help="Path to languagetool-commandline.jar (default: LANGUAGETOOL_HOME env)",
    )
    parser.add_argument(
        "--no-allowlist",
        action="store_true",
        help="Do not filter matches with consumer allowlists",
    )
    parser.add_argument(
        "--dump-preprocessed",
        action="store_true",
        help="Print the preprocessed markdown (for debugging) to stdout and exit",
    )
    args = parser.parse_args()

    root = (args.repo_root or repo_root()).resolve()
    file_path = (root / args.path) if not args.path.is_absolute() else args.path
    if not file_path.is_file():
        print(f"run_languagetool_local: missing file: {file_path}", file=sys.stderr)
        return 2

    jar = args.jar
    if jar is None:
        lt_home = os.environ.get("LANGUAGETOOL_HOME")
        if lt_home:
            jar = Path(lt_home) / "languagetool-commandline.jar"
    if jar is None or not Path(jar).is_file():
        print(
            "run_languagetool_local: languagetool-commandline.jar not found "
            "(set --jar or LANGUAGETOOL_HOME)",
            file=sys.stderr,
        )
        return 2

    full_text = file_path.read_text(encoding="utf-8")
    body, line_offset = prepare_md_for_languagetool(full_text)
    if args.dump_preprocessed:
        sys.stdout.write(body)
        return 0

    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".md",
        encoding="utf-8",
        delete=False,
    ) as tmp:
        tmp.write(body)
        tmp_path = Path(tmp.name)

    try:
        cmd = ["java", "-jar", str(jar), "-l", args.language, "--json", str(tmp_path)]
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
    matches: list[dict] = []
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

    if not args.no_allowlist:
        terms, casing = load_consumer_allowlists(root)
        matches = filter_languagetool_matches(matches, terms, casing)

    try:
        rel = str(file_path.relative_to(root))
    except ValueError:
        rel = str(file_path)

    out = {
        "file": rel,
        "language": args.language,
        "matches": matches,
        "stderr": (proc.stderr or "").strip() or None,
        "exit_code": proc.returncode,
    }
    sys.stdout.write(json.dumps(out, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

