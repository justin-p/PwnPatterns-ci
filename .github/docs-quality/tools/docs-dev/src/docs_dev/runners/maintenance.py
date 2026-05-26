from __future__ import annotations

from collections.abc import Callable

from docs_dev.context import RepoContext
from docs_dev.subprocess_util import run_bash_script, stream_bash_script


def run_sync(ctx: RepoContext, on_line: Callable[[str], None] | None = None) -> int:
    script = ctx.automation_bin / "sync-allowlists.sh"
    if on_line:
        return stream_bash_script(ctx, script, on_line=on_line)
    return run_bash_script(ctx, script).returncode


def run_vale_sync(ctx: RepoContext, on_line: Callable[[str], None] | None = None) -> int:
    script = ctx.automation_bin / "vale-sync.sh"
    if on_line:
        return stream_bash_script(ctx, script, on_line=on_line)
    return run_bash_script(ctx, script).returncode


def run_shell(
    ctx: RepoContext,
    *,
    fix: bool = False,
    on_line: Callable[[str], None] | None = None,
) -> int:
    env = {"CI_LINT_AUTOFIX": "true"} if fix else None
    script = ctx.automation_bin / "lint-shell.sh"
    if on_line:
        return stream_bash_script(ctx, script, env_extra=env, on_line=on_line)
    return run_bash_script(ctx, script, env_extra=env).returncode


def run_checksums(ctx: RepoContext, on_line: Callable[[str], None] | None = None) -> int:
    script = ctx.automation_bin / "refresh-checksums.sh"
    if on_line:
        return stream_bash_script(ctx, script, on_line=on_line)
    return run_bash_script(ctx, script).returncode


def run_harper(ctx: RepoContext, on_line: Callable[[str], None] | None = None) -> int:
    script = ctx.automation_bin / "harper-lint-issues.sh"
    if on_line:
        return stream_bash_script(ctx, script, on_line=on_line)
    return run_bash_script(ctx, script).returncode
