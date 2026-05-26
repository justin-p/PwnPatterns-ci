from __future__ import annotations

import subprocess
from pathlib import Path


def all_doc_markdown(repo_root: Path) -> list[str]:
    docs = repo_root / "docs"
    return sorted(str(p.relative_to(repo_root)) for p in docs.rglob("*.md"))


def changed_doc_markdown(
    repo_root: Path,
    base: str = "origin/main",
    head: str = "HEAD",
) -> list[str]:
    proc = subprocess.run(
        [
            "git",
            "diff",
            "--name-only",
            "--diff-filter=ACMR",
            f"{base}...{head}",
            "--",
            "docs/",
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    paths: list[str] = []
    for line in proc.stdout.splitlines():
        s = line.strip()
        if s.endswith(".md"):
            paths.append(s)
    return sorted(paths)
