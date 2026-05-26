from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass

from docs_dev.context import RepoContext


@dataclass
class ToolStatus:
    name: str
    state: str
    version: str | None = None


def _version_from_output(name: str, out: str) -> str:
    line = (out.strip().splitlines() or [""])[0]
    if name == "actionlint":
        return line.split()[0] if line else "ok"
    if name == "shellcheck":
        m = re.search(r"version:\s*(\S+)", out, re.I)
        return m.group(1) if m else line
    if name == "shfmt":
        return line.lstrip("v")
    if name in ("harper", "harper-cli"):
        parts = line.split()
        return parts[1] if len(parts) > 1 else line
    return line


def _probe_binary(ctx: RepoContext, name: str) -> ToolStatus:
    path = ctx.doc_lint_install_dir / name
    if path.is_file():
        bin_path = str(path)
        label = "installed"
    elif shutil.which(name):
        bin_path = shutil.which(name) or name
        label = "on PATH"
    else:
        return ToolStatus(name, "missing")

    for flag in ("--version", "-version", "-v"):
        try:
            proc = subprocess.run(
                [bin_path, flag],
                capture_output=True,
                text=True,
                check=False,
                timeout=10,
            )
            out = proc.stdout or proc.stderr
            if proc.returncode == 0 or out.strip():
                ver = _version_from_output(name, out)
                return ToolStatus(name, label, ver)
        except (OSError, subprocess.TimeoutExpired):
            continue
    return ToolStatus(name, label, "ok")


def run_doctor(ctx: RepoContext) -> tuple[bool, list[ToolStatus]]:
    ok = True
    rows: list[ToolStatus] = []
    for cmd in ("curl", "jq", "uv"):
        if shutil.which(cmd):
            rows.append(ToolStatus(cmd, "ok"))
        else:
            rows.append(ToolStatus(cmd, "MISSING"))
            ok = False

    for name in (
        "vale",
        "typos",
        "rumdl",
        "harper-cli",
        "lychee",
        "shellcheck",
        "shfmt",
        "reviewdog",
        "actionlint",
    ):
        st = _probe_binary(ctx, name)
        if st.state == "missing":
            ok = False
        rows.append(st)

    if shutil.which("prek"):
        rows.append(ToolStatus("prek", "ok"))
    else:
        rows.append(ToolStatus("prek", "not installed"))

    return ok, rows
