from __future__ import annotations

import os
import sys
from enum import Enum
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from docs_dev.context import RepoContext
from docs_dev.output.json_export import render_json
from docs_dev.output.plain import render_plain
from docs_dev.runners.check import CheckOptions, run_check
from docs_dev.runners.setup import run_setup

CLI_COMMANDS = frozenset({"setup"})

app = typer.Typer(
    name="docs-dev",
    help="PwnPatterns documentation quality (local)",
    no_args_is_help=False,
    add_completion=False,
    invoke_without_command=True,
)
console = Console(stderr=True)


class OutputFormat(str, Enum):
    rich = "rich"
    json = "json"
    plain = "plain"


def _ctx() -> RepoContext:
    return RepoContext.from_env()


def _emit_check_report(report, fmt: OutputFormat) -> None:
    if fmt == OutputFormat.json:
        sys.stdout.write(render_json(report))
        sys.stdout.write("\n")
    elif fmt == OutputFormat.plain:
        sys.stdout.write(render_plain(report))
    else:
        table = Table(title="Check summary")
        table.add_column("Step")
        table.add_column("Status")
        for step in report.steps:
            table.add_row(step.name, step.status.value)
        console.print(table)
        if report.files:
            console.print(
                f"\n[bold]{sum(ff.count for ff in report.files)}[/] finding(s) "
                f"in [bold]{len(report.files)}[/] file(s)\n"
            )
            for ff in report.files[:40]:
                console.print(f"[cyan]{ff.path}[/] ({ff.count})")
                for f in ff.findings[:8]:
                    loc = f"{f.line}:{f.column}"
                    console.print(f"  [{f.tool}] {loc}: {f.message}")
                if ff.count > 8:
                    console.print(f"  … {ff.count - 8} more in this file")
            if len(report.files) > 40:
                console.print(f"… {len(report.files) - 40} more files (see lint-logs/)")
        else:
            console.print("[green]No findings[/]")
        if not report.passed:
            console.print(
                "\n[yellow]Some checks failed. See lint-logs/ or use --format json[/]"
            )


@app.command("setup")
def setup_cmd(
    with_vale: Annotated[
        bool, typer.Option("--with-vale", help="Sync Vale styles after install")
    ] = False,
) -> None:
    """Install pinned CLIs, lychee, and prek hooks."""
    ctx = _ctx()

    def on_line(msg: str) -> None:
        console.print(msg)

    raise typer.Exit(run_setup(ctx, with_vale=with_vale, on_line=on_line))


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    changed: Annotated[
        bool,
        typer.Option(
            "--changed",
            help="Lint docs changed on the branch vs origin/main plus local edits",
        ),
    ] = False,
    fix: Annotated[
        bool, typer.Option("--fix", help="Apply typos/rumdl/shfmt fixes, then re-check")
    ] = False,
    skip_lychee: Annotated[bool, typer.Option("--skip-lychee")] = False,
    lychee_offline: Annotated[
        bool,
        typer.Option(
            "--lychee-offline",
            help="Only check URLs already in lychee cache (skips never-seen links)",
        ),
    ] = False,
    skip_actionlint: Annotated[bool, typer.Option("--skip-actionlint")] = False,
    skip_prek: Annotated[
        bool,
        typer.Option(
            "--skip-prek",
            help="Skip prek (full-repo hooks); default in TUI, use for faster local checks",
        ),
    ] = False,
    format: Annotated[
        OutputFormat, typer.Option("--format", help="Output format (non-TUI)")
    ] = OutputFormat.rich,
    no_ui: Annotated[
        bool, typer.Option("--no-ui", help="Run check in CLI (no Textual)")
    ] = False,
) -> None:
    """Run the documentation quality check (default when using --no-ui)."""
    if ctx.invoked_subcommand is not None:
        return
    del no_ui
    ctx = _ctx()
    opts = CheckOptions(
        changed=changed,
        fix=fix,
        skip_lychee=skip_lychee,
        lychee_offline=lychee_offline,
        skip_actionlint=skip_actionlint,
        skip_prek=skip_prek,
    )
    def on_progress(message: str) -> None:
        console.print(message)

    report = run_check(ctx, opts, on_progress=on_progress)
    _emit_check_report(report, format)
    raise typer.Exit(0 if report.passed else 1)


def dispatch(argv: list[str] | None = None) -> int:
    """Run Typer CLI; return exit code."""
    from typer.main import get_command

    args = list(argv) if argv is not None else sys.argv[1:]
    command = get_command(app)
    try:
        command.main(args=args, prog_name="docs-dev", standalone_mode=False)
        return 0
    except typer.Exit as exc:
        return int(exc.code) if exc.code is not None else 0


def parse_global_flags(argv: list[str]) -> tuple[bool, OutputFormat | None, bool]:
    no_ui = "--no-ui" in argv
    changed = "--changed" in argv
    fmt: OutputFormat | None = None
    for i, arg in enumerate(argv):
        if arg == "--format" and i + 1 < len(argv):
            try:
                fmt = OutputFormat(argv[i + 1])
            except ValueError:
                pass
        if arg.startswith("--format="):
            try:
                fmt = OutputFormat(arg.split("=", 1)[1])
            except ValueError:
                pass
    return no_ui, fmt, changed


def _is_textual_web() -> bool:
    driver = os.environ.get("TEXTUAL_DRIVER", "")
    return "web_driver" in driver or driver.endswith("WebDriver")


def should_use_tui(argv: list[str]) -> bool:
    if "check" in argv or "fix" in argv:
        return False
    if argv and argv[0] in CLI_COMMANDS:
        return False
    if _is_textual_web():
        return True
    no_ui, fmt, _ = parse_global_flags(argv)
    if no_ui or fmt in (OutputFormat.json, OutputFormat.plain):
        return False
    if not sys.stdout.isatty():
        return False
    return True
