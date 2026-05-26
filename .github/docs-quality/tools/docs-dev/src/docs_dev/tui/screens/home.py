from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Footer, Header, Static

from docs_dev.context import RepoContext
from docs_dev.runners import setup
from docs_dev.tui.menu import (
    MenuEntry,
    compose_menu_grid,
    entries_as_tuples,
    shortcut_bindings,
)
from docs_dev.tui.screens.check_screen import CheckScreen
from docs_dev.tui.screens.tools_screen import ToolsScreen
from docs_dev.tui.worker_screen import WorkerScreen

HOME_ENTRIES: list[MenuEntry] = [
    MenuEntry("setup", "Setup", "Install linters and prek hooks", "success", "1"),
    MenuEntry(
        "changed",
        "Check Changed",
        "Lint branch + local doc edits vs main",
        "warning",
        "2",
    ),
    MenuEntry("check", "Check All", "Lint all documentation", "primary", "3"),
    MenuEntry("tools", "Tools", "Doctor, sync, e2e, and more", "secondary", "4"),
]

class HomeScreen(Screen):
    """Main launcher."""

    MENU_ITEMS = entries_as_tuples(HOME_ENTRIES)

    BINDINGS = shortcut_bindings(
        HOME_ENTRIES,
        extra=[
            Binding("q", "quit", "Quit"),
            Binding("?", "help", "Shortcuts"),
        ],
    )

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="home-hero"):
            yield Static("PwnPatterns", id="banner-accent")
            yield Static("Documentation quality", id="banner")
        yield from compose_menu_grid(HOME_ENTRIES, id_prefix="cmd")
        yield Footer()

    def on_button_pressed(self, event) -> None:
        from textual.widgets import Button

        if not isinstance(event.button, Button):
            return
        if not event.button.id or not event.button.id.startswith("cmd-"):
            return
        cmd = event.button.id.removeprefix("cmd-")
        self._open_command(cmd)

    def action_menu_setup(self) -> None:
        self._open_command("setup")

    def action_menu_check(self) -> None:
        self._open_command("check")

    def action_menu_changed(self) -> None:
        self._open_command("changed")

    def action_menu_tools(self) -> None:
        self._open_command("tools")

    def _open_command(self, cmd: str) -> None:
        if cmd == "check":
            self.app.push_screen(CheckScreen())
            return
        if cmd == "changed":
            self.app.push_screen(CheckScreen(changed=True))
            return
        if cmd == "tools":
            self.app.push_screen(ToolsScreen())
            return
        if cmd == "setup":
            ctx = RepoContext.from_env()
            self.app.push_screen(
                WorkerScreen(
                    "setup",
                    lambda on: setup.run_setup(ctx, on_line=on),
                )
            )
            return

    def action_help(self) -> None:
        lines = [
            "1 — Setup (install tools + hooks)",
            "2 — Check changed docs only",
            "3 — Check all docs",
            "4 — Tools submenu",
            "r — Run check · f — Fix (on check screen)",
            "Esc — Back",
            "q — Quit (home) or back (other screens)",
            "Ctrl+P — Command palette",
        ]
        self.notify("\n".join(lines), title="Keyboard shortcuts", timeout=10)

    def action_quit(self) -> None:
        self.app.exit()
