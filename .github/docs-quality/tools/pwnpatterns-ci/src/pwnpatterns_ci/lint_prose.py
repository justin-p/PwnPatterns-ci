"""Parallel prose lint (vale, typos/textlint, rumdl, harper, languagetool)."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from pwnpatterns_ci.config import apply_manifest_to_environ, load_manifest
from pwnpatterns_ci.paths import Layout
from pwnpatterns_ci.report import record_lint_exits


def _grammar_smoke_paths(layout: Layout) -> list[str]:
    cfg = layout.consumer_config_dir / "language-tools.yml"
    defaults = [".github/tests/fixtures/nl-languagetool-smoke.md"]
    if not cfg.is_file():
        return defaults
    import re

    paths: list[str] = []
    in_section = False
    for line in cfg.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("grammar_smoke_paths:"):
            in_section = True
            continue
        if in_section and line.strip().startswith("- "):
            paths.append(line.strip()[2:].strip().strip("'\""))
        elif in_section and line.strip() and not line.startswith(" "):
            break
    return paths or defaults


def merge_paths(layout: Layout, paths: list[str]) -> list[str]:
    out = list(paths)
    for rel in _grammar_smoke_paths(layout):
        full = layout.repo_root / rel
        if full.is_file() and rel not in out:
            out.append(rel)
    platform_smoke = (
        layout.docs_quality_dir.parent.parent
        / "tests"
        / "fixtures"
        / "nl-languagetool-smoke.md"
    )
    if platform_smoke.is_file():
        rel = layout.rel(platform_smoke)
        if rel not in out:
            out.append(rel)
    return out


def build_path_index(log_dir: Path, paths: list[str]) -> None:
    index: dict[str, str] = {}
    for p in paths:
        base = Path(p).name
        index[base] = p
    (log_dir / "path-index.json").write_text(json.dumps(index), encoding="utf-8")


def route_grammar(layout: Layout, log_dir: Path) -> None:
    bin_sh = layout.automation_dir / "bin" / "route-grammar-paths.sh"
    if bin_sh.is_file():
        subprocess.run(
            ["bash", str(bin_sh), str(log_dir)],
            cwd=layout.repo_root,
            check=True,
            env=os.environ.copy(),
        )


def _run(
    cmd: list[str],
    log: Path,
    stderr: Path,
    *,
    cwd: Path | str | None = None,
    empty_json: str = "[]",
) -> None:
    log.parent.mkdir(parents=True, exist_ok=True)
    run_cwd = cwd if cwd is not None else os.environ.get("REPO_ROOT", ".")
    with log.open("w", encoding="utf-8") as out, stderr.open("w", encoding="utf-8") as err:
        r = subprocess.run(cmd, stdout=out, stderr=err, cwd=run_cwd)
    if r.returncode != 0 and not log.stat().st_size:
        log.write_text(empty_json, encoding="utf-8")


def lint_prose(layout: Layout, paths: list[str], log_dir: Path) -> None:
    apply_manifest_to_environ(layout, load_manifest(layout))
    paths = merge_paths(layout, paths)
    if not paths:
        raise SystemExit("lint prose: no documentation paths")

    log_dir.mkdir(parents=True, exist_ok=True)
    (log_dir / "lint-paths.lst").write_text("\n".join(paths) + "\n", encoding="utf-8")
    build_path_index(log_dir, paths)
    route_grammar(layout, log_dir)

    install = os.environ.get("PATH", "")
    doc_bin = os.environ.get("DOC_LINT_INSTALL_DIR", "/tmp")
    env = os.environ.copy()
    env["PATH"] = f"{doc_bin}:{install}"

    harper_paths: list[str] = []
    hp = log_dir / "grammar-harper-paths.lst"
    if hp.is_file():
        harper_paths = [ln.strip() for ln in hp.read_text(encoding="utf-8").splitlines() if ln.strip()]
    typos_paths: list[str] = []
    tp = log_dir / "spelling-typos-paths.lst"
    if tp.is_file():
        typos_paths = [ln.strip() for ln in tp.read_text(encoding="utf-8").splitlines() if ln.strip()]
    textlint_paths: list[str] = []
    tl = log_dir / "spelling-textlint-paths.lst"
    if tl.is_file():
        textlint_paths = [ln.strip() for ln in tl.read_text(encoding="utf-8").splitlines() if ln.strip()]

    dict_path = os.environ.get("HARPER_USER_DICT", "")
    ignore = os.environ.get("HARPER_IGNORE_RULES", "")

    tasks: list[tuple[str, callable]] = []

    def vale() -> None:
        _run(
            ["vale", "--output=JSON", *paths],
            log_dir / "vale.json",
            log_dir / "vale.stderr",
            empty_json="{}",
        )

    def typos() -> None:
        if typos_paths:
            _run(
                ["typos", "--format", "json", *typos_paths],
                log_dir / "typos.json",
                log_dir / "typos.stderr",
            )
        else:
            (log_dir / "typos.json").write_text("", encoding="utf-8")
            (log_dir / "typos.stderr").write_text("", encoding="utf-8")

    def textlint() -> None:
        if not textlint_paths:
            (log_dir / "textlint.json").write_text("[]", encoding="utf-8")
            (log_dir / "textlint.stderr").write_text("", encoding="utf-8")
            return
        textlint_cfg = layout.docs_quality_dir / "config" / "textlint"
        if not textlint_cfg.is_dir():
            (log_dir / "textlint.json").write_text("[]", encoding="utf-8")
            (log_dir / "textlint.stderr").write_text(
                "textlint config missing; lane skipped\n",
                encoding="utf-8",
            )
            return
        if not shutil.which("bun"):
            (log_dir / "textlint.json").write_text("[]", encoding="utf-8")
            (log_dir / "textlint.stderr").write_text(
                "bun not found; textlint lane skipped\n",
                encoding="utf-8",
            )
            return
        repo = Path(os.environ.get("REPO_ROOT", layout.repo_root))
        abs_paths = [
            p if Path(p).is_absolute() else str((repo / p).resolve())
            for p in textlint_paths
        ]
        _run(
            [
                "bunx",
                "textlint",
                "--config",
                ".textlintrc.json",
                "--format",
                "json",
                *abs_paths,
            ],
            log_dir / "textlint.json",
            log_dir / "textlint.stderr",
            cwd=textlint_cfg,
            empty_json="[]",
        )

    def rumdl() -> None:
        _run(
            ["rumdl", "check", "--output", "json", *paths],
            log_dir / "rumdl.json",
            log_dir / "rumdl.stderr",
        )

    def harper() -> None:
        if harper_paths and dict_path:
            cmd = [
                "harper-cli",
                "lint",
                *harper_paths,
                "--format",
                "json",
                "--user-dict-path",
                dict_path,
            ]
            if ignore:
                cmd.extend(["--ignore", ignore])
            _run(cmd, log_dir / "harper.json", log_dir / "harper.stderr")
        else:
            (log_dir / "harper.json").write_text("[]", encoding="utf-8")
            (log_dir / "harper.stderr").write_text("", encoding="utf-8")

    def languagetool() -> None:
        tsv = log_dir / "grammar-languagetool.tsv"
        if not tsv.is_file() or tsv.stat().st_size == 0:
            (log_dir / "languagetool.json").write_text("[]", encoding="utf-8")
            return
        gr = layout.tools_dir / "grammar-routing"
        subprocess.run(
            [
                "uv",
                "run",
                "--directory",
                str(gr),
                "python",
                "run_languagetool_batch.py",
                "--log-dir",
                str(log_dir),
                "--repo-root",
                str(layout.repo_root),
            ],
            cwd=layout.repo_root,
            env=env,
            check=False,
        )

    for name, fn in [
        ("vale", vale),
        ("typos", typos),
        ("textlint", textlint),
        ("rumdl", rumdl),
        ("harper", harper),
        ("languagetool", languagetool),
    ]:
        tasks.append((name, fn))

    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {pool.submit(fn): name for name, fn in tasks}
        for fut in as_completed(futures):
            name = futures[fut]
            try:
                fut.result()
            except Exception as exc:
                print(f"{name}: {exc}", file=sys.stderr)

    merge_py = layout.automation_dir / "bin" / "merge-template-list-vale.py"
    if merge_py.is_file():
        subprocess.run([sys.executable, str(merge_py)], cwd=layout.repo_root, check=False)

    record_lint_exits(log_dir)
