"""reviewdog reporter helpers."""

from __future__ import annotations

import json
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
_DEFAULT_MAX_RESULTS_PR_REVIEW = 20
_DEFAULT_MAX_RESULTS_CHECK = 10


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


def _max_results(rep: str) -> int:
    key = "REVIEWDOG_MAX_RESULTS_PR_REVIEW" if rep == "github-pr-review" else "REVIEWDOG_MAX_RESULTS_CHECK"
    default = _DEFAULT_MAX_RESULTS_PR_REVIEW if rep == "github-pr-review" else _DEFAULT_MAX_RESULTS_CHECK
    raw = os.environ.get(key, os.environ.get("REVIEWDOG_MAX_RESULTS", str(default)))
    try:
        return max(1, int(raw))
    except ValueError:
        return default


def _truncate_rdjsonl(stdin: str, *, max_results: int) -> tuple[str, int]:
    lines = [ln for ln in stdin.splitlines() if ln.strip()]
    if len(lines) <= max_results:
        return stdin, 0

    kept = lines[:max_results]
    omitted = len(lines) - max_results
    first = json.loads(kept[0])
    location = first.get("location") or {}
    path = location.get("path") or ".github/workflows/docs-quality.yml"
    synthetic = {
        "message": (
            f"[docs-quality] review output truncated: omitted {omitted} finding(s). "
            "See workflow logs for full diagnostics."
        ),
        "location": {"path": path, "range": {"start": {"line": 1, "column": 1}}},
        "severity": "WARNING",
    }
    kept.append(json.dumps(synthetic, ensure_ascii=False))
    return "\n".join(kept) + "\n", omitted


def _run_reviewdog(
    name: str,
    stdin: str,
    *,
    rep: str,
    extra_args: list[str] | None = None,
) -> subprocess.CompletedProcess[str]:
    cmd = [
        "reviewdog",
        "-f=rdjsonl",
        f"-name={name}",
        f"-reporter={rep}",
        f"-fail-level={fail_level(rep)}",
        f"-filter-mode={filter_mode(rep)}",
        *(extra_args or []),
    ]
    return subprocess.run(cmd, input=stdin, text=True, capture_output=True, check=False)


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
    payload = stdin
    payload, omitted = _truncate_rdjsonl(stdin, max_results=_max_results(rep))
    if omitted:
        print(
            f"reviewdog: truncating {rep} payload by {omitted} finding(s)",
            file=sys.stderr,
        )

    proc = _run_reviewdog(name, payload, rep=rep, extra_args=extra_args)
    if proc.stdout:
        print(proc.stdout, end="")
    if proc.stderr:
        print(proc.stderr, end="", file=sys.stderr)

    if proc.returncode != 0 and rep == "github-pr-review":
        print(
            "reviewdog: github-pr-review reporter failed; falling back to github-check",
            file=sys.stderr,
        )
        check_payload, check_omitted = _truncate_rdjsonl(payload, max_results=_max_results("github-check"))
        if check_omitted:
            print(
                f"reviewdog: truncating github-check payload by {check_omitted} finding(s)",
                file=sys.stderr,
            )
        fb = _run_reviewdog(name, check_payload, rep="github-check", extra_args=extra_args)
        if fb.stdout:
            print(fb.stdout, end="")
        if fb.stderr:
            print(fb.stderr, end="", file=sys.stderr)


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
