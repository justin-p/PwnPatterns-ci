from __future__ import annotations

import os
from pathlib import Path

import pytest

from docs_dev.context import RepoContext, resolve_consumer_config_dir, resolve_docs_quality_dir


def test_resolve_docs_quality_dir_prefers_platform(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("DOCS_QUALITY_DIR", raising=False)
    repo = tmp_path / "repo"
    platform = repo / ".github" / "pwnpatterns-ci" / ".github" / "docs-quality"
    legacy = repo / ".github" / "docs-quality"
    platform.mkdir(parents=True)
    legacy.mkdir(parents=True)
    assert resolve_docs_quality_dir(repo) == platform.resolve()


def test_resolve_consumer_config_dir_splits_from_platform(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    platform = repo / ".github" / "pwnpatterns-ci" / ".github" / "docs-quality"
    consumer_cfg = repo / ".github" / "docs-quality" / "config"
    platform.mkdir(parents=True)
    consumer_cfg.mkdir(parents=True)
    assert resolve_consumer_config_dir(repo, platform) == consumer_cfg.resolve()


def test_from_env_platform_layout(tmp_path: Path, monkeypatch) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "docs").mkdir()
    platform = repo / ".github" / "pwnpatterns-ci" / ".github" / "docs-quality"
    (platform / "config").mkdir(parents=True)
    (platform / "config" / "manifest.env").write_text(
        "DOC_LINT_INSTALL_DIR=.local/doc-linters\n"
        "VALE_VERSION=3.9.1\n"
        "TYPOS_VERSION=1.29.0\n"
        "RUMDL_VERSION=0.1.78\n"
        "HARPER_VERSION=2.1.0\n"
        "HARPER_USER_DICT=.github/docs-quality/generated/harper-dictionary.txt\n"
        "HARPER_IGNORE_RULES_FILE=.github/docs-quality/config/harper.ignore-rules\n"
        "SHELLCHECK_VERSION=0.11.0\n"
        "SHFMT_VERSION=3.12.0\n"
        "REVIEWDOG_VERSION=0.20.3\n"
        "LYCHEE_VERSION=0.24.2\n"
        "ACTIONLINT_VERSION=1.7.12\n",
        encoding="utf-8",
    )
    consumer_cfg = repo / ".github" / "docs-quality" / "config"
    consumer_cfg.mkdir(parents=True)
    monkeypatch.chdir(repo)
    monkeypatch.delenv("DOCS_QUALITY_DIR", raising=False)
    monkeypatch.setenv("REPO_ROOT", str(repo))

    ctx = RepoContext.from_env()

    assert ctx.docs_quality_dir == platform.resolve()
    assert ctx.consumer_config_dir == consumer_cfg.resolve()
    assert ctx.manifest_path == platform / "config" / "manifest.env"
