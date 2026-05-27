from __future__ import annotations

from collections.abc import Callable

from docs_dev.context import RepoContext
from docs_dev.subprocess_util import run, uv_run_tool


def run_setup(
    ctx: RepoContext,
    *,
    with_vale: bool = False,
    on_line: Callable[[str], None] | None = None,
) -> int:
    def log(msg: str) -> None:
        if on_line:
            on_line(msg)

    pci = ctx.docs_quality_dir / "tools" / "pwnpatterns-ci"
    ctx.doc_lint_install_dir.mkdir(parents=True, exist_ok=True)
    log(f"==> doc linters -> {ctx.doc_lint_install_dir}")

    for cmd in (
        ["pwnpatterns-ci", "install-linters"],
        ["pwnpatterns-ci", "install-shell-linters"],
        ["pwnpatterns-ci", "install-reviewdog"],
        ["pwnpatterns-ci", "install-actionlint"],
    ):
        log(f"==> {' '.join(cmd)}")
        r = uv_run_tool(ctx, pci, *cmd)
        if r.returncode != 0:
            log(r.stderr or r.stdout)
            return r.returncode

    log("==> lychee")
    lychee_install = (
        "set -euo pipefail; "
        f"source {ctx.docs_quality_dir.parent / 'lychee' / 'automation' / 'lib' / 'ci-steps-lychee.sh'}; "
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
        r = uv_run_tool(ctx, pci, "pwnpatterns-ci", "vale-sync")
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
