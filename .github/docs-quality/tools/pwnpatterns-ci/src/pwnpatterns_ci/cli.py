"""Typer CLI for pwnpatterns-ci."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

import typer

from pwnpatterns_ci.checksums import refresh_checksums
from pwnpatterns_ci.config import apply_manifest_to_environ, load_manifest
from pwnpatterns_ci.lint_prose import lint_prose
from pwnpatterns_ci.paths import Layout
from pwnpatterns_ci.pin import verify_pin
from pwnpatterns_ci.report import report_failures
from pwnpatterns_ci.targets import doc_targets, write_github_output

app = typer.Typer(
    name="pwnpatterns-ci",
    help="PwnPatterns documentation quality CI orchestration",
    no_args_is_help=True,
)
ci_app = typer.Typer(help="CI subcommands")
app.add_typer(ci_app, name="ci")


def _layout() -> Layout:
    return Layout.discover()


@ci_app.command("doc-targets")
def cmd_doc_targets() -> None:
    """Emit GITHUB_OUTPUT for documentation scan targets."""
    layout = _layout()
    scan_mode, paths, skip = doc_targets(layout)
    write_github_output(layout, scan_mode, paths, skip)
    if skip:
        typer.echo("No documentation targets for this event.")
        raise typer.Exit(0)
    typer.echo(f"scan_mode={scan_mode} paths={len(paths)}")


@ci_app.command("lint-prose")
def cmd_lint_prose(
    log_dir: Path = typer.Argument(Path("lint-logs"), help="Lint log directory"),
    paths_file: Optional[Path] = typer.Option(
        None, "--paths-file", help="Newline-separated doc paths"
    ),
) -> None:
    """Run vale, typos, rumdl, harper, and languagetool in parallel."""
    layout = _layout()
    if paths_file and paths_file.is_file():
        paths = [ln.strip() for ln in paths_file.read_text(encoding="utf-8").splitlines() if ln.strip()]
    elif os.environ.get("DOC_PATHS"):
        paths = [ln.strip() for ln in os.environ["DOC_PATHS"].splitlines() if ln.strip()]
    else:
        _, paths, skip = doc_targets(layout)
        if skip or not paths:
            raise typer.Exit("no paths to lint")
    lint_prose(layout, paths, log_dir.resolve())


@ci_app.command("record-exits")
def cmd_record_exits(log_dir: Path = typer.Argument(Path("lint-logs"))) -> None:
    from pwnpatterns_ci.report import record_lint_exits

    record_lint_exits(log_dir.resolve())


@ci_app.command("report-failures")
def cmd_report_failures(log_dir: Path = typer.Argument(Path("lint-logs"))) -> None:
    raise typer.Exit(report_failures(log_dir.resolve()))


@ci_app.command("verify-pin")
def cmd_verify_pin() -> None:
    """Verify .github/platform.ref matches workflow uses: SHAs."""
    layout = _layout()
    errors = verify_pin(layout.repo_root)
    for err in errors:
        typer.echo(f"verify-pin: {err}", err=True)
    if errors:
        raise typer.Exit(1)
    typer.echo("verify-pin: OK")


@ci_app.command("refresh-checksums")
def cmd_refresh_checksums() -> None:
    """Update *_SHA256 lines in platform manifest.env."""
    layout = _layout()
    apply_manifest_to_environ(layout)
    refresh_checksums(layout)
    typer.echo(f"Updated {layout.manifest_path()}")


@ci_app.command("prose-to-rdjsonl")
def cmd_prose_to_rdjsonl(
    tool: str = typer.Argument(..., help="vale|typos|rumdl|harper|languagetool"),
    log_dir: Path = typer.Argument(Path("lint-logs")),
) -> None:
    """Pipe tool JSON through jq rdjsonl filter (stdout)."""
    layout = _layout()
    sh = layout.automation_dir / "bin" / "prose-to-rdjsonl.sh"
    if not sh.is_file():
        raise typer.Exit(f"missing {sh}")
    subprocess.run(["bash", str(sh), tool, str(log_dir)], check=True)


@ci_app.command("sync-allowlists")
def cmd_sync_allowlists() -> None:
    layout = _layout()
    sh = layout.automation_dir / "bin" / "sync-allowlists.sh"
    subprocess.run(["bash", str(sh)], cwd=layout.repo_root, check=True)


@ci_app.command("install-linters")
def cmd_install_linters() -> None:
    layout = _layout()
    apply_manifest_to_environ(layout)
    sh = layout.automation_dir / "install" / "doc-linters.sh"
    subprocess.run(["bash", str(sh)], cwd=layout.repo_root, check=True)


@ci_app.command("vale-sync")
def cmd_vale_sync() -> None:
    layout = _layout()
    sh = layout.automation_dir / "bin" / "vale-sync.sh"
    subprocess.run(["bash", str(sh)], cwd=layout.repo_root, check=True)


@ci_app.command("run-e2e")
def cmd_run_e2e(
    job: str = typer.Option("all", "--job"),
    smoke_docs: bool = typer.Option(False, "--smoke-docs"),
) -> None:
    layout = _layout()
    sh = layout.automation_dir / "bin" / "run-ci-e2e.sh"
    args = ["bash", str(sh), "--job", job]
    if smoke_docs:
        args.append("--smoke-docs")
    subprocess.run(args, cwd=layout.repo_root, check=True)


if __name__ == "__main__":
    app()
