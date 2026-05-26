from __future__ import annotations

from pathlib import Path

import pytest

import sync_allowlists
from sync_allowlists import read_terms


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return sync_allowlists.repo_root()


def test_read_terms_from_canonical_file(repo_root: Path) -> None:
    terms_path = (
        repo_root
        / ".github/docs-quality/config/allowlists/terms.txt"
    )
    terms = read_terms(terms_path)
    assert "actionlint" in terms
    assert terms == sorted(set(terms), key=lambda s: (s.casefold(), s))


def test_sync_main_exits_zero(repo_root: Path) -> None:
    assert sync_allowlists.repo_root() == repo_root
    assert sync_allowlists.main() == 0
