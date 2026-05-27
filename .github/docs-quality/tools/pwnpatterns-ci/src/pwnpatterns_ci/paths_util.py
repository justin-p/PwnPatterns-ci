"""Doc path loading and path-index resolution for rdjsonl."""

from __future__ import annotations

import json
import os
from pathlib import Path

_PLATFORM_PATH_PREFIXES = (
    ".github/pwnpatterns-ci/",
    ".github/docs-quality/tools/pwnpatterns-ci/",
)


def strip_repo_root(path: str, repo_root: str) -> str:
    if not path or not repo_root:
        return path
    root = repo_root if repo_root.endswith("/") else f"{repo_root}/"
    if path.startswith(root):
        rel = path[len(root) :]
        return rel[1:] if rel.startswith("/") else rel
    return path


def _strip_platform_prefix(path: str) -> str:
    for prefix in _PLATFORM_PATH_PREFIXES:
        if path.startswith(prefix):
            return path[len(prefix) :]
    return path


def resolve_path(
    raw: str,
    path_index: dict[str, str],
    *,
    repo_root: str = "",
) -> str:
    if not raw or not isinstance(raw, str):
        return raw
    rel = strip_repo_root(raw, repo_root)
    rel = _strip_platform_prefix(rel)
    if "/" in rel:
        if rel.startswith("docs/"):
            return rel
        return path_index.get(Path(rel).name, rel)
    return path_index.get(rel, rel)


def load_path_index(log_dir: Path) -> dict[str, str]:
    idx = log_dir / "path-index.json"
    if not idx.is_file():
        return {}
    return json.loads(idx.read_text(encoding="utf-8"))


def build_path_index(log_dir: Path, paths: list[str]) -> None:
    index: dict[str, str] = {}
    for p in paths:
        index[Path(p).name] = p
    log_dir.mkdir(parents=True, exist_ok=True)
    (log_dir / "path-index.json").write_text(json.dumps(index), encoding="utf-8")


def expand_doc_paths(multiline: str) -> str:
    """Expand GHA multiline paths output to newline-separated paths."""
    return "\n".join(ln.strip() for ln in multiline.splitlines() if ln.strip())


def write_github_paths_output(paths: str, output_file: str | None = None) -> None:
    """Write paths<<EOF block for GITHUB_OUTPUT."""
    out = output_file or os.environ.get("GITHUB_OUTPUT", "")
    if not out:
        return
    with open(out, "a", encoding="utf-8") as fh:
        fh.write("paths<<EOF\n")
        fh.write(paths)
        if paths and not paths.endswith("\n"):
            fh.write("\n")
        fh.write("EOF\n")
