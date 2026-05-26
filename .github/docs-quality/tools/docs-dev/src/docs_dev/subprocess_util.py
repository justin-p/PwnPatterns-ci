from __future__ import annotations

import subprocess
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from docs_dev.context import RepoContext
from docs_dev.log_util import lines_from_capture, strip_ansi


@dataclass
class RunResult:
    returncode: int
    stdout: str
    stderr: str
    duration_ms: int


def run(
    ctx: RepoContext,
    args: list[str],
    *,
    cwd: Path | None = None,
    env_extra: dict[str, str] | None = None,
    capture: bool = True,
) -> RunResult:
    env = ctx.path_with_tools()
    if env_extra:
        env.update(env_extra)
    start = time.monotonic()
    proc = subprocess.run(
        args,
        cwd=cwd or ctx.repo_root,
        env=env,
        capture_output=capture,
        text=True,
        check=False,
    )
    elapsed = int((time.monotonic() - start) * 1000)
    return RunResult(
        returncode=proc.returncode,
        stdout=proc.stdout or "",
        stderr=proc.stderr or "",
        duration_ms=elapsed,
    )


def run_bash_script(
    ctx: RepoContext,
    script: Path,
    *script_args: str,
    cwd: Path | None = None,
    env_extra: dict[str, str] | None = None,
) -> RunResult:
    return run(
        ctx,
        ["bash", str(script), *script_args],
        cwd=cwd,
        env_extra=env_extra,
    )


def _plain_output_env(env: dict[str, str]) -> dict[str, str]:
    """Disable color/progress styling from child CLIs (e.g. vale sync)."""
    out = dict(env)
    out.setdefault("NO_COLOR", "1")
    out.setdefault("CLICOLOR", "0")
    out.setdefault("TERM", "dumb")
    return out


def emit_captured_output(
    result: RunResult,
    on_line: Callable[[str], None],
) -> None:
    for line in lines_from_capture(result.stdout):
        on_line(line)
    for line in lines_from_capture(result.stderr):
        on_line(line)


def stream_bash_script(
    ctx: RepoContext,
    script: Path,
    *script_args: str,
    cwd: Path | None = None,
    env_extra: dict[str, str] | None = None,
    on_line: Callable[[str], None] | None = None,
) -> int:
    """Run a bash script and stream merged stdout/stderr line-by-line."""
    env = _plain_output_env(ctx.path_with_tools())
    if env_extra:
        env.update(env_extra)
    start = time.monotonic()
    proc = subprocess.Popen(
        ["bash", str(script), *script_args],
        cwd=cwd or ctx.repo_root,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    assert proc.stdout is not None
    for raw in proc.stdout:
        chunk = strip_ansi(raw.rstrip("\n"))
        if not chunk:
            continue
        for segment in chunk.split("\r"):
            line = segment.strip()
            if line and on_line:
                on_line(line)
    proc.wait()
    _ = int((time.monotonic() - start) * 1000)
    return proc.returncode or 0


def uv_run_tool(
    ctx: RepoContext,
    project_dir: Path,
    *args: str,
) -> RunResult:
    env = ctx.path_with_tools()
    clean = {k: v for k, v in env.items() if k != "VIRTUAL_ENV"}
    start = time.monotonic()
    proc = subprocess.run(
        ["uv", "run", "--directory", str(project_dir), *args],
        cwd=ctx.repo_root,
        env=clean,
        capture_output=True,
        text=True,
        check=False,
    )
    elapsed = int((time.monotonic() - start) * 1000)
    return RunResult(
        returncode=proc.returncode,
        stdout=proc.stdout or "",
        stderr=proc.stderr or "",
        duration_ms=elapsed,
    )


def write_log(ctx: RepoContext, name: str, content: str) -> Path:
    ctx.lint_log_dir.mkdir(parents=True, exist_ok=True)
    path = ctx.lint_log_dir / name
    path.write_text(content, encoding="utf-8")
    return path


def write_exit_code(ctx: RepoContext, tool: str, code: int) -> None:
    write_log(ctx, f"{tool}.exit", str(code))
