"""Global Textual stylesheet and Bearded Theme (feat gold d raynh) palette."""

from textual.theme import Theme

# Colors from Bearded Theme Feat-gold-d-raynh (VS Code / Cursor extension).
# https://github.com/BeardedBear/bearded-theme
BEARDED_FEAT_GOLD_D_RAYNH = Theme(
    name="bearded-feat-gold-d-raynh",
    primary="#e39000",
    secondary="#3eb2ff",
    accent="#ffd000",
    warning="#ff823f",
    error="#f7775a",
    success="#21ff7d",
    foreground="#b8c4e4",
    background="#0f1628",
    surface="#0c1220",
    panel="#16203b",
    boost="#1d2a4d",
    dark=True,
    variables={
        "border": "#27365c",
        "footer-key-foreground": "#ffd000",
        "block-cursor-background": "#ffd000",
        "block-cursor-foreground": "#0f1628",
        "input-selection-background": "#395397 50%",
        "button-color-foreground": "#0c1220",
    },
)

# Dark text on saturated menu buttons (matches theme badge.foreground).
_MENU_BTN_TEXT = "#0c1220"

APP_CSS = """
Screen {
    background: $background;
}

Header {
    background: $surface;
    color: $text;
    border-bottom: solid $border;
}

Footer {
    background: $surface;
    color: $text-muted;
}

/* ── Hero / titles ───────────────────────────────────────────── */

#home-hero, #screen-hero {
    padding: 1 2 0 2;
    height: auto;
    border-bottom: solid $border;
    background: $surface;
}

#banner, #screen-title {
    text-style: bold;
    color: $text;
    padding: 0 0 0 0;
}

#banner-accent {
    color: $primary;
    text-style: bold;
    padding: 0 0 0 0;
}

.muted, .menu-desc {
    color: $text-muted;
}

.hint-bar {
    color: $text-muted;
    padding: 0 2 1 2;
    height: auto;
}

/* ── Action menus (home, tools) ────────────────────────────────── */

.action-menu {
    grid-size: 2;
    grid-columns: 1fr 1fr;
    grid-gutter: 1 2;
    padding: 1 2 1 2;
    height: auto;
}

.menu-card {
    width: 100%;
    height: auto;
    padding: 1 1 0 1;
    border: solid $border;
    background: $panel;
}

.menu-card:focus-within {
    border: solid $primary;
    background: $boost;
}

.menu-card Button {
    width: 100%;
    min-height: 3;
    content-align: center middle;
    text-style: bold;
}

.menu-btn--primary {
    background: $primary;
    color: """ + _MENU_BTN_TEXT + """;
    border: none;
}

.menu-btn--primary:hover {
    background: $primary-lighten-1;
}

.menu-btn--secondary {
    background: $secondary;
    color: """ + _MENU_BTN_TEXT + """;
    border: none;
}

.menu-btn--secondary:hover {
    background: $secondary-lighten-1;
}

.menu-btn--success {
    background: $success;
    color: """ + _MENU_BTN_TEXT + """;
    border: none;
}

.menu-btn--success:hover {
    background: $success-lighten-1;
}

.menu-btn--warning {
    background: $warning;
    color: """ + _MENU_BTN_TEXT + """;
    border: none;
}

.menu-btn--warning:hover {
    background: $warning-lighten-1;
}

.menu-btn--accent {
    background: $accent;
    color: """ + _MENU_BTN_TEXT + """;
    border: none;
}

.menu-btn--accent:hover {
    background: $accent-lighten-1;
}

.menu-btn--default {
    background: $surface;
    color: $text;
    border: solid $border;
}

.menu-btn--default:hover {
    background: $boost;
    border: solid $primary;
}

.menu-desc {
    padding: 0 1 1 1;
    height: auto;
}

/* ── Toolbars ────────────────────────────────────────────────── */

#toolbar {
    height: auto;
    padding: 0 2 1 2;
    align: left middle;
}

#toolbar Button {
    margin-right: 1;
    min-width: 14;
    min-height: 3;
    border: none;
    border-top: none;
    border-bottom: none;
    content-align: center middle;
}

#toolbar Button.-primary {
    background: $primary;
    color: """ + _MENU_BTN_TEXT + """;
}

#toolbar Button.-primary:hover {
    background: $primary-lighten-1;
}

#toolbar Button.-primary:focus {
    background: $primary-lighten-1;
}

#toolbar Button.-success {
    background: $success;
    color: """ + _MENU_BTN_TEXT + """;
}

#toolbar Button.-success:hover {
    background: $success-lighten-1;
}

#toolbar Button.-success:focus {
    background: $success-lighten-1;
}

#toolbar Button.-warning {
    background: $warning;
    color: """ + _MENU_BTN_TEXT + """;
}

#toolbar Button.-warning:hover {
    background: $warning-lighten-1;
}

#toolbar Button.-warning:focus {
    background: $warning-lighten-1;
}

#toolbar Button.-default {
    background: $panel;
    color: $text;
}

#toolbar Button.-default:hover {
    background: $boost;
}

#toolbar Button.-default:focus {
    background: $boost;
}

/* ── Check screen ─────────────────────────────────────────────── */

#title {
    padding: 1 2 0 2;
    height: auto;
    text-style: bold;
}

#summary-footer {
    height: auto;
    padding: 0 2 1 2;
    border-top: solid $border;
    background: $surface;
}

#summary-footer #summary {
    padding: 0;
    height: auto;
    border: none;
    background: transparent;
}

#check-progress {
    height: 3;
    max-height: 3;
    border: solid $border;
    padding: 0 1;
    background: $panel;
    margin-top: 0;
}

#check-progress.-hidden {
    display: none;
}

#results-body {
    height: 1fr;
    min-height: 18;
    margin: 0 2;
}

#results-body.-editor-hidden #editor-panel {
    display: none;
}

#results-body.-editor-hidden #results-left {
    width: 1fr;
}

#results-left {
    width: 42%;
    min-width: 32;
    height: 100%;
}

#files-panel {
    height: 1fr;
    min-height: 8;
}

#file-filter {
    margin: 0 0 0 0;
    border: tall $border-blurred;
}

#file-filter:focus {
    border: tall $primary;
}

#file-filter-status {
    padding: 0 0 0 0;
    height: auto;
}

#files {
    height: 1fr;
    min-height: 6;
    border: solid $border;
    background: $panel;
}

#files:focus {
    border: solid $primary;
}

#detail-panel {
    height: 14;
    min-height: 10;
    border: solid $border;
    background: $surface;
    padding: 0 0 1 0;
    margin-top: 1;
}

#detail-actions {
    height: auto;
    padding: 0 1 1 1;
    align: left middle;
}

#open-editor {
    width: auto;
    height: auto;
    min-height: 1;
    min-width: 0;
    margin: 0;
}

#open-editor:disabled {
    opacity: 0.45;
}

#findings {
    height: 1fr;
    min-height: 6;
    margin: 1 1 0 1;
    border: solid $border;
    background: $panel;
}

#findings:focus {
    border: solid $secondary;
}

#editor-panel {
    width: 1fr;
    min-width: 28;
    height: 100%;
    border: solid $border;
    background: $panel;
    margin-left: 1;
}

#editor-panel:focus-within {
    border: solid $accent;
}

#editor-top {
    height: auto;
    align: left middle;
    border-bottom: solid $border;
    background: $surface;
}

#editor-header {
    padding: 0 1;
    height: auto;
    width: 1fr;
}

#close-editor {
    margin: 0 1 0 0;
    min-width: 16;
}

#file-editor {
    height: 1fr;
    min-height: 12;
    margin: 0 1 1 1;
    border: tall $border-blurred;
    background: $background;
    color: $foreground;
}

#file-editor:focus {
    border: tall $accent;
}

#file-editor .text-area--gutter {
    color: #313a55;
    background: $background;
}

#file-editor .text-area--cursor {
    background: #ffd000;
    color: #0f1628;
}

#open-editor,
#close-editor {
    border: none;
}

#open-editor:focus,
#close-editor:focus {
    border: none;
}

#summary {
    padding: 0 2 1 2;
    height: auto;
    border-top: solid $border;
    background: $surface;
}

/* ── Worker / log screen ───────────────────────────────────────── */

#status {
    padding: 1 2 0 2;
    height: auto;
    text-style: bold;
}

#status.-running {
    color: $warning;
}

#status.-ok {
    color: $success;
}

#status.-fail {
    color: $error;
}

#log {
    height: 1fr;
    min-height: 12;
    margin: 0 2 1 2;
    border: solid $border;
    background: $panel;
    padding: 0 1;
}

#log:focus {
    border: solid $primary;
}
"""
