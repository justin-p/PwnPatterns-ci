"""Load manifest.env, repo.yml, and merged tool environment."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import yaml

from pwnpatterns_ci.paths import Layout

_ENV_LINE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$")


def _parse_env_file(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = _ENV_LINE.match(line)
        if m:
            out[m.group(1)] = m.group(2)
    return out


def load_repo_yml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {
            "vale_vocab": "PwnPatterns",
            "vale_styles_path": "styles",
            "docs_dir": "docs",
            "tool_versions": {},
            "path_filter_extra": [],
        }
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return {
        "vale_vocab": data.get("vale_vocab", "PwnPatterns"),
        "vale_styles_path": data.get("vale_styles_path", "styles"),
        "docs_dir": data.get("docs_dir", "docs"),
        "tool_versions": data.get("tool_versions") or {},
        "path_filter_extra": data.get("path_filter_extra") or [],
    }


def load_manifest(layout: Layout) -> dict[str, str]:
    manifest = _parse_env_file(layout.manifest_path())
    repo = load_repo_yml(layout.repo_yml_path())
    for key, val in (repo.get("tool_versions") or {}).items():
        manifest[str(key)] = str(val)
    return manifest


def apply_manifest_to_environ(layout: Layout, manifest: dict[str, str] | None = None) -> dict[str, str]:
    """Export manifest keys to os.environ; resolve REPO_ROOT-relative paths."""
    m = manifest or load_manifest(layout)
    os.environ.setdefault("REPO_ROOT", str(layout.repo_root))
    os.environ.setdefault("DOCS_QUALITY_DIR", str(layout.docs_quality_dir))
    os.environ.setdefault("AUTOMATION_DIR", str(layout.automation_dir))

    for key, value in m.items():
        os.environ[key] = value

    for path_key in (
        "HARPER_USER_DICT",
        "HARPER_IGNORE_RULES_FILE",
        "ALLOWED_TERMS",
        "ALLOWED_PATTERNS",
    ):
        if path_key in os.environ and not Path(os.environ[path_key]).is_absolute():
            os.environ[path_key] = str(layout.repo_root / os.environ[path_key])

    ignore_file = layout.consumer_config_dir / "harper.ignore-rules"
    if ignore_file.is_file():
        lines = [
            ln.strip()
            for ln in ignore_file.read_text(encoding="utf-8").splitlines()
            if ln.strip() and not ln.strip().startswith("#")
        ]
        if lines:
            os.environ["HARPER_IGNORE_RULES"] = ",".join(lines)

    return m


def vale_accept_path(layout: Layout, repo: dict[str, Any] | None = None) -> Path:
    r = repo or load_repo_yml(layout.repo_yml_path())
    vocab = r.get("vale_vocab", "PwnPatterns")
    return layout.repo_root / "styles" / "config" / "vocabularies" / vocab / "accept.txt"
