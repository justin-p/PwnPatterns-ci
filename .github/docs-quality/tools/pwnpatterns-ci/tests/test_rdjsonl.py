"""rdjsonl converter parity tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pwnpatterns_ci.paths_util import resolve_path
from pwnpatterns_ci.rdjsonl.convert import prose_to_rdjsonl

FIXTURES = (
    Path(__file__).resolve().parents[3]
    / "docs-dev"
    / "tests"
    / "fixtures"
)


@pytest.fixture
def log_dir(tmp_path: Path) -> Path:
    return tmp_path


def test_vale_rdjsonl(log_dir: Path) -> None:
    sample = FIXTURES / "vale_sample.json"
    if not sample.is_file():
        pytest.skip("vale_sample.json missing")
    (log_dir / "vale.json").write_text(sample.read_text(encoding="utf-8"), encoding="utf-8")
    out = prose_to_rdjsonl("vale", log_dir)
    lines = [json.loads(ln) for ln in out.splitlines() if ln.strip()]
    assert lines
    assert all(ln["message"].startswith("[vale]") for ln in lines)


def test_harper_resolves_path_index(log_dir: Path) -> None:
    sample = FIXTURES / "harper_sample.json"
    paths = FIXTURES / "lint-paths.lst"
    if not sample.is_file() or not paths.is_file():
        pytest.skip("harper fixtures missing")
    (log_dir / "harper.json").write_text(sample.read_text(encoding="utf-8"), encoding="utf-8")
    path_list = [ln.strip() for ln in paths.read_text(encoding="utf-8").splitlines() if ln.strip()]
    out = prose_to_rdjsonl("harper", log_dir, path_list)
    lines = [json.loads(ln) for ln in out.splitlines() if ln.strip()]
    assert all(ln["location"]["path"].startswith("docs/") for ln in lines)
    assert any("InflectedVerbAfterTo" in ln["message"] for ln in lines)


def test_resolve_path_strips_platform_checkout_prefix() -> None:
    path_index = {
        "Protocollen_zonder_transportlaag_beveiliging.md": (
            "docs/infra/general/Protocollen_zonder_transportlaag_beveiliging/"
            "Protocollen_zonder_transportlaag_beveiliging.md"
        )
    }
    raw = (
        ".github/docs-quality/tools/pwnpatterns-ci/docs/infra/general/"
        "Protocollen_zonder_transportlaag_beveiliging/"
        "Protocollen_zonder_transportlaag_beveiliging.md"
    )
    got = resolve_path(raw, path_index, repo_root="")
    assert got == path_index["Protocollen_zonder_transportlaag_beveiliging.md"]


def test_resolve_path_strips_embedded_platform_checkout_prefix() -> None:
    path_index = {
        "Protocollen_zonder_transportlaag_beveiliging.md": (
            "docs/infra/general/Protocollen_zonder_transportlaag_beveiliging/"
            "Protocollen_zonder_transportlaag_beveiliging.md"
        )
    }
    raw = (
        "/home/runner/work/PwnPatterns-nl/PwnPatterns-nl/.github/pwnpatterns-ci/docs/infra/general/"
        "Protocollen_zonder_transportlaag_beveiliging/"
        "Protocollen_zonder_transportlaag_beveiliging.md"
    )
    got = resolve_path(raw, path_index, repo_root="")
    assert got == path_index["Protocollen_zonder_transportlaag_beveiliging.md"]
