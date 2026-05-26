from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

TOOL_DIR = Path(__file__).resolve().parents[1]
FIXTURE = (
    Path(__file__).resolve().parents[5]
    / ".github/tests/fixtures/metadata-invalid.md"
)


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return Path(__file__).resolve().parents[5]


def _run(repo_root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    del repo_root
    return subprocess.run(
        [sys.executable, str(TOOL_DIR / "verify_metadata.py"), *args],
        cwd=TOOL_DIR,
        capture_output=True,
        text=True,
    )


def test_valid_pattern_metadata_passes(repo_root: Path) -> None:
    rel = (
        "docs/ad/general/Unhygienic_Default_Domain_Administrator_Account/"
        "Unhygienic_Default_Domain_Administrator_Account.md"
    )
    proc = _run(repo_root, rel)
    assert proc.returncode == 0, proc.stderr


def test_invalid_fixture_fails_with_rdjsonl(repo_root: Path) -> None:
    rel = "docs/.ci-verify-metadata-invalid.md"
    dest = repo_root / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
    try:
        proc = _run(repo_root, "--rdjsonl", rel)
        assert proc.returncode == 1, proc.stdout
        lines = [ln for ln in proc.stdout.splitlines() if ln.strip()]
        assert lines
        row = json.loads(lines[0])
        assert row["severity"] == "ERROR"
        assert rel in row["location"]["path"]
        assert row["message"].startswith("[metadata]")
        assert "File:" in row["message"]
    finally:
        dest.unlink(missing_ok=True)
