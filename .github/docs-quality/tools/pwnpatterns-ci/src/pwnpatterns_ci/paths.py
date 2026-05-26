"""Repository and platform path resolution."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _find_repo_root(start: Path | None = None) -> Path:
    if os.environ.get("REPO_ROOT"):
        return Path(os.environ["REPO_ROOT"]).resolve()
    if os.environ.get("GITHUB_WORKSPACE"):
        return Path(os.environ["GITHUB_WORKSPACE"]).resolve()
    dq_env = os.environ.get("DOCS_QUALITY_DIR")
    if dq_env:
        dq = Path(dq_env).resolve()
        # Consumer checkout: .../repo/.github/pwnpatterns-ci/.github/docs-quality
        if (
            dq.name == "docs-quality"
            and dq.parent.name == ".github"
            and dq.parent.parent.name == "pwnpatterns-ci"
        ):
            consumer = dq.parent.parent.parent.parent
            if (consumer / ".github" / "platform.ref").is_file():
                return consumer
    cur = (start or Path.cwd()).resolve()
    for parent in [cur, *cur.parents]:
        if (parent / ".git").exists():
            return parent
    return cur


def resolve_docs_quality_dir(repo_root: Path) -> Path:
    if os.environ.get("DOCS_QUALITY_DIR"):
        return Path(os.environ["DOCS_QUALITY_DIR"]).resolve()
    platform = repo_root / ".github" / "pwnpatterns-ci" / ".github" / "docs-quality"
    if platform.is_dir():
        return platform
    legacy = repo_root / ".github" / "docs-quality"
    return legacy


@dataclass(frozen=True)
class Layout:
    repo_root: Path
    docs_quality_dir: Path
    automation_dir: Path
    config_dir: Path
    tools_dir: Path
    consumer_config_dir: Path

    @classmethod
    def discover(cls, repo_root: Path | None = None) -> Layout:
        root = repo_root or _find_repo_root()
        dq = resolve_docs_quality_dir(root)
        consumer_cfg = root / ".github" / "docs-quality" / "config"
        if not consumer_cfg.is_dir():
            consumer_cfg = dq / "config"
        return cls(
            repo_root=root,
            docs_quality_dir=dq,
            automation_dir=dq / "automation",
            config_dir=dq / "config",
            tools_dir=dq / "tools",
            consumer_config_dir=consumer_cfg,
        )

    def manifest_path(self) -> Path:
        return self.config_dir / "manifest.env"

    def repo_yml_path(self) -> Path:
        p = self.consumer_config_dir / "repo.yml"
        if p.is_file():
            return p
        return self.config_dir / "repo.yml"

    def platform_ref_path(self) -> Path:
        return self.repo_root / ".github" / "platform.ref"

    def rel(self, path: Path) -> str:
        try:
            return path.resolve().relative_to(self.repo_root.resolve()).as_posix()
        except ValueError:
            return path.as_posix()

    def resolve_log_dir(self, log_dir: Path) -> Path:
        """Resolve lint log dir under the consumer repo, not uv's project cwd."""
        if log_dir.is_absolute():
            return log_dir.resolve()
        return (self.repo_root / log_dir).resolve()
