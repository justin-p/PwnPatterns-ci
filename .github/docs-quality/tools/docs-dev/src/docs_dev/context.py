from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from docs_dev.manifest import Manifest, load_manifest


def _find_repo_root(start: Path | None = None) -> Path:
    if env := os.environ.get("REPO_ROOT"):
        return Path(env).resolve()
    cur = (start or Path.cwd()).resolve()
    for parent in [cur, *cur.parents]:
        if (parent / "docs").is_dir() and (parent / ".github" / "docs-quality").is_dir():
            return parent
    return cur


@dataclass
class RepoContext:
    repo_root: Path
    docs_quality_dir: Path
    automation_dir: Path
    automation_bin: Path
    automation_install: Path
    manifest_path: Path
    manifest: Manifest
    doc_lint_install_dir: Path
    lint_log_dir: Path
    lychee_filter_jq: Path

    @classmethod
    def from_env(cls, start: Path | None = None) -> RepoContext:
        repo_root = _find_repo_root(start)
        docs_quality = repo_root / ".github" / "docs-quality"
        automation = docs_quality / "automation"
        manifest_path = docs_quality / "config" / "manifest.env"
        manifest = load_manifest(manifest_path)

        install = Path(
            os.environ.get(
                "DOC_LINT_INSTALL_DIR",
                repo_root / ".local" / "doc-linters",
            )
        ).resolve()

        return cls(
            repo_root=repo_root,
            docs_quality_dir=docs_quality,
            automation_dir=automation,
            automation_bin=automation / "bin",
            automation_install=automation / "install",
            manifest_path=manifest_path,
            manifest=manifest,
            doc_lint_install_dir=install,
            lint_log_dir=repo_root / "lint-logs",
            lychee_filter_jq=repo_root
            / ".github"
            / "lychee"
            / "automation"
            / "filters"
            / "to-rdjsonl.jq",
        )

    def path_with_tools(self) -> dict[str, str]:
        env = os.environ.copy()
        env["REPO_ROOT"] = str(self.repo_root)
        env["DOC_LINT_INSTALL_DIR"] = str(self.doc_lint_install_dir)
        env["PATH"] = f"{self.doc_lint_install_dir}:{env.get('PATH', '')}"
        env["HOME"] = env.get("HOME", str(Path.home()))
        return env

    def harper_user_dict_path(self) -> Path:
        return self.repo_root / self.manifest.harper_user_dict

    def prepare_harper_config(self) -> None:
        harper_cfg = Path.home() / ".config" / "harper-ls"
        harper_share = Path.home() / ".local" / "share" / "harper-ls" / "file_dictionaries"
        harper_cfg.mkdir(parents=True, exist_ok=True)
        harper_share.mkdir(parents=True, exist_ok=True)
        (harper_cfg / "dictionary.txt").touch(exist_ok=True)

    def tool_path(self, name: str) -> str:
        candidate = self.doc_lint_install_dir / name
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
        return name
