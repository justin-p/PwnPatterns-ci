"""Verify platform.ref matches workflow uses: SHA pins."""

from __future__ import annotations

import re
from pathlib import Path

USES_SHA = re.compile(
    r"uses:\s+ocd-nl/pwnpatterns-ci/\.github/workflows/[^\s]+@([0-9a-f]{40})",
    re.IGNORECASE,
)
USES_LOCAL = re.compile(
    r"uses:\s+\./\.github/pwnpatterns-ci/\.github/workflows/[^\s]+\.yml",
    re.IGNORECASE,
)
REF_SHA = re.compile(r"^[0-9a-f]{40}\s*$", re.IGNORECASE)


def read_platform_ref(path: Path) -> str | None:
    if not path.is_file():
        return None
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            if REF_SHA.match(line):
                return line.lower()
            raise ValueError(f"invalid platform.ref (expected 40-char SHA): {line!r}")
    return None


def workflow_shas(workflows_dir: Path) -> set[str]:
    shas: set[str] = set()
    if not workflows_dir.is_dir():
        return shas
    for wf in workflows_dir.glob("*.yml"):
        text = wf.read_text(encoding="utf-8")
        shas.update(m.lower() for m in USES_SHA.findall(text))
    return shas


def verify_pin(repo_root: Path) -> list[str]:
    errors: list[str] = []
    ref_path = repo_root / ".github" / "platform.ref"
    ref = read_platform_ref(ref_path)
    if ref is None:
        errors.append(f"missing or empty {ref_path}")
        return errors

    workflows_dir = repo_root / ".github" / "workflows"
    wf_shas = workflow_shas(workflows_dir)
    uses_local = any(workflows_dir.glob("*.yml")) and any(
        USES_LOCAL.search(p.read_text(encoding="utf-8"))
        for p in workflows_dir.glob("*.yml")
    )
    if not wf_shas:
        if uses_local:
            return errors
        errors.append(
            "no ocd-nl/pwnpatterns-ci @SHA or ./.github/pwnpatterns-ci workflow uses found"
        )
        return errors

    if len(wf_shas) > 1:
        errors.append(f"workflow platform SHAs disagree: {sorted(wf_shas)}")

    wf_sha = next(iter(wf_shas))
    if ref != wf_sha:
        errors.append(f"platform.ref ({ref}) != workflow uses SHA ({wf_sha})")
    return errors
