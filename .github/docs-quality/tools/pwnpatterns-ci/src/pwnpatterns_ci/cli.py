"""Typer CLI for pwnpatterns-ci (flat commands)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

import typer

from pwnpatterns_ci.checksums import refresh_checksums
from pwnpatterns_ci.config import apply_manifest_to_environ, load_manifest
from pwnpatterns_ci.e2e import run_e2e
from pwnpatterns_ci.install import (
    install_actionlint,
    install_doc_linters,
    install_reviewdog,
    install_shell_linters,
)
from pwnpatterns_ci.jobs import (
    actionlint_job,
    lint_shell,
    report_reviewdog,
    run_prek,
    verify_metadata,
)
from pwnpatterns_ci.lint_prose import lint_prose
from pwnpatterns_ci.paths import Layout
from pwnpatterns_ci.paths_util import expand_doc_paths
from pwnpatterns_ci.pin import verify_pin
from pwnpatterns_ci.rdjsonl.convert import prose_to_rdjsonl
from pwnpatterns_ci.report import report_failures
from pwnpatterns_ci.targets import doc_targets, write_github_output

app = typer.Typer(
    name="pwnpatterns-ci",
    help="PwnPatterns documentation quality CI orchestration",
    no_args_is_help=True,
)


def _layout() -> Layout:
    return Layout.discover()


def _apply_manifest(layout: Layout) -> None:
    load_manifest(layout)
    apply_manifest_to_environ(layout)


@app.command("doc-targets")
def cmd_doc_targets() -> None:
    """Emit GITHUB_OUTPUT for documentation scan targets."""
    layout = _layout()
    scan_mode, paths, skip = doc_targets(layout)
    write_github_output(layout, scan_mode, paths, skip)
    if skip:
        typer.echo("No documentation targets for this event.")
        raise typer.Exit(0)
    typer.echo(f"scan_mode={scan_mode} paths={len(paths)}")


@app.command("load-doc-paths")
def cmd_load_doc_paths(multiline: str = typer.Argument(..., help="GHA multiline paths output")) -> None:
    """Print newline-separated doc paths (stdout)."""
    typer.echo(expand_doc_paths(multiline), nl=False)


@app.command("lint-prose")
def cmd_lint_prose(
    log_dir: Path = typer.Argument(Path("lint-logs"), help="Lint log directory"),
    paths_file: Optional[Path] = typer.Option(
        None, "--paths-file", help="Newline-separated doc paths"
    ),
) -> None:
    """Run vale, typos, rumdl, harper, and languagetool in parallel."""
    layout = _layout()
    if paths_file and paths_file.is_file():
        paths = [
            ln.strip()
            for ln in paths_file.read_text(encoding="utf-8").splitlines()
            if ln.strip()
        ]
    elif os.environ.get("DOC_PATHS"):
        paths = [ln.strip() for ln in os.environ["DOC_PATHS"].splitlines() if ln.strip()]
    else:
        _, paths, skip = doc_targets(layout)
        if skip or not paths:
            raise typer.Exit("no paths to lint")
    lint_prose(layout, paths, layout.resolve_log_dir(log_dir))


@app.command("record-exits")
def cmd_record_exits(log_dir: Path = typer.Argument(Path("lint-logs"))) -> None:
    from pwnpatterns_ci.report import record_lint_exits

    layout = _layout()
    record_lint_exits(layout.resolve_log_dir(log_dir))


@app.command("report-failures")
def cmd_report_failures(log_dir: Path = typer.Argument(Path("lint-logs"))) -> None:
    layout = _layout()
    raise typer.Exit(report_failures(layout.resolve_log_dir(log_dir)))


@app.command("verify-pin")
def cmd_verify_pin() -> None:
    """Verify .github/platform.ref matches workflow uses: SHAs."""
    layout = _layout()
    errors = verify_pin(layout.repo_root)
    for err in errors:
        typer.echo(f"verify-pin: {err}", err=True)
    if errors:
        raise typer.Exit(1)
    typer.echo("verify-pin: OK")


@app.command("refresh-checksums")
def cmd_refresh_checksums() -> None:
    """Update *_SHA256 lines in platform manifest.env."""
    layout = _layout()
    _apply_manifest(layout)
    refresh_checksums(layout)
    typer.echo(f"Updated {layout.manifest_path()}")


@app.command("prose-to-rdjsonl")
def cmd_prose_to_rdjsonl(
    tool: str = typer.Argument(..., help="vale|typos|textlint|rumdl|harper|languagetool"),
    log_dir: Path = typer.Argument(Path("lint-logs")),
) -> None:
    """Convert lint log JSON to reviewdog rdjsonl on stdout."""
    layout = _layout()
    resolved = layout.resolve_log_dir(log_dir)
    sys.stdout.write(prose_to_rdjsonl(tool, resolved))


@app.command("sync-allowlists")
def cmd_sync_allowlists() -> None:
    layout = _layout()
    tool = layout.docs_quality_dir / "tools" / "sync-allowlists" / "sync_allowlists.py"
    subprocess.run([sys.executable, str(tool)], cwd=layout.repo_root, check=True)


@app.command("install-linters")
def cmd_install_linters() -> None:
    layout = _layout()
    _apply_manifest(layout)
    install_doc_linters(layout)


@app.command("install-shell-linters")
def cmd_install_shell_linters() -> None:
    _apply_manifest(_layout())
    install_shell_linters()


@app.command("install-actionlint")
def cmd_install_actionlint() -> None:
    _apply_manifest(_layout())
    install_actionlint()


@app.command("install-reviewdog")
def cmd_install_reviewdog() -> None:
    _apply_manifest(_layout())
    install_reviewdog()


@app.command("vale-sync")
def cmd_vale_sync() -> None:
    layout = _layout()
    subprocess.run(["vale", "sync"], cwd=layout.repo_root, check=True)


@app.command("verify-metadata")
def cmd_verify_metadata(
    log_dir: Path = typer.Argument(Path("lint-logs")),
    scan_mode: str = typer.Option("changed", "--scan-mode"),
    paths_file: Path = typer.Option(..., "--paths-file"),
) -> None:
    layout = _layout()
    paths = [
        ln.strip() for ln in paths_file.read_text(encoding="utf-8").splitlines() if ln.strip()
    ]
    ec = verify_metadata(layout, layout.resolve_log_dir(log_dir), paths, scan_mode)
    raise typer.Exit(ec)


@app.command("run-prek")
def cmd_run_prek(log_dir: Path = typer.Argument(Path("lint-logs"))) -> None:
    ec = run_prek(_layout().resolve_log_dir(log_dir))
    raise typer.Exit(ec)


@app.command("report-reviewdog")
def cmd_report_reviewdog(
    log_dir: Path = typer.Argument(Path("lint-logs")),
    reporter_name: Optional[str] = typer.Option(None, "--reporter"),
) -> None:
    report_reviewdog(_layout().resolve_log_dir(log_dir), rep=reporter_name)


@app.command("lint-shell")
def cmd_lint_shell(
    include_platform: bool = typer.Option(False, "--include-platform"),
    autofix: bool = typer.Option(False, "--autofix"),
) -> None:
    layout = _layout()
    _apply_manifest(layout)
    raise typer.Exit(lint_shell(layout, include_platform=include_platform, autofix=autofix))


@app.command("actionlint-job")
def cmd_actionlint_job(log_dir: Path = typer.Argument(Path("lint-logs"))) -> None:
    layout = _layout()
    _apply_manifest(layout)
    ec = actionlint_job(layout, layout.resolve_log_dir(log_dir))
    raise typer.Exit(ec)


@app.command("run-e2e")
def cmd_run_e2e(
    job: str = typer.Option("all", "--job"),
    smoke_docs: bool = typer.Option(False, "--smoke-docs"),
    skip_lychee: bool = typer.Option(False, "--skip-lychee"),
    include_dashboard: bool = typer.Option(False, "--include-dashboard"),
    component_only: bool = typer.Option(False, "--component-tests-only"),
) -> None:
    layout = _layout()
    _apply_manifest(layout)
    run_e2e(
        layout,
        job=job,
        smoke_docs=smoke_docs,
        skip_lychee=skip_lychee,
        include_dashboard=include_dashboard,
        component_only=component_only,
    )


if __name__ == "__main__":
    app()
