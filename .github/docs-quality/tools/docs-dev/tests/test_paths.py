from pathlib import Path

from docs_dev.tui.paths import display_path


def test_display_path_shortens_under_repo_root() -> None:
    root = Path("/repo")
    long = root / "docs/ad/general/Some_Very_Long_Document_Name/Some_Very_Long_Document_Name.md"
    shown = display_path(str(long), root)
    assert shown.endswith("Some_Very_Long_Document_Name.md")
    assert "docs/ad" in shown or shown.startswith("…/")
