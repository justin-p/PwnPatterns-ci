#!/usr/bin/env python3
"""Merge PwnPatterns.Contractions findings from ```YAML [list] blocks into lint-logs/vale.json."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def main() -> int:
    repo_root = Path(os.environ.get("REPO_ROOT", Path.cwd())).resolve()
    lint_dir = Path(os.environ.get("CI_LINT_LOG_DIR", repo_root / "lint-logs"))
    paths_file = lint_dir / "lint-paths.lst"
    if not paths_file.is_file():
        return 0
    paths = [ln.strip() for ln in paths_file.read_text(encoding="utf-8").splitlines() if ln.strip()]
    if not paths:
        return 0

    sys.path.insert(0, str(repo_root / ".github/docs-quality/tools/docs-dev/src"))
    from docs_dev.template_list_contractions import merge_into_vale_json

    vale_json = lint_dir / "vale.json"
    return 1 if merge_into_vale_json(repo_root, paths, vale_json) else 0


if __name__ == "__main__":
    raise SystemExit(main())
