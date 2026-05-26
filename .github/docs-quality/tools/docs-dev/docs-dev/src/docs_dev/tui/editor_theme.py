"""TextArea syntax theme aligned with Bearded Theme Feat-gold-d-raynh."""

from __future__ import annotations

from rich.style import Style
from textual.widgets.text_area import TextAreaTheme

# Palette mirrors docs_dev.tui.theme.BEARDED_FEAT_GOLD_D_RAYNH and the VS Code
# extension tokenColors in bearded-theme-feat-gold-d-raynh.json.
_BG = "#0f1628"
_FG = "#b8c4e4"
_GUTTER = "#313a55"
_GUTTER_ACTIVE = "#7186c0"
_CURSOR_LINE = "#17223e"
_SELECTION = "#395397"

_GOLD = "#ffd000"
_GREEN = "#21ff7d"
_BLUE = "#3eb2ff"
_PURPLE = "#a167ff"
_ORANGE = "#ff823f"
_RED = "#ff3d3d"
_MUTED = "#334984"
_CYAN = "#44f8e9"
_MAGENTA = "#e4ac73"

BEARDED_TEXT_AREA_THEME = TextAreaTheme(
    name="bearded-feat-gold-d-raynh",
    base_style=Style(color=_FG, bgcolor=_BG),
    gutter_style=Style(color=_GUTTER, bgcolor=_BG),
    cursor_style=Style(color=_BG, bgcolor=_GOLD),
    cursor_line_style=Style(bgcolor=_CURSOR_LINE),
    cursor_line_gutter_style=Style(color=_GUTTER_ACTIVE, bgcolor=_CURSOR_LINE),
    bracket_matching_style=Style(bgcolor="#395397", bold=True),
    selection_style=Style(bgcolor=_SELECTION),
    syntax_styles={
        # Prose / markdown (markup.* scopes in the VS Code theme)
        "heading": Style(color=_GOLD, bold=True),
        "heading.marker": Style(color=_GOLD),
        "bold": Style(color=_RED, bold=True),
        "italic": Style(color=_ORANGE, italic=True),
        "strikethrough": Style(color=_RED, strike=True),
        "link.label": Style(color=_BLUE),
        "link.uri": Style(color=_BLUE, underline=True),
        "list.marker": Style(color=_BLUE),
        "inline_code": Style(color=_GOLD),
        "info_string": Style(color=_PURPLE, bold=True, italic=True),
        "comment": Style(color=_MUTED, italic=True),
        "string": Style(color=_GREEN),
        "string.documentation": Style(color="#a4e661"),
        # YAML frontmatter / keys
        "yaml.field": Style(color=_GOLD, bold=True),
        # Fenced blocks (often parsed as JSON or plain text)
        "json.label": Style(color=_GOLD, bold=True),
        "json.null": Style(color=_CYAN),
        "keyword": Style(color=_GOLD),
        "keyword.function": Style(color=_BLUE),
        "keyword.return": Style(color=_BLUE),
        "keyword.operator": Style(color=_GOLD),
        "conditional": Style(color=_BLUE),
        "repeat": Style(color=_BLUE),
        "exception": Style(color=_BLUE),
        "include": Style(color=_BLUE),
        "operator": Style(color=_FG),
        "number": Style(color=_ORANGE),
        "float": Style(color=_ORANGE),
        "boolean": Style(color=_RED),
        "constant.builtin": Style(color=_RED),
        "type": Style(color=_PURPLE),
        "type.class": Style(color=_PURPLE),
        "type.builtin": Style(color=_CYAN),
        "class": Style(color=_PURPLE),
        "function": Style(color=_BLUE),
        "function.call": Style(color=_BLUE),
        "method": Style(color=_CYAN),
        "method.call": Style(color=_CYAN),
        "constructor": Style(color=_CYAN),
        "tag": Style(color=_PURPLE),
        "toml.type": Style(color=_BLUE),
        "toml.datetime": Style(color=_MAGENTA, italic=True),
        "css.property": Style(color=_FG),
        "punctuation.bracket": Style(color=_GOLD),
        "punctuation.delimiter": Style(color="#93a6d6"),
        "punctuation.special": Style(color="#93a6d6"),
    },
)


def register_bearded_editor_theme(text_area) -> None:
    """Register and activate the Bearded editor theme on a TextArea instance."""
    text_area.register_theme(BEARDED_TEXT_AREA_THEME)
    text_area.theme = BEARDED_TEXT_AREA_THEME.name
