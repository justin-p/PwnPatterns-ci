from __future__ import annotations

from collections.abc import Iterable

from textual.app import App, SystemCommand
from textual.screen import Screen

from docs_dev.tui.commands import iter_docs_dev_commands, nav_setup
from docs_dev.tui.screens.check_screen import CheckScreen
from docs_dev.tui.screens.home import HomeScreen
from docs_dev.tui.screens.tools_screen import ToolsScreen
from docs_dev.tui.theme import APP_CSS, BEARDED_FEAT_GOLD_D_RAYNH


class DocsDevApp(App):
    TITLE = "docs-dev"
    CSS = APP_CSS

    COMMAND_PALETTE_DISPLAY = "Ctrl+P"

    #: Re-lint the current file after allowlist + sync (shared by Check All / Changed).
    auto_refresh_after_allowlist: bool = True

    #: Regenerate Vale/Harper/Typos/Textlint allowlist artifacts after allowlisting from TUI.
    auto_sync_after_allowlist: bool = True

    def get_system_commands(self, screen: Screen) -> Iterable[SystemCommand]:
        yield from super().get_system_commands(screen)
        yield from iter_docs_dev_commands(self, screen)

    def action_nav_home(self) -> None:
        while len(self.screen_stack) > 1:
            self.pop_screen()
        if not isinstance(self.screen, HomeScreen):
            self.push_screen(HomeScreen())

    def action_nav_check_all(self) -> None:
        self.push_screen(CheckScreen())

    def action_nav_check_changed(self) -> None:
        self.push_screen(CheckScreen(changed=True))

    def action_nav_tools(self) -> None:
        self.push_screen(ToolsScreen())

    def action_nav_setup(self) -> None:
        nav_setup(self)

    def on_mount(self) -> None:
        from docs_dev.cli import parse_global_flags

        import sys

        self.register_theme(BEARDED_FEAT_GOLD_D_RAYNH)
        self.theme = BEARDED_FEAT_GOLD_D_RAYNH.name

        _, _, changed = parse_global_flags(sys.argv[1:])
        if changed:
            from docs_dev.tui.screens.check_screen import CheckScreen

            self.push_screen(CheckScreen(changed=True))
        else:
            self.push_screen(HomeScreen())
