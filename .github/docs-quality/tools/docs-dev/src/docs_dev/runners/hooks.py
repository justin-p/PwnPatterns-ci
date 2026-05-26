from __future__ import annotations

from docs_dev.context import RepoContext
from docs_dev.subprocess_util import run


def run_hooks_install(ctx: RepoContext, extra_args: list[str]) -> int:
    run(ctx, ["uv", "tool", "install", "prek"])
    args = ["prek", "install", *extra_args]
    return run(ctx, args).returncode


def run_hooks_run(ctx: RepoContext) -> int:
    return run(
        ctx,
        ["prek", "run", "--all-files", "--show-diff-on-failure"],
    ).returncode
