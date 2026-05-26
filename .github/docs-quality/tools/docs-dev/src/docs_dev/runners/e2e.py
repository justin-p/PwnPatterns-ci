from __future__ import annotations

from pathlib import Path

from docs_dev.context import RepoContext
from docs_dev.subprocess_util import run_bash_script


def _component_tests_script(ctx: RepoContext) -> Path:
    for candidate in (
        ctx.repo_root / ".github/pwnpatterns-ci/.github/tests/run-component-tests.sh",
        ctx.repo_root / ".github/tests/run-component-tests.sh",
        ctx.docs_quality_dir.parent / "tests/run-component-tests.sh",
    ):
        if candidate.is_file():
            return candidate
    msg = "run-component-tests.sh not found (run scripts/ensure-platform.sh)"
    raise FileNotFoundError(msg)


def run_e2e(ctx: RepoContext, extra_args: list[str]) -> int:
    return run_bash_script(
        ctx,
        ctx.automation_bin / "run-ci-e2e.sh",
        *extra_args,
    ).returncode


def run_test(ctx: RepoContext) -> int:
    return run_bash_script(ctx, _component_tests_script(ctx)).returncode
