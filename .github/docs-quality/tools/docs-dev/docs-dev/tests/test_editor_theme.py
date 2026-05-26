"""Bearded TextArea editor theme."""

from rich.style import Style
from textual.widgets import TextArea

from docs_dev.tui.editor_theme import (
    BEARDED_TEXT_AREA_THEME,
    register_bearded_editor_theme,
)


def test_bearded_theme_matches_app_palette() -> None:
    assert BEARDED_TEXT_AREA_THEME.name == "bearded-feat-gold-d-raynh"
    assert BEARDED_TEXT_AREA_THEME.base_style == Style(color="#b8c4e4", bgcolor="#0f1628")
    assert BEARDED_TEXT_AREA_THEME.syntax_styles["heading"] == Style(
        color="#ffd000", bold=True
    )
    assert BEARDED_TEXT_AREA_THEME.syntax_styles["string"] == Style(color="#21ff7d")
    assert BEARDED_TEXT_AREA_THEME.syntax_styles["yaml.field"] == Style(
        color="#ffd000", bold=True
    )


def test_register_bearded_editor_theme() -> None:
    editor = TextArea(language="markdown")
    register_bearded_editor_theme(editor)
    assert editor.theme == "bearded-feat-gold-d-raynh"
    assert "bearded-feat-gold-d-raynh" in editor.available_themes
