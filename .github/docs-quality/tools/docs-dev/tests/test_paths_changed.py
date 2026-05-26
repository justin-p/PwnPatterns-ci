"""changed_doc_markdown includes committed branch edits and local worktree edits."""

from __future__ import annotations

import subprocess
from pathlib import Path

from docs_dev.paths import changed_doc_markdown


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


def _init_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    docs = repo / "docs"
    docs.mkdir()
    main_doc = docs / "on-main.md"
    main_doc.write_text("# main\n", encoding="utf-8")
    _git(repo, "add", "docs/on-main.md")
    _git(repo, "commit", "-m", "main doc")
    return repo


def test_changed_includes_uncommitted_worktree_edit(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    branch_doc = repo / "docs" / "branch-only.md"
    branch_doc.write_text("# branch\n", encoding="utf-8")
    _git(repo, "add", "docs/branch-only.md")
    _git(repo, "commit", "-m", "branch doc")

    local_doc = repo / "docs" / "local-edit.md"
    local_doc.write_text("# local\n", encoding="utf-8")
    _git(repo, "add", "docs/local-edit.md")
    _git(repo, "commit", "-m", "add local-edit")

    local_doc.write_text("# edited locally\n", encoding="utf-8")

    committed_only = changed_doc_markdown(
        repo, "main", "HEAD", include_worktree=False
    )
    assert "docs/local-edit.md" not in committed_only

    with_worktree = changed_doc_markdown(repo, "main", "HEAD", include_worktree=True)
    assert "docs/local-edit.md" in with_worktree


def test_changed_includes_untracked_md_under_docs(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    new_doc = repo / "docs" / "new-untracked.md"
    new_doc.write_text("# new\n", encoding="utf-8")

    paths = changed_doc_markdown(repo, "main", "HEAD", include_worktree=True)
    assert "docs/new-untracked.md" in paths
