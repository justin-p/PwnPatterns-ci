from __future__ import annotations

from collections.abc import Callable

from docs_dev.context import RepoContext
from docs_dev.subprocess_util import uv_run_tool, uv_run_tool_streamed


def _pci(ctx: RepoContext):
    return ctx.docs_quality_dir / "tools" / "pwnpatterns-ci"


def run_sync(ctx: RepoContext, on_line: Callable[[str], None] | None = None) -> int:
    if on_line:
        return uv_run_tool_streamed(
            ctx, _pci(ctx), "pwnpatterns-ci", "sync-allowlists", on_line=on_line
        ).returncode
    return uv_run_tool(ctx, _pci(ctx), "pwnpatterns-ci", "sync-allowlists").returncode


def run_vale_sync(ctx: RepoContext, on_line: Callable[[str], None] | None = None) -> int:
    if on_line:
        return uv_run_tool_streamed(
            ctx, _pci(ctx), "pwnpatterns-ci", "vale-sync", on_line=on_line
        ).returncode
    return uv_run_tool(ctx, _pci(ctx), "pwnpatterns-ci", "vale-sync").returncode


def run_shell(
    ctx: RepoContext,
    *,
    fix: bool = False,
    on_line: Callable[[str], None] | None = None,
) -> int:
    args = ["pwnpatterns-ci", "lint-shell", "--include-platform"]
    if fix:
        args.append("--autofix")
    if on_line:
        return uv_run_tool_streamed(ctx, _pci(ctx), *args, on_line=on_line).returncode
    return uv_run_tool(ctx, _pci(ctx), *args).returncode


def run_checksums(ctx: RepoContext, on_line: Callable[[str], None] | None = None) -> int:
    if on_line:
        return uv_run_tool_streamed(
            ctx, _pci(ctx), "pwnpatterns-ci", "refresh-checksums", on_line=on_line
        ).returncode
    return uv_run_tool(ctx, _pci(ctx), "pwnpatterns-ci", "refresh-checksums").returncode


def run_harper(ctx: RepoContext, on_line: Callable[[str], None] | None = None) -> int:
    """Harper maintenance is covered by docs-dev check prose lane."""
    if on_line:
        on_line("Harper issues are reported during docs-dev check (prose lint).")
    return 0
