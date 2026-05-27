"""CI E2E driver (parity with docs-quality.yml + actionlint + lychee)."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

from pwnpatterns_ci.config import apply_manifest_to_environ, load_manifest
from pwnpatterns_ci.install import install_doc_linters, install_reviewdog
from pwnpatterns_ci.jobs import actionlint_job, report_reviewdog, run_prek, verify_metadata
from pwnpatterns_ci.lint_prose import lint_prose
from pwnpatterns_ci.paths import Layout
from pwnpatterns_ci.targets import doc_targets

_LINE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$")


def _load_expectations(layout: Layout) -> dict[str, int]:
    out: dict[str, int] = {}
    for path in (
        layout.docs_quality_dir / "config" / "ci-e2e-expectations.env",
        layout.consumer_config_dir / "ci-e2e-expectations.env",
    ):
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            m = _LINE.match(line.strip())
            if not m or not m.group(1).startswith("EXPECT_"):
                continue
            key = m.group(1).replace("EXPECT_", "").replace("_EXIT", "").lower()
            if key == "lychee_filter":
                key = "lychee"
            out[key] = int(m.group(2))
    return out


def _run_component_tests(layout: Layout) -> None:
    for candidate in (
        layout.repo_root / ".github/pwnpatterns-ci/.github/tests/run-component-tests.sh",
        layout.repo_root / ".github/tests/run-component-tests.sh",
        layout.docs_quality_dir.parent / "tests/run-component-tests.sh",
    ):
        if candidate.is_file():
            subprocess.run(["bash", str(candidate)], cwd=layout.repo_root, check=True)
            return
    raise RuntimeError("run-component-tests.sh not found")


def _lychee_lib(layout: Layout) -> Path:
    for candidate in (
        layout.repo_root / ".github/pwnpatterns-ci/.github/lychee/automation/lib",
        layout.repo_root / ".github/lychee/automation/lib",
    ):
        if (candidate / "ci-steps-lychee.sh").is_file():
            return candidate
    raise RuntimeError("lychee ci-steps-lychee.sh not found")


def _run_lychee(layout: Layout, log_dir: Path, paths: list[str]) -> int:
    temp_cfg = layout.repo_root / ".lychee.toml"
    created_temp_cfg = False
    if not temp_cfg.is_file():
        temp_cfg.write_text(
            "\n".join(
                (
                    "# Temporary CI E2E fallback config for platform-only checkouts.",
                    "# Consumer repos should provide their own .lychee.toml.",
                    "max_redirects = 8",
                    "max_retries = 2",
                    "retry_wait_time = 2",
                    "timeout = 20",
                    "insecure = false",
                    "",
                )
            ),
            encoding="utf-8",
        )
        created_temp_cfg = True
        print("lychee config .lychee.toml not found; created temporary fallback config.")
    lib = _lychee_lib(layout)
    env = os.environ.copy()
    env["CI_LINT_LOG_DIR"] = str(log_dir)
    env["LINT_LOG_DIR"] = str(log_dir)
    quoted = " ".join(f'"{p}"' for p in paths)
    script = f"""
set -euo pipefail
source "{lib}/../lib/env.sh" 2>/dev/null || true
source "{layout.docs_quality_dir}/automation/lib/env.sh" 2>/dev/null || true
export REPO_ROOT="{layout.repo_root}"
export DOCS_QUALITY_DIR="{layout.docs_quality_dir}"
source "{lib}/ci-steps-lychee.sh"
ci_lychee_pr {quoted}
"""
    try:
        proc = subprocess.run(["bash", "-c", script], cwd=layout.repo_root, env=env)
    finally:
        if created_temp_cfg:
            temp_cfg.unlink(missing_ok=True)
    exit_f = log_dir / "lychee-filter.exit"
    if exit_f.is_file():
        return int(exit_f.read_text(encoding="utf-8").strip() or "0")
    return proc.returncode


def _prepare_harper() -> None:
    home = Path.home()
    (home / ".config/harper-ls").mkdir(parents=True, exist_ok=True)
    (home / ".local/share/harper-ls/file_dictionaries").mkdir(parents=True, exist_ok=True)
    dict_file = home / ".config/harper-ls/dictionary.txt"
    dict_file.touch(exist_ok=True)


def _sync_allowlists(layout: Layout) -> None:
    tool = layout.docs_quality_dir / "tools" / "sync-allowlists" / "sync_allowlists.py"
    subprocess.run([sys.executable, str(tool)], cwd=layout.repo_root, check=True)


def _has_smoke_probe_fixtures(layout: Layout) -> bool:
    """True when the consumer smoke PR fixtures are present (not just --smoke-docs on platform)."""
    root = layout.repo_root
    if (root / "docs/_ci_trigger_smoke").is_dir():
        return True
    if (root / ".github/workflows/ci-smoke-actionlint-probe.yml").is_file():
        return True
    if (root / ".github/ci-smoke-shellcheck-probe.sh").is_file():
        return True
    return False


def run_e2e(
    layout: Layout,
    *,
    job: str = "all",
    smoke_docs: bool = False,
    skip_lychee: bool = False,
    include_dashboard: bool = False,
    component_only: bool = False,
) -> None:
    os.environ.setdefault("CI_REVIEWDOG_MODE", "local")
    log_dir = layout.resolve_log_dir(Path(os.environ.get("CI_LINT_LOG_DIR", "lint-logs")))
    os.environ["CI_LINT_LOG_DIR"] = str(log_dir)
    apply_manifest_to_environ(layout)
    load_manifest(layout)
    results: dict[str, int] = {}
    expected = _load_expectations(layout)
    if smoke_docs and _has_smoke_probe_fixtures(layout):
        # Consumer smoke PR fixtures intentionally fail content linters / probes.
        # Platform repo may use --smoke-docs without these paths (no docs tree); keep default expectations.
        expected.update(
            {
                "vale": 1,
                "rumdl": 1,
                "metadata": 1,
                "lychee": 1,
                "shellcheck": 1,
                "actionlint": 1,
            }
        )

    print("==> component tests")
    _run_component_tests(layout)
    if component_only:
        return

    def lint_job() -> None:
        if smoke_docs:
            docs = layout.repo_root / "docs"
            paths = sorted(docs.glob("**/*.md"))[:5] if docs.is_dir() else []
            paths = [layout.rel(p) for p in paths]
            if not paths:
                print("CI_E2E smoke-docs: no docs/*.md under repo root; skipping lint job.")
                return
        else:
            scan_mode, paths, skip = doc_targets(layout, config_only_full_scan=False)
            if skip and os.environ.get("CI_E2E_FULL_LINT") == "true":
                paths = [layout.rel(p) for p in sorted((layout.repo_root / "docs").glob("**/*.md"))]
                skip = False
            if skip:
                print("No documentation targets; skipping lint job.")
                return
        if not paths:
            raise RuntimeError("No paths to lint")
        if os.environ.get("CI_E2E_SKIP_SYNC", "true") != "true":
            _sync_allowlists(layout)
        _prepare_harper()
        install_doc_linters(layout)
        subprocess.run(
            ["vale", "sync"],
            cwd=layout.repo_root,
            check=True,
            env=os.environ.copy(),
        )
        install_reviewdog()
        lint_prose(layout, paths, log_dir)
        for tool in ("vale", "typos", "textlint", "rumdl", "harper", "languagetool"):
            exit_f = log_dir / f"{tool}.exit"
            results[tool] = int(exit_f.read_text(encoding="utf-8").strip()) if exit_f.is_file() else 0
        scan_mode, _, _ = doc_targets(layout, config_only_full_scan=False)
        meta_ec = verify_metadata(layout, log_dir, paths, scan_mode)
        results["metadata"] = meta_ec
        if os.environ.get("CI_E2E_SKIP_PREK", "true") == "true":
            (log_dir / "prek.exit").write_text("0", encoding="utf-8")
            results["prek"] = 0
        else:
            results["prek"] = run_prek(log_dir)
        report_reviewdog(log_dir)

    def lychee_job() -> None:
        if skip_lychee:
            print("Skipping lychee (--skip-lychee)")
            return
        install_reviewdog()
        if smoke_docs:
            paths = ["./docs/**/*.md"][:1]
            md = sorted((layout.repo_root / "docs").glob("**/*.md"))[:3]
            paths = [str(p.relative_to(layout.repo_root)) for p in md]
        else:
            paths = ["./docs/**/*.md"]
        results["lychee"] = _run_lychee(layout, log_dir, paths)

    def actionlint() -> None:
        install_reviewdog()
        ec = actionlint_job(layout, log_dir)
        for name in ("shellcheck", "shfmt", "actionlint"):
            exit_f = log_dir / f"{name}.exit"
            results[name] = int(exit_f.read_text(encoding="utf-8").strip()) if exit_f.is_file() else ec

    log_dir.mkdir(parents=True, exist_ok=True)
    if job == "all":
        lint_job()
        lychee_job()
        actionlint()
        if include_dashboard:
            pass  # dashboard optional; lychee bash provides ci_lychee_dashboard
    elif job == "lint":
        lint_job()
    elif job == "lychee":
        lychee_job()
    elif job == "actionlint":
        actionlint()
    elif job == "dashboard":
        install_reviewdog()
        _run_lychee(layout, log_dir, ["./docs/**/*.md"])
    else:
        raise ValueError(f"Unknown job: {job}")

    print("\n==> E2E summary (reviewdog=local)")
    fail = 0
    for name in (
        "vale",
        "typos",
        "textlint",
        "rumdl",
        "harper",
        "languagetool",
        "metadata",
        "prek",
        "lychee",
        "shellcheck",
        "shfmt",
        "actionlint",
    ):
        if name not in results:
            print(f"  {name}: (not run)")
            continue
        actual = results[name]
        exp = expected.get(name, 0)
        if actual == exp:
            print(f"  {name}: exit={actual} expected={exp} PASS")
        else:
            print(f"  {name}: exit={actual} expected={exp} FAIL", file=sys.stderr)
            fail = 1
    if fail:
        raise SystemExit(1)
    print("CI E2E machinery checks passed.")
