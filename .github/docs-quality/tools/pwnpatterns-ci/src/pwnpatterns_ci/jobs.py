"""CI job orchestration (metadata, prek, actionlint, reviewdog reporting)."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from pwnpatterns_ci.install import install_actionlint, install_reviewdog, install_shell_linters
from pwnpatterns_ci.paths import Layout
from pwnpatterns_ci.report import record_lint_exits
from pwnpatterns_ci.reviewdog import (
    report_actionlint,
    report_docs_quality,
    report_prek,
    reporter,
    shellcheck_checkstyle,
)


def verify_metadata(layout: Layout, log_dir: Path, paths: list[str], scan_mode: str) -> int:
    log_dir.mkdir(parents=True, exist_ok=True)
    if scan_mode == "all" and paths:
        paths = sorted(layout.repo_root.glob("docs/**/*.md"))
        paths = [layout.rel(p) for p in paths if p.is_file()]
    meta_project = layout.docs_quality_dir / "tools" / "verify-metadata"
    subprocess.run(["uv", "sync", "--directory", str(meta_project)], check=True)
    rdjsonl = log_dir / "metadata.rdjsonl"
    stderr = log_dir / "metadata.stderr"
    cmd = [
        "uv",
        "run",
        "--directory",
        str(meta_project),
        "python",
        "verify_metadata.py",
        "--rdjsonl",
        *paths,
    ]
    with rdjsonl.open("w", encoding="utf-8") as out, stderr.open("w", encoding="utf-8") as err:
        proc = subprocess.run(cmd, stdout=out, stderr=err, cwd=layout.repo_root)
    (log_dir / "metadata.exit").write_text(str(proc.returncode), encoding="utf-8")
    record_lint_exits(log_dir)
    return proc.returncode


def run_prek(log_dir: Path) -> int:
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "prek.log"
    with log_file.open("w", encoding="utf-8") as fh:
        proc = subprocess.run(
            ["prek", "run", "--all-files", "--show-diff-on-failure"],
            stdout=fh,
            stderr=subprocess.STDOUT,
            cwd=os.environ.get("REPO_ROOT") or os.environ.get("GITHUB_WORKSPACE") or ".",
        )
    (log_dir / "prek.exit").write_text(str(proc.returncode), encoding="utf-8")
    return proc.returncode


def report_reviewdog(log_dir: Path, rep: str | None = None) -> None:
    rep = rep or reporter()
    report_docs_quality(log_dir, rep=rep)
    report_prek(log_dir, rep=rep)


def _find_scripts(repo_root: Path, exclude_platform: bool = True) -> list[str]:
    scripts: list[str] = []
    for p in sorted(repo_root.glob(".github/**/*.sh")):
        if exclude_platform and "pwnpatterns-ci" in p.parts:
            continue
        scripts.append(str(p.relative_to(repo_root)))
    return scripts


def _find_workflows(repo_root: Path, exclude_platform: bool = True) -> list[str]:
    wf: list[str] = []
    base = repo_root / ".github" / "workflows"
    if not base.is_dir():
        return wf
    for p in sorted(base.iterdir()):
        if p.suffix not in (".yml", ".yaml"):
            continue
        if exclude_platform and "pwnpatterns-ci" in p.parts:
            continue
        wf.append(str(p))
    return wf


def actionlint_job(layout: Layout, log_dir: Path, *, exclude_platform: bool = True) -> int:
    install_shell_linters()
    install_actionlint()
    install_reviewdog()
    log_dir.mkdir(parents=True, exist_ok=True)
    repo = layout.repo_root
    scripts = _find_scripts(repo, exclude_platform=exclude_platform)
    rep = reporter()

    if not scripts:
        (log_dir / "shellcheck.exit").write_text("0", encoding="utf-8")
    else:
        shellcheck_rc = layout.consumer_config_dir / "shellcheckrc"
        args = ["shellcheck", "-f", "checkstyle", "-x"]
        if shellcheck_rc.is_file():
            args.append(f"--rcfile={shellcheck_rc}")
        args.extend(scripts)
        sc_out = log_dir / "shellcheck.txt"
        sc_err = log_dir / "shellcheck.stderr"
        with sc_out.open("w", encoding="utf-8") as out, sc_err.open("w", encoding="utf-8") as err:
            proc = subprocess.run(args, stdout=out, stderr=err, cwd=repo)
        (log_dir / "shellcheck.exit").write_text(str(proc.returncode), encoding="utf-8")

    workflows = _find_workflows(repo, exclude_platform=exclude_platform)
    if not workflows or shutil.which("actionlint") is None:
        (log_dir / "actionlint.exit").write_text("0", encoding="utf-8")
    else:
        al_out = log_dir / "actionlint.txt"
        with al_out.open("w", encoding="utf-8") as fh:
            proc = subprocess.run(["actionlint", *workflows], stdout=fh, stderr=subprocess.STDOUT, cwd=repo)
        (log_dir / "actionlint.exit").write_text(str(proc.returncode), encoding="utf-8")

    if not scripts:
        (log_dir / "shfmt.exit").write_text("0", encoding="utf-8")
    else:
        sh_out = log_dir / "shfmt.diff"
        with sh_out.open("w", encoding="utf-8") as fh:
            proc = subprocess.run(
                ["shfmt", "-d", "-ln", "bash", "-i", "2", "-ci", *scripts],
                stdout=fh,
                stderr=subprocess.STDOUT,
                cwd=repo,
            )
        (log_dir / "shfmt.exit").write_text(str(proc.returncode), encoding="utf-8")

    if (log_dir / "actionlint.txt").is_file() and (log_dir / "actionlint.txt").stat().st_size > 0:
        report_actionlint((log_dir / "actionlint.txt").read_text(encoding="utf-8"), rep=rep)
    if (log_dir / "shellcheck.txt").is_file() and (log_dir / "shellcheck.txt").stat().st_size > 0:
        shellcheck_checkstyle(
            (log_dir / "shellcheck.txt").read_text(encoding="utf-8"),
            "shellcheck",
            rep=rep,
        )

    return fail_actionlint(log_dir)


def lint_shell(
    layout: Layout,
    *,
    include_platform: bool = False,
    autofix: bool = False,
) -> int:
    """Run shellcheck + shfmt on .github/**/*.sh (docs-dev / local)."""
    install_shell_linters()
    repo = layout.repo_root
    scripts = _find_scripts(repo, exclude_platform=not include_platform)
    if not scripts:
        return 0
    shellcheck_rc = layout.consumer_config_dir / "shellcheckrc"
    args = ["shellcheck", "-x"]
    if shellcheck_rc.is_file():
        args.append(f"--rcfile={shellcheck_rc}")
    args.extend(scripts)
    sc = subprocess.run(args, cwd=repo)
    if sc.returncode != 0:
        return sc.returncode
    shfmt_args = ["shfmt", "-w" if autofix else "-d", "-ln", "bash", "-i", "2", "-ci", *scripts]
    return subprocess.run(shfmt_args, cwd=repo).returncode


def fail_actionlint(log_dir: Path) -> int:
    fail = 0
    for name, log in (
        ("shellcheck", "shellcheck.stderr"),
        ("shfmt", "shfmt.diff"),
        ("actionlint", "actionlint.txt"),
    ):
        exit_f = log_dir / f"{name}.exit"
        if exit_f.is_file() and int(exit_f.read_text(encoding="utf-8").strip() or "0") != 0:
            p = log_dir / log
            if p.is_file():
                print(p.read_text(encoding="utf-8", errors="replace"), file=sys.stderr)
            if name == "shfmt":
                print(f"shfmt: formatting differs (see {p})", file=sys.stderr)
            fail = 1
    return fail
