"""Documentation path targeting for CI (doc-targets)."""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

from pwnpatterns_ci.config import load_repo_yml
from pwnpatterns_ci.paths import Layout

_CONFIG_PATTERN = re.compile(
    r"^(\.vale\.ini|_typos\.toml|rumdl\.toml|\.markdownlint\.json|styles/|"
    r"\.github/docs-quality/|\.github/lychee/|\.github/pwnpatterns-ci/)"
)


def _git(*args: str, cwd: Path) -> str:
    r = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    return r.stdout if r.returncode == 0 else ""


def doc_targets(layout: Layout, *, config_only_full_scan: bool = True) -> tuple[str, list[str], bool]:
    """Return (scan_mode, paths, skip)."""
    repo = load_repo_yml(layout.repo_yml_path())
    docs_dir = repo.get("docs_dir", "docs")
    root = layout.repo_root
    event = os.environ.get("GITHUB_EVENT_NAME", "push")

    base = os.environ.get("GITHUB_EVENT_PULL_REQUEST_BASE_SHA")
    head = os.environ.get("GITHUB_EVENT_PULL_REQUEST_HEAD_SHA")

    if event == "pull_request" or (base and head):
        base = base or "origin/main"
        head = head or "HEAD"
        pr_range = f"{base}...{head}"
        md_out = _git(
            "diff", "--name-only", "--diff-filter=ACMR", pr_range, "--", f"{docs_dir}/",
            cwd=root,
        )
        md_files = [ln.strip() for ln in md_out.splitlines() if ln.strip().endswith(".md")]
        if md_files:
            return "changed", md_files, False

        other_out = _git("diff", "--name-only", "--diff-filter=ACMR", pr_range, cwd=root)
        other_files = [ln.strip() for ln in other_out.splitlines() if ln.strip()]
        config_only = bool(other_files) and all(
            _CONFIG_PATTERN.match(f) for f in other_files
        )
        if config_only:
            if not config_only_full_scan:
                return "all", [], True
            all_md = sorted((root / docs_dir).rglob("*.md"))
            return "all", [layout.rel(p) for p in all_md], False
        return "all", [], True

    all_md = sorted((root / docs_dir).rglob("*.md"))
    return "all", [layout.rel(p) for p in all_md], False


def write_github_output(layout: Layout, scan_mode: str, paths: list[str], skip: bool) -> None:
    out_path = os.environ.get("GITHUB_OUTPUT")
    if not out_path:
        return
    lines: list[str] = []
    if skip:
        lines.append("skip=true")
    else:
        lines.append("skip=false")
        lines.append(f"scan_mode={scan_mode}")
        lines.append("paths<<EOF")
        lines.extend(paths)
        lines.append("EOF")
    with open(out_path, "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
