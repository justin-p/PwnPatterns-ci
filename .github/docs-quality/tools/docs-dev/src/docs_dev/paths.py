from __future__ import annotations

import subprocess
from collections.abc import Iterable
from pathlib import Path


def all_doc_markdown(repo_root: Path) -> list[str]:
    docs = repo_root / "docs"
    return sorted(str(p.relative_to(repo_root)) for p in docs.rglob("*.md"))


def _git_name_only(repo_root: Path, *args: str) -> list[str]:
    proc = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def _md_under_docs(paths: Iterable[str]) -> list[str]:
    return sorted({p for p in paths if p.startswith("docs/") and p.endswith(".md")})


def changed_doc_markdown(
    repo_root: Path,
    base: str = "origin/main",
    head: str = "HEAD",
    *,
    include_worktree: bool = True,
) -> list[str]:
    """Markdown under ``docs/`` changed on the branch and/or in the working tree.

    Uses ``{base}...{head}`` (committed branch changes, same as PR CI). When
    *include_worktree* is true, also includes staged/unstaged edits vs *head* and
    untracked ``docs/**/*.md`` so local docs-dev matches what you see in ``git status``.
    """
    committed = _git_name_only(
        repo_root,
        "diff",
        "--name-only",
        "--diff-filter=ACMR",
        f"{base}...{head}",
        "--",
        "docs/",
    )
    found: set[str] = set(_md_under_docs(committed))

    if include_worktree:
        local = _git_name_only(
            repo_root,
            "diff",
            "--name-only",
            "--diff-filter=ACMR",
            head,
            "--",
            "docs/",
        )
        found.update(_md_under_docs(local))
        untracked = _git_name_only(
            repo_root,
            "ls-files",
            "--others",
            "--exclude-standard",
            "--",
            "docs/",
        )
        found.update(_md_under_docs(untracked))

    return sorted(found)
