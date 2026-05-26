from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from docs_dev.context import RepoContext
from docs_dev.models import (
    CheckReport,
    Finding,
    StepResult,
    StepStatus,
    group_findings_by_file,
)
from docs_dev.parsers import lychee, parse_all_lint_logs
from docs_dev.parsers.harper import BLOCKING_PRIORITY
from docs_dev.subprocess_util import (
    run,
    run_bash_script,
    uv_run_tool,
    uv_run_tool_streamed,
    write_exit_code,
    write_log,
)
from docs_dev.template_list_contractions import (
    apply_fixes as apply_template_list_contraction_fixes,
    merge_into_vale_json,
)
from docs_dev.vale_fix import apply_vale_line_fixes, collect_contraction_fixes, load_vale_json

ProgressFn = Callable[[str], None]


def _progress(on_progress: ProgressFn | None, message: str) -> None:
    if on_progress is not None:
        on_progress(message)


@dataclass
class CheckOptions:
    changed: bool = False
    fix: bool = False
    skip_lychee: bool = False
    skip_actionlint: bool = False
    skip_shell: bool = False
    skip_prek: bool = False
    git_base: str = "origin/main"
    git_head: str = "HEAD"


def _setup_job(
    ctx: RepoContext,
    on_progress: ProgressFn | None = None,
    *,
    skip_prek: bool = False,
) -> int:
    _progress(on_progress, "Preparing Harper config…")
    ctx.prepare_harper_config()
    _progress(on_progress, "Syncing allowlists…")
    r = run_bash_script(ctx, ctx.automation_bin / "sync-allowlists.sh")
    if r.returncode != 0:
        return r.returncode
    _progress(on_progress, "Verifying doc linters…")
    r = run_bash_script(ctx, ctx.automation_install / "doc-linters.sh")
    if r.returncode != 0:
        return r.returncode
    _progress(on_progress, "Syncing Vale styles…")
    run_bash_script(ctx, ctx.automation_bin / "vale-sync.sh")
    _progress(on_progress, "Preparing metadata validator…")
    meta_project = ctx.docs_quality_dir / "tools" / "verify-metadata"
    run(ctx, ["uv", "sync", "--directory", str(meta_project)], capture=True)
    if not skip_prek:
        _progress(on_progress, "Ensuring prek is installed…")
        run(ctx, ["uv", "tool", "install", "prek"])
    return 0


def _resolve_paths(ctx: RepoContext, opts: CheckOptions) -> list[str]:
    from docs_dev.paths import all_doc_markdown, changed_doc_markdown

    if opts.changed:
        return changed_doc_markdown(ctx.repo_root, opts.git_base, opts.git_head)
    return all_doc_markdown(ctx.repo_root)


def _write_lint_paths(ctx: RepoContext, paths: list[str]) -> None:
    ctx.lint_log_dir.mkdir(parents=True, exist_ok=True)
    (ctx.lint_log_dir / "lint-paths.lst").write_text(
        "\n".join(paths) + ("\n" if paths else ""),
        encoding="utf-8",
    )


def _apply_autofix(ctx: RepoContext, paths: list[str]) -> None:
    if not paths:
        return
    _run_vale(ctx, paths)
    vale_json = ctx.lint_log_dir / "vale.json"
    if vale_json.is_file():
        fixes = collect_contraction_fixes(load_vale_json(vale_json))
        applied = apply_vale_line_fixes(ctx.repo_root, fixes)
        tpl_applied = apply_template_list_contraction_fixes(ctx.repo_root, paths)
        write_log(
            ctx,
            "vale-fix.log",
            f"applied {applied} Vale + {tpl_applied} template-list PwnPatterns.Contractions substitution(s)\n",
        )
    args = [ctx.tool_path("typos"), "--write-changes", *paths]
    r = run(ctx, args)
    write_log(ctx, "typos-fix.log", (r.stdout or "") + (r.stderr or ""))
    args = [ctx.tool_path("rumdl"), "check", "--fix", *paths]
    r = run(ctx, args)
    write_log(ctx, "rumdl-fix.log", (r.stdout or "") + (r.stderr or ""))


def _run_vale(ctx: RepoContext, paths: list[str]) -> int:
    out = ctx.lint_log_dir / "vale.json"
    err = ctx.lint_log_dir / "vale.stderr"
    r = run(
        ctx,
        [ctx.tool_path("vale"), "--output=JSON", *paths],
    )
    out.write_text(r.stdout, encoding="utf-8")
    err.write_text(r.stderr, encoding="utf-8")
    write_exit_code(ctx, "vale", r.returncode)
    return r.returncode


def _run_typos(ctx: RepoContext, paths: list[str]) -> int:
    out = ctx.lint_log_dir / "typos.json"
    err = ctx.lint_log_dir / "typos.stderr"
    r = run(ctx, [ctx.tool_path("typos"), "--format", "json", *paths])
    out.write_text(r.stdout, encoding="utf-8")
    err.write_text(r.stderr, encoding="utf-8")
    write_exit_code(ctx, "typos", r.returncode)
    return r.returncode


def _run_rumdl(ctx: RepoContext, paths: list[str]) -> int:
    out = ctx.lint_log_dir / "rumdl.json"
    err = ctx.lint_log_dir / "rumdl.stderr"
    r = run(
        ctx,
        [ctx.tool_path("rumdl"), "check", "--output", "json", *paths],
    )
    out.write_text(r.stdout, encoding="utf-8")
    err.write_text(r.stderr, encoding="utf-8")
    write_exit_code(ctx, "rumdl", r.returncode)
    return r.returncode


def _run_harper(ctx: RepoContext, paths: list[str]) -> int:
    out = ctx.lint_log_dir / "harper.json"
    err = ctx.lint_log_dir / "harper.stderr"
    ignore = ctx.manifest.harper_ignore_rules_csv(ctx.repo_root)
    args = [
        ctx.tool_path("harper-cli"),
        "lint",
        *paths,
        "--format",
        "json",
        "--user-dict-path",
        str(ctx.harper_user_dict_path()),
    ]
    if ignore:
        args.extend(["--ignore", ignore])
    r = run(ctx, args)
    out.write_text(r.stdout or "[]", encoding="utf-8")
    err.write_text(r.stderr, encoding="utf-8")
    blocking = 0
    try:
        data = json.loads(r.stdout or "[]")
        for entry in data:
            for lint in entry.get("lints") or []:
                if int(lint.get("priority") or 0) >= BLOCKING_PRIORITY:
                    blocking += 1
    except json.JSONDecodeError:
        blocking = 1
    code = 1 if blocking > 0 else 0
    write_exit_code(ctx, "harper", code)
    return code


def _run_prose_tools(
    ctx: RepoContext,
    paths: list[str],
    *,
    on_progress: ProgressFn | None = None,
) -> bool:
    """Run vale, typos, rumdl, and grammar tools on *paths*. Return True if any tool failed."""
    import os

    from docs_dev.subprocess_util import stream_bash_script

    _write_lint_paths(ctx, paths)
    ctx.lint_log_dir.mkdir(parents=True, exist_ok=True)
    os.environ["DOC_PATHS"] = "\n".join(paths)
    os.environ["REPO_ROOT"] = str(ctx.repo_root)
    os.environ["HARPER_USER_DICT"] = str(ctx.harper_user_dict_path())
    ignore = ctx.manifest.harper_ignore_rules_csv(ctx.repo_root)
    if ignore:
        os.environ["HARPER_IGNORE_RULES"] = ignore
    _progress(
        on_progress,
        f"Prose lint on {len(paths)} file(s) (vale, typos, rumdl, harper, languagetool)…",
    )
    script = ctx.automation_bin / "run-parallel-prose-lint.sh"
    if on_progress is not None:
        code = stream_bash_script(
            ctx,
            script,
            str(ctx.lint_log_dir),
            on_line=on_progress,
        )
    else:
        code = run_bash_script(ctx, script, str(ctx.lint_log_dir)).returncode
    return code != 0 or _prose_failed(ctx)


def _record_lint_exits_from_json(ctx: RepoContext) -> None:
    script = ctx.automation_bin / "record-lint-exits.sh"
    if script.is_file():
        run_bash_script(ctx, script, str(ctx.lint_log_dir))


def run_prose_lint(
    ctx: RepoContext,
    paths: list[str],
    *,
    on_progress: ProgressFn | None = None,
) -> list[Finding]:
    """Run prose linters on *paths* and return findings for those paths only."""
    if not paths:
        return []
    _run_prose_tools(ctx, paths, on_progress=on_progress)
    allowed = set(paths)
    return [f for f in parse_all_lint_logs(ctx.lint_log_dir, paths) if f.path in allowed]


def _parallel_prose_lint(
    ctx: RepoContext,
    paths: list[str],
    *,
    on_progress: ProgressFn | None = None,
) -> StepResult:
    failed = _run_prose_tools(ctx, paths, on_progress=on_progress)
    return StepResult(
        name="prose lint",
        status=StepStatus.FAIL if failed else StepStatus.PASS,
    )


def _run_prek(ctx: RepoContext, on_progress: ProgressFn | None = None) -> StepResult:
    _progress(on_progress, "Running prek hooks…")
    r = run(
        ctx,
        ["prek", "run", "--all-files", "--show-diff-on-failure"],
    )
    return StepResult(
        name="prek",
        status=StepStatus.PASS if r.returncode == 0 else StepStatus.FAIL,
        duration_ms=r.duration_ms,
    )


def _run_metadata(
    ctx: RepoContext,
    paths: list[str],
    on_progress: ProgressFn | None = None,
) -> StepResult:
    _progress(on_progress, f"Verifying metadata on {len(paths)} file(s)…")
    out = ctx.lint_log_dir / "metadata.rdjsonl"
    err = ctx.lint_log_dir / "metadata.stderr"
    project = ctx.docs_quality_dir / "tools" / "verify-metadata"
    env_extra = {"DOCS_DEV_PROGRESS": "1"}
    if on_progress is not None:
        r = uv_run_tool_streamed(
            ctx,
            project,
            "python",
            "verify_metadata.py",
            "--rdjsonl",
            *paths,
            env_extra=env_extra,
            on_line=lambda line: _progress(on_progress, line),
        )
    else:
        r = uv_run_tool(
            ctx,
            project,
            "python",
            "verify_metadata.py",
            "--rdjsonl",
            *paths,
            env_extra=env_extra,
        )
    out.write_text(r.stdout, encoding="utf-8")
    err.write_text(r.stderr, encoding="utf-8")
    write_exit_code(ctx, "metadata", r.returncode)
    _record_lint_exits_from_json(ctx)
    meta_exit = (ctx.lint_log_dir / "metadata.exit").read_text(encoding="utf-8").strip()
    return StepResult(
        name="metadata",
        status=StepStatus.PASS if meta_exit == "0" else StepStatus.FAIL,
        duration_ms=r.duration_ms,
        log_path=str(out),
    )


def _lychee_install_bash(ctx: RepoContext) -> str:
    lychee_lib = ctx.docs_quality_dir.parent / "lychee" / "automation" / "lib" / "ci-steps-lychee.sh"
    return (
        "set -euo pipefail; "
        f"source {ctx.automation_dir / 'lib' / 'env.sh'}; "
        f"source {lychee_lib}; "
        "lychee_install_cli"
    )


def _run_lychee_offline(
    ctx: RepoContext,
    paths: list[str],
    on_progress: ProgressFn | None = None,
) -> StepResult:
    _progress(on_progress, f"Checking cached links (offline) on {len(paths)} file(s)…")
    install = run(ctx, ["bash", "-c", _lychee_install_bash(ctx)])
    if install.returncode != 0:
        detail = (install.stderr or install.stdout or "").strip().splitlines()
        hint = detail[-1] if detail else "lychee install failed"
        return StepResult(
            name="lychee (offline)",
            status=StepStatus.FAIL,
            detail=hint[:200],
        )
    report = ctx.repo_root / "lychee" / "report-offline.json"
    report.parent.mkdir(parents=True, exist_ok=True)
    log = ctx.lint_log_dir / "lychee-offline.log"
    r = run(
        ctx,
        [
            ctx.tool_path("lychee"),
            "--config",
            ".lychee.toml",
            "--offline",
            "--no-progress",
            "--format",
            "json",
            "--output",
            str(report),
            *paths,
        ],
    )
    log.write_text((r.stdout or "") + (r.stderr or ""), encoding="utf-8")
    if not report.is_file():
        tail = (r.stderr or r.stdout or "").strip().splitlines()
        hint = tail[-1][:160] if tail else "no report produced"
        return StepResult(
            name="lychee (offline)",
            status=StepStatus.FAIL,
            detail=hint,
        )
    data = json.loads(report.read_text(encoding="utf-8"))
    errors = int(data.get("errors") or 0)
    status = StepStatus.PASS if errors == 0 else StepStatus.FAIL
    return StepResult(
        name="lychee (offline)",
        status=status,
        detail=f"{errors} cached link error(s)" if errors else None,
    )


def _run_shell(
    ctx: RepoContext,
    *,
    autofix: bool,
    on_progress: ProgressFn | None = None,
) -> StepResult:
    from docs_dev.subprocess_util import stream_bash_script

    label = "shellcheck/shfmt (autofix)…" if autofix else "shellcheck/shfmt…"
    _progress(on_progress, f"Linting {label}")
    env = {"CI_LINT_AUTOFIX": "true"} if autofix else {}
    script = ctx.automation_bin / "lint-shell.sh"
    if on_progress is not None:
        code = stream_bash_script(ctx, script, env_extra=env, on_line=on_progress)
        return StepResult(
            name="shell",
            status=StepStatus.PASS if code == 0 else StepStatus.FAIL,
        )
    r = run_bash_script(ctx, script, env_extra=env)
    return StepResult(
        name="shell",
        status=StepStatus.PASS if r.returncode == 0 else StepStatus.FAIL,
        duration_ms=r.duration_ms,
    )


def _run_actionlint(ctx: RepoContext, on_progress: ProgressFn | None = None) -> StepResult:
    workflows = sorted(ctx.repo_root.glob(".github/workflows/*.yml"))
    if not workflows:
        return StepResult(name="actionlint", status=StepStatus.PASS)
    _progress(on_progress, f"Linting {len(workflows)} workflow(s) with actionlint…")
    r = run(
        ctx,
        [ctx.tool_path("actionlint"), *[str(w) for w in workflows]],
    )
    return StepResult(
        name="actionlint",
        status=StepStatus.PASS if r.returncode == 0 else StepStatus.FAIL,
        duration_ms=r.duration_ms,
    )


def _prose_failed(ctx: RepoContext) -> bool:
    for tool in ("vale", "typos", "rumdl", "harper", "languagetool"):
        exit_file = ctx.lint_log_dir / f"{tool}.exit"
        if exit_file.is_file() and exit_file.read_text(encoding="utf-8").strip() != "0":
            return True
    return False


_PROSE_TOOLS = ("vale", "typos", "rumdl", "harper", "languagetool")


def _stderr_excerpt(ctx: RepoContext, tool: str, *, limit: int = 160) -> str:
    err = ctx.lint_log_dir / f"{tool}.stderr"
    if not err.is_file():
        return ""
    text = err.read_text(encoding="utf-8").strip()
    if not text:
        return ""
    return text.splitlines()[0].strip()[:limit]


def _synthetic_tool_finding(
    ctx: RepoContext,
    *,
    tool: str,
    path: str,
    exit_code: str,
) -> Finding:
    hint = _stderr_excerpt(ctx, tool)
    message = f"{tool} exited {exit_code}"
    if hint:
        message = f"{message}: {hint}"
    else:
        try:
            log_hint = ctx.lint_log_dir.relative_to(ctx.repo_root)
        except ValueError:
            log_hint = ctx.lint_log_dir
        message = f"{message} (see {log_hint}/{tool}.stderr)"
    return Finding(
        tool=tool,
        path=path,
        line=1,
        column=1,
        severity="error",
        message=message,
        rule=f"{tool}.exit",
    )


def _findings_for_unreported_tool_failures(
    ctx: RepoContext,
    paths: list[str],
    findings: list[Finding],
) -> list[Finding]:
    """Tools may exit non-zero without JSON the parsers understand — surface that in the UI."""
    tools_with_findings = {f.tool for f in findings}
    anchor = paths[0] if paths else "docs/"
    extra: list[Finding] = []

    for tool in _PROSE_TOOLS:
        exit_file = ctx.lint_log_dir / f"{tool}.exit"
        if not exit_file.is_file():
            continue
        code = exit_file.read_text(encoding="utf-8").strip()
        if code == "0" or tool in tools_with_findings:
            continue
        extra.append(
            _synthetic_tool_finding(ctx, tool=tool, path=anchor, exit_code=code)
        )

    meta_exit = ctx.lint_log_dir / "metadata.exit"
    if (
        meta_exit.is_file()
        and meta_exit.read_text(encoding="utf-8").strip() != "0"
        and "metadata" not in tools_with_findings
    ):
        code = meta_exit.read_text(encoding="utf-8").strip()
        err = ctx.lint_log_dir / "metadata.stderr"
        hint = ""
        if err.is_file():
            hint = err.read_text(encoding="utf-8").strip().splitlines()
            hint = hint[0][:160] if hint else ""
        message = f"metadata validation exited {code}"
        if hint:
            message = f"{message}: {hint}"
        extra.append(
            Finding(
                tool="metadata",
                path=anchor,
                line=1,
                column=1,
                severity="error",
                message=message,
                rule="metadata.exit",
            )
        )

    if "lychee" not in tools_with_findings:
        log = ctx.lint_log_dir / "lychee-offline.log"
        if log.is_file():
            tail = log.read_text(encoding="utf-8").strip().splitlines()
            if tail and "error" in tail[-1].lower():
                extra.append(
                    Finding(
                        tool="lychee",
                        path=anchor,
                        line=1,
                        column=1,
                        severity="error",
                        message=tail[-1][:200],
                        rule="lychee.offline",
                    )
                )

    return extra


def run_check(
    ctx: RepoContext,
    opts: CheckOptions,
    *,
    on_progress: ProgressFn | None = None,
) -> CheckReport:
    report = CheckReport(
        command="check",
        options={
            "changed": opts.changed,
            "fix": opts.fix,
            "skip_lychee": opts.skip_lychee,
            "skip_actionlint": opts.skip_actionlint,
            "skip_shell": opts.skip_shell,
            "skip_prek": opts.skip_prek,
        },
    )

    if not (ctx.doc_lint_install_dir / "vale").exists():
        report.steps.append(
            StepResult(
                name="setup",
                status=StepStatus.FAIL,
                detail="run docs-dev setup first",
            )
        )
        return report

    _progress(on_progress, "Setting up linters…")
    if _setup_job(ctx, on_progress, skip_prek=opts.skip_prek) != 0:
        report.steps.append(StepResult(name="setup", status=StepStatus.FAIL))
        return report

    paths = _resolve_paths(ctx, opts)
    if not paths:
        _progress(on_progress, "No markdown files to lint.")
        report.steps.append(
            StepResult(name="paths", status=StepStatus.PASS, detail="no markdown to lint")
        )
        return report

    scope = "changed" if opts.changed else "all"
    _progress(on_progress, f"Found {len(paths)} {scope} markdown file(s).")

    if opts.fix:
        _progress(on_progress, "Applying autofix (vale, typos, rumdl)…")
        _apply_autofix(ctx, paths)
        report.steps.append(StepResult(name="autofix", status=StepStatus.PASS))
        report.steps.append(
            _parallel_prose_lint(ctx, paths, on_progress=on_progress)
        )
        if opts.skip_prek:
            report.steps.append(StepResult(name="prek", status=StepStatus.SKIP))
        else:
            report.steps.append(_run_prek(ctx, on_progress))
    else:
        report.steps.append(
            _parallel_prose_lint(ctx, paths, on_progress=on_progress)
        )
        if opts.skip_prek:
            report.steps.append(StepResult(name="prek", status=StepStatus.SKIP))
        else:
            report.steps.append(_run_prek(ctx, on_progress))

    report.steps.append(_run_metadata(ctx, paths, on_progress))

    if opts.skip_lychee:
        report.steps.append(
            StepResult(name="lychee (offline)", status=StepStatus.SKIP)
        )
    else:
        lychee_bin = ctx.doc_lint_install_dir / "lychee"
        if lychee_bin.is_file():
            report.steps.append(_run_lychee_offline(ctx, paths, on_progress))
        else:
            report.steps.append(
                StepResult(
                    name="lychee (offline)",
                    status=StepStatus.FAIL,
                    detail="lychee not installed",
                )
            )

    if opts.skip_shell:
        report.steps.append(StepResult(name="shell", status=StepStatus.SKIP))
    else:
        report.steps.append(_run_shell(ctx, autofix=opts.fix, on_progress=on_progress))

    if opts.skip_actionlint:
        report.steps.append(StepResult(name="actionlint", status=StepStatus.SKIP))
    else:
        report.steps.append(_run_actionlint(ctx, on_progress))

    _progress(on_progress, "Collecting findings…")
    findings = parse_all_lint_logs(ctx.lint_log_dir, paths)
    lychee_report = ctx.repo_root / "lychee" / "report-offline.json"
    if lychee_report.is_file() and not opts.skip_lychee:
        findings.extend(lychee.parse_report(lychee_report))
    findings.extend(_findings_for_unreported_tool_failures(ctx, paths, findings))

    report.files = group_findings_by_file(findings)
    return report
