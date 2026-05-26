from __future__ import annotations

from collections.abc import Callable

from docs_dev.context import RepoContext
from docs_dev.subprocess_util import run, run_bash_script


def run_setup(
    ctx: RepoContext,
    *,
    with_vale: bool = False,
    on_line: Callable[[str], None] | None = None,
) -> int:
    def log(msg: str) -> None:
        if on_line:
            on_line(msg)

    ctx.doc_lint_install_dir.mkdir(parents=True, exist_ok=True)
    log(f"==> doc linters -> {ctx.doc_lint_install_dir}")

    scripts = [
        ctx.automation_install / "doc-linters.sh",
        ctx.automation_install / "shell-linters.sh",
        ctx.automation_install / "reviewdog.sh",
        ctx.automation_install / "actionlint.sh",
    ]
    for script in scripts:
        log(f"==> {script.name}")
        r = run_bash_script(ctx, script)
        if r.returncode != 0:
            log(r.stderr or r.stdout)
            return r.returncode

    log("==> lychee")
    lychee_install = (
        "set -euo pipefail; "
        f"source {ctx.automation_dir / 'lib' / 'env.sh'}; "
        f"source {ctx.repo_root / '.github' / 'lychee' / 'automation' / 'lib' / 'ci-steps-lychee.sh'}; "
        "lychee_install_cli"
    )
    r = run(ctx, ["bash", "-c", lychee_install])
    if r.returncode != 0:
        log(r.stderr or r.stdout)
        return r.returncode

    log("==> prek")
    run(ctx, ["uv", "tool", "install", "prek"])

    if with_vale:
        log("==> Vale styles")
        r = run_bash_script(ctx, ctx.automation_bin / "vale-sync.sh")
        if r.returncode != 0:
            return r.returncode
    else:
        log("Tip: run vale-sync after changing .vale.ini")

    log("==> prek hooks")
    from docs_dev.runners import hooks

    code = hooks.run_hooks_install(ctx, [])
    if code != 0:
        return code

    log("Setup complete.")
    return 0
