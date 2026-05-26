"""Verify platform.ref matches workflow uses: SHA pins."""

from __future__ import annotations

import re
from pathlib import Path

USES_SHA = re.compile(
    r"uses:\s+justin-p/PwnPatterns-ci/\.github/(?:workflows|actions)/[^\s]+@([0-9a-f]{40})",
    re.IGNORECASE,
)
PLATFORM_REF_INPUT = re.compile(
    r"platform_ref:\s*([0-9a-f]{40})",
    re.IGNORECASE,
)
CHECKOUT_PLATFORM_REF = re.compile(
    r"repository:\s+justin-p/PwnPatterns-ci\s*\n\s+ref:\s*([0-9a-f]{40})",
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


def workflow_pins(workflows_dir: Path) -> set[str]:
    pins: set[str] = set()
    if not workflows_dir.is_dir():
        return pins
    for wf in workflows_dir.glob("*.yml"):
        text = wf.read_text(encoding="utf-8")
        pins.update(m.lower() for m in USES_SHA.findall(text))
        pins.update(m.lower() for m in PLATFORM_REF_INPUT.findall(text))
        pins.update(m.lower() for m in CHECKOUT_PLATFORM_REF.findall(text))
    return pins


def verify_pin(repo_root: Path) -> list[str]:
    errors: list[str] = []
    ref_path = repo_root / ".github" / "platform.ref"
    ref = read_platform_ref(ref_path)
    if ref is None:
        errors.append(f"missing or empty {ref_path}")
        return errors

    workflows_dir = repo_root / ".github" / "workflows"
    wf_pins = workflow_pins(workflows_dir)
    uses_local = any(workflows_dir.glob("*.yml")) and any(
        USES_LOCAL.search(p.read_text(encoding="utf-8"))
        for p in workflows_dir.glob("*.yml")
    )
    if not wf_pins:
        if uses_local:
            return errors
        errors.append(
            "no platform pin found (justin-p/PwnPatterns-ci @SHA, platform_ref:, or checkout ref)"
        )
        return errors

    if len(wf_pins) > 1:
        errors.append(f"workflow platform pins disagree: {sorted(wf_pins)}")

    wf_pin = next(iter(wf_pins))
    if ref != wf_pin:
        errors.append(f"platform.ref ({ref}) != workflow pin ({wf_pin})")
    return errors
