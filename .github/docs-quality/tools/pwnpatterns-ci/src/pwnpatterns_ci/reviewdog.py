"""reviewdog reporter helpers."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

from pwnpatterns_ci.rdjsonl.convert import report_docs_quality_combined

_METADATA_RE = re.compile(
    r"^\s*❌\s+(docs/.+\.md):\s*(.*)$",
    re.MULTILINE,
)
_SHELLCHECK_RE = re.compile(r"^\.github/.*\.sh:\d+:\d+:")
_DEFAULT_MAX_RESULTS_PR_REVIEW = 20
_DEFAULT_MAX_RESULTS_CHECK = 10
_PLATFORM_DOC_PATH_MARKERS = (
    ".github/docs-quality/tools/pwnpatterns-ci/docs/",
    ".github/pwnpatterns-ci/docs/",
    "/.github/docs-quality/tools/pwnpatterns-ci/docs/",
    "/.github/pwnpatterns-ci/docs/",
)


def _repo_cwd() -> str:
    return os.environ.get("REPO_ROOT") or os.environ.get("GITHUB_WORKSPACE") or "."


def _should_fallback_to_check(stderr: str) -> bool:
    # Prefer exhausting PR review comments before creating check annotations.
    raw = os.environ.get("REVIEWDOG_FALLBACK_TO_CHECK", "false").strip().lower()
    if raw not in ("1", "true", "yes", "on"):
        return False
    if "Too many results (annotations) in diff." in stderr:
        return False
    return True


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

    # Keep at least one finding per tool (by message prefix) before filling
    # remaining slots in original order. This prevents one noisy tool from
    # fully starving others (e.g. textlint hiding LanguageTool).
    indexed: list[tuple[int, str, str]] = []
    for i, raw in enumerate(lines):
        try:
            diag = json.loads(raw)
        except json.JSONDecodeError:
            indexed.append((i, "unknown", raw))
            continue
        message = str(diag.get("message") or "")
        m = re.match(r"^\[([^\]]+)\]", message)
        tool = (m.group(1).lower() if m else "unknown")
        indexed.append((i, tool, raw))

    selected: list[int] = []
    seen_tools: set[str] = set()
    for i, tool, _ in indexed:
        if tool in seen_tools:
            continue
        selected.append(i)
        seen_tools.add(tool)
        if len(selected) >= max_results:
            break
    if len(selected) < max_results:
        for i, _, _ in indexed:
            if i in selected:
                continue
            selected.append(i)
            if len(selected) >= max_results:
                break

    selected_set = set(selected)
    kept = [raw for i, raw in enumerate(lines) if i in selected_set][:max_results]
    omitted = len(lines) - max_results
    return "\n".join(kept) + ("\n" if kept else ""), omitted


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
    return subprocess.run(
        cmd,
        input=stdin,
        text=True,
        capture_output=True,
        check=False,
        cwd=_repo_cwd(),
    )


def _normalize_path(path: str) -> str:
    for marker in _PLATFORM_DOC_PATH_MARKERS:
        if marker in path:
            return f"docs/{path.split(marker, 1)[1]}"
    return path


def _parse_rdjsonl_lines(stdin: str) -> list[dict]:
    out: list[dict] = []
    for line in stdin.splitlines():
        raw = line.strip()
        if not raw:
            continue
        try:
            out.append(json.loads(raw))
        except json.JSONDecodeError:
            continue
    return out


def _tool_from_message(message: str) -> str:
    m = re.match(r"^\[([^\]]+)\]", message or "")
    return (m.group(1).lower() if m else "unknown")


def _diagnostic_digest_line(diag: dict) -> str:
    location = diag.get("location") or {}
    path = location.get("path") or "?"
    start = (location.get("range") or {}).get("start") or {}
    line = start.get("line") or 1
    column = start.get("column") or 1
    message = str(diag.get("message") or "issue")
    tool = _tool_from_message(message)
    return f"- `{path}:{line}:{column}` **[{tool}]** {message}"


def _format_overflow_digest(
    diagnostics: list[dict],
    *,
    inline_shown: int,
    omitted: int,
    check_url: str | None,
    workflow_url: str | None,
) -> str:
    lines = [
        "## docs-quality findings digest",
        "",
        f"Posted **{inline_shown}** inline PR review comment(s). "
        f"**{omitted}** additional finding(s) are listed below.",
        "",
    ]
    if check_url:
        lines.append(f"**Full report:** {check_url}")
    if workflow_url:
        lines.append(f"**Workflow run:** {workflow_url}")
    lines.extend(["", "### All findings", ""])
    for diag in diagnostics:
        lines.append(_diagnostic_digest_line(diag))
    return "\n".join(lines) + "\n"


def _github_token() -> str | None:
    return os.environ.get("REVIEWDOG_GITHUB_API_TOKEN") or os.environ.get("GITHUB_TOKEN")


def _workflow_run_url() -> str | None:
    server = (os.environ.get("GITHUB_SERVER_URL") or "https://github.com").rstrip("/")
    repo = os.environ.get("GITHUB_REPOSITORY")
    run_id = os.environ.get("GITHUB_RUN_ID")
    if repo and run_id:
        return f"{server}/{repo}/actions/runs/{run_id}"
    return None


def _github_api(method: str, path: str, payload: dict | None = None) -> dict | None:
    token = _github_token()
    repo = os.environ.get("GITHUB_REPOSITORY")
    if not token or not repo:
        return None
    url = f"https://api.github.com/repos/{repo}/{path.lstrip('/')}"
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "User-Agent": "PwnPatterns-ci/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body) if body.strip() else {}
    except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError, TimeoutError) as exc:
        print(f"reviewdog: GitHub API {method} {path} failed: {exc}", file=sys.stderr)
        return None


def _resolve_pr_number() -> int | None:
    raw = (os.environ.get("GITHUB_PR_NUMBER") or "").strip()
    if raw.isdigit():
        return int(raw)
    proc = subprocess.run(
        ["gh", "pr", "view", "--json", "number", "-q", ".number"],
        capture_output=True,
        text=True,
        check=False,
        cwd=_repo_cwd(),
    )
    if proc.returncode == 0 and proc.stdout.strip().isdigit():
        return int(proc.stdout.strip())
    return None


def _create_summary_check_run(summary: str, *, name: str = "docs-quality") -> str | None:
    sha = os.environ.get("GITHUB_SHA")
    if not sha:
        return None
    if len(summary) > 65000:
        summary = summary[:65000] + "\n\n… (truncated for GitHub check summary limit)"
    resp = _github_api(
        "POST",
        "check-runs",
        {
            "name": name,
            "head_sha": sha,
            "status": "completed",
            "conclusion": "failure",
            "output": {
                "title": "docs-quality findings digest",
                "summary": summary,
            },
        },
    )
    if not resp:
        return None
    return resp.get("html_url") or resp.get("details_url")


def _post_pr_issue_comment(body: str) -> bool:
    pr = _resolve_pr_number()
    if pr is None:
        print("reviewdog: could not resolve PR number for overflow digest comment", file=sys.stderr)
        return False
    resp = _github_api("POST", f"issues/{pr}/comments", {"body": body})
    return resp is not None


def _publish_overflow_report(full_payload: str, *, inline_shown: int, omitted: int) -> None:
    if omitted <= 0:
        return
    diagnostics = _parse_rdjsonl_lines(full_payload)
    if not diagnostics:
        return
    workflow_url = _workflow_run_url()
    digest = _format_overflow_digest(
        diagnostics,
        inline_shown=inline_shown,
        omitted=omitted,
        check_url=None,
        workflow_url=workflow_url,
    )
    check_url = _create_summary_check_run(digest)
    comment = _format_overflow_digest(
        diagnostics,
        inline_shown=inline_shown,
        omitted=omitted,
        check_url=check_url,
        workflow_url=workflow_url,
    )
    if _post_pr_issue_comment(comment):
        print(
            f"reviewdog: posted overflow digest PR comment ({omitted} omitted finding(s))",
            file=sys.stderr,
        )
    elif check_url:
        print(f"reviewdog: overflow digest check run: {check_url}", file=sys.stderr)


def _normalize_rdjsonl_paths(stdin: str) -> str:
    out: list[str] = []
    for line in stdin.splitlines():
        raw = line.strip()
        if not raw:
            continue
        try:
            diag = json.loads(raw)
        except json.JSONDecodeError:
            out.append(line)
            continue
        location = diag.get("location")
        if isinstance(location, dict):
            path = location.get("path")
            if isinstance(path, str) and path:
                location["path"] = _normalize_path(path)
        out.append(json.dumps(diag, ensure_ascii=False))
    return "\n".join(out) + ("\n" if out else "")


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
    full_payload = _normalize_rdjsonl_paths(stdin)
    payload, omitted = _truncate_rdjsonl(full_payload, max_results=_max_results(rep))
    inline_shown = len([ln for ln in payload.splitlines() if ln.strip()])
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

    overflow_omitted = omitted
    if proc.returncode != 0 and rep == "github-pr-review":
        stderr = proc.stderr or ""
        if "Too many results" in stderr:
            total = len(_parse_rdjsonl_lines(full_payload))
            overflow_omitted = max(overflow_omitted, total - inline_shown)

    if rep == "github-pr-review" and overflow_omitted > 0:
        _publish_overflow_report(
            full_payload,
            inline_shown=inline_shown,
            omitted=overflow_omitted,
        )

    if proc.returncode != 0 and rep == "github-pr-review":
        if not _should_fallback_to_check(proc.stderr or ""):
            print(
                "reviewdog: github-pr-review failed; skipping github-check fallback "
                "(prefer PR comments, avoid duplicate annotations)",
                file=sys.stderr,
            )
            return
        print("reviewdog: github-pr-review reporter failed; falling back to github-check", file=sys.stderr)
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
