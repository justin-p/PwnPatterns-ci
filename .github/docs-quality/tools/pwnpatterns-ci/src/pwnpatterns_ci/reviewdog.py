"""reviewdog reporter helpers."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

from pwnpatterns_ci.rdjsonl.convert import report_docs_quality_combined

_METADATA_RE = re.compile(
    r"^\s*❌\s+(docs/.+\.md):\s*(.*)$",
    re.MULTILINE,
)
_SHELLCHECK_RE = re.compile(r"^\.github/.*\.sh:\d+:\d+:")


def reporter() -> str:
    if os.environ.get("CI_REVIEWDOG_MODE") == "local" or not os.environ.get("GITHUB_ACTIONS"):
        return "local"
    if os.environ.get("GITHUB_EVENT_NAME") == "pull_request":
        return "github-pr-review"
    return "github-check"


def fail_level(rep: str | None = None) -> str:
    rep = rep or reporter()
    return "none" if rep == "local" else "error"


def filter_mode(rep: str | None = None) -> str:
    return "nofilter"


def rdjsonl(
    name: str,
    stdin: str,
    *,
    rep: str | None = None,
    extra_args: list[str] | None = None,
) -> None:
    if not stdin.strip():
        return
    rep = rep or reporter()
    cmd = [
        "reviewdog",
        "-f=rdjsonl",
        f"-name={name}",
        f"-reporter={rep}",
        f"-fail-level={fail_level(rep)}",
        f"-filter-mode={filter_mode(rep)}",
        *(extra_args or []),
    ]
    subprocess.run(cmd, input=stdin, text=True, check=False)


def report_docs_quality(log_dir: Path, rep: str | None = None) -> None:
    combined = report_docs_quality_combined(log_dir)
    if combined:
        rdjsonl("docs-quality", combined, rep=rep)


def report_prek(
    log_dir: Path,
    rep: str | None = None,
    *,
    exit_file: Path | None = None,
    log_file: Path | None = None,
) -> None:
    rep = rep or reporter()
    exit_path = exit_file or log_dir / "prek.exit"
    log_path = log_file or log_dir / "prek.log"
    if not exit_path.is_file():
        return
    if int(exit_path.read_text(encoding="utf-8").strip() or "0") == 0:
        return

    fl = fail_level(rep)
    fm = filter_mode(rep)
    reported = False

    diff = subprocess.run(
        ["git", "diff", "--quiet"],
        cwd=os.environ.get("REPO_ROOT") or os.environ.get("GITHUB_WORKSPACE") or ".",
        check=False,
    )
    if diff.returncode != 0:
        proc = subprocess.run(
            ["git", "--no-pager", "diff"],
            capture_output=True,
            text=True,
            check=False,
        )
        cmd = [
            "reviewdog",
            "-f=diff",
            "-name=prek",
            f"-reporter={rep}",
            f"-fail-level={fl}",
            f"-filter-mode={fm}",
        ]
        if rep == "local":
            cmd.append("-diff=git diff")
        subprocess.run(cmd, input=proc.stdout, text=True, check=False)
        reported = True

    if log_path.is_file():
        log_text = log_path.read_text(encoding="utf-8", errors="replace")
        meta_lines: list[str] = []
        for m in _METADATA_RE.finditer(log_text):
            path, msg = m.group(1), m.group(2)
            import json

            meta_lines.append(
                json.dumps(
                    {
                        "message": (
                            f"[prek] metadata: {msg} — File: {path} — "
                            "Fix YAML frontmatter / pattern metadata (see verify-metadata)."
                        ),
                        "location": {"path": path, "range": {"start": {"line": 1, "column": 1}}},
                        "severity": "ERROR",
                    },
                    ensure_ascii=False,
                )
            )
        if meta_lines:
            rdjsonl("prek", "\n".join(meta_lines) + "\n", rep=rep)
            reported = True

        shell_lines = [ln for ln in log_text.splitlines() if _SHELLCHECK_RE.match(ln)]
        if shell_lines:
            shellcheck_gcc(
                "\n".join(shell_lines) + "\n",
                "prek-shellcheck",
                rep=rep,
            )
            reported = True

    if not reported and log_path.is_file():
        print(
            f"prek failed but produced no diff or parseable diagnostics; see {log_path}",
            file=sys.stderr,
        )
        tail = log_path.read_text(encoding="utf-8", errors="replace").splitlines()[-80:]
        print("\n".join(tail), file=sys.stderr)


def shellcheck_checkstyle(log_text: str, name: str = "shellcheck", *, rep: str | None = None) -> None:
    if not log_text.strip():
        return
    rep = rep or reporter()
    subprocess.run(
        [
            "reviewdog",
            "-f=checkstyle",
            f"-name={name}",
            f"-reporter={rep}",
            f"-fail-level={fail_level(rep)}",
            f"-filter-mode={filter_mode(rep)}",
        ],
        input=log_text,
        text=True,
        check=False,
    )


def shellcheck_gcc(log_text: str, name: str = "shellcheck", *, rep: str | None = None) -> None:
    if not log_text.strip():
        return
    rep = rep or reporter()
    subprocess.run(
        [
            "reviewdog",
            "-efm=%f:%l:%c: %t: %m",
            f"-name={name}",
            f"-reporter={rep}",
            f"-fail-level={fail_level(rep)}",
            f"-filter-mode={filter_mode(rep)}",
        ],
        input=log_text,
        text=True,
        check=False,
    )


def report_actionlint(stdout: str, rep: str | None = None) -> None:
    if not stdout.strip():
        return
    rep = rep or reporter()
    subprocess.run(
        [
            "reviewdog",
            "-efm=%f:%l:%c: %m",
            "-name=actionlint",
            f"-reporter={rep}",
            f"-fail-level={fail_level(rep)}",
            f"-filter-mode={filter_mode(rep)}",
        ],
        input=stdout,
        text=True,
        check=False,
    )
