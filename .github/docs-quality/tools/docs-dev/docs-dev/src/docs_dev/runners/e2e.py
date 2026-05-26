from __future__ import annotations

from docs_dev.context import RepoContext
from docs_dev.subprocess_util import run_bash_script


def run_e2e(ctx: RepoContext, extra_args: list[str]) -> int:
    return run_bash_script(
        ctx,
        ctx.automation_bin / "run-ci-e2e.sh",
        *extra_args,
    ).returncode


def run_test(ctx: RepoContext) -> int:
    return run_bash_script(
        ctx,
        ctx.repo_root / ".github" / "tests" / "run-component-tests.sh",
    ).returncode
