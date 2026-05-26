from __future__ import annotations

from pathlib import Path

from docs_dev.models import Finding
from docs_dev.parsers import harper, languagetool, lychee, metadata, rumdl, typos, vale


def parse_all_lint_logs(
    lint_dir: Path,
    lint_paths: list[str] | None = None,
) -> list[Finding]:
    findings: list[Finding] = []
    vale_path = lint_dir / "vale.json"
    if vale_path.is_file():
        findings.extend(vale.parse_file(vale_path))
    typos_path = lint_dir / "typos.json"
    if typos_path.is_file():
        findings.extend(typos.parse_file(typos_path))
    rumdl_path = lint_dir / "rumdl.json"
    if rumdl_path.is_file():
        findings.extend(rumdl.parse_file(rumdl_path))
    harper_path = lint_dir / "harper.json"
    if harper_path.is_file():
        paths_file = lint_dir / "lint-paths.lst"
        paths = lint_paths
        if paths is None and paths_file.is_file():
            paths = [
                ln.strip()
                for ln in paths_file.read_text(encoding="utf-8").splitlines()
                if ln.strip()
            ]
        findings.extend(harper.parse_file(harper_path, paths or []))
    lt_path = lint_dir / "languagetool.json"
    if lt_path.is_file():
        findings.extend(languagetool.parse_file(lt_path))
    meta_path = lint_dir / "metadata.rdjsonl"
    if meta_path.is_file():
        findings.extend(metadata.parse_file(meta_path))
    return findings


__all__ = [
    "Finding",
    "parse_all_lint_logs",
    "vale",
    "typos",
    "rumdl",
    "harper",
    "languagetool",
    "metadata",
    "lychee",
]
