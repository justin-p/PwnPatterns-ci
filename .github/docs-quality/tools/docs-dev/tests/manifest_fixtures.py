"""Shared manifest.env helpers for docs-dev tests.

Platform ``config/manifest.env`` is the single source of truth for pinned tool
versions. Tests must load from that file instead of hardcoding versions so
Renovate manifest bumps do not require manual test edits.
"""

from __future__ import annotations

from pathlib import Path

from docs_dev.context import RepoContext
from docs_dev.manifest import Manifest, load_manifest


def platform_manifest_env_path() -> Path:
    return Path(__file__).resolve().parents[3] / "config" / "manifest.env"


def load_platform_manifest() -> Manifest:
    return load_manifest(platform_manifest_env_path())


def copy_platform_manifest_to(docs_quality_dir: Path) -> Path:
    dest = docs_quality_dir / "config" / "manifest.env"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(
        platform_manifest_env_path().read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    return dest


def setup_tui_check_docs_quality(repo_root: Path) -> Path:
    """Minimal consumer docs-quality tree for CheckScreen TUI e2e tests."""
    docs_quality = repo_root / ".github" / "docs-quality"
    allowlists = docs_quality / "config" / "allowlists"
    allowlists.mkdir(parents=True, exist_ok=True)
    (allowlists / "terms.txt").write_text("# terms\n", encoding="utf-8")
    (allowlists / "canonical-casing.txt").write_text("# casing\n", encoding="utf-8")
    copy_platform_manifest_to(docs_quality)
    return docs_quality


def tui_check_repo_context(repo_root: Path) -> RepoContext:
    """RepoContext for CheckScreen tests with platform manifest pins."""
    docs_quality = setup_tui_check_docs_quality(repo_root)
    manifest_path = docs_quality / "config" / "manifest.env"
    return RepoContext(
        repo_root=repo_root,
        docs_quality_dir=docs_quality,
        consumer_config_dir=docs_quality / "config",
        automation_dir=docs_quality / "automation",
        automation_bin=docs_quality / "automation" / "bin",
        automation_install=docs_quality / "automation" / "install",
        manifest_path=manifest_path,
        manifest=load_manifest(manifest_path),
        doc_lint_install_dir=repo_root / "linters",
        lint_log_dir=repo_root / "lint-logs",
        lychee_filter_jq=repo_root / "filter.jq",
    )
