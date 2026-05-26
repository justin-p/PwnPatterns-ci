from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Footer, Header, Static

from docs_dev.context import RepoContext
from docs_dev.runners import doctor, e2e, maintenance
from docs_dev.tui.menu import (
    MenuEntry,
    compose_menu_grid,
    entries_as_tuples,
    shortcut_bindings,
)
from docs_dev.tui.worker_screen import WorkerScreen

TOOL_ENTRIES: list[MenuEntry] = [
    MenuEntry("doctor", "Doctor", "Show tool versions and PATH", "primary", "1"),
    MenuEntry("sync", "Sync", "Regenerate allowlists", "success", "2"),
    MenuEntry("vale-sync", "Vale sync", "Download Vale style packages", "accent", "3"),
    MenuEntry("checksums", "Checksums", "Refresh SHA256 pins in manifest", "warning", "4"),
    MenuEntry("e2e", "E2E", "Run CI machinery smoke tests", "default", "5"),
]

class ToolsScreen(Screen):
    """Maintenance and diagnostics."""

    MENU_ITEMS = entries_as_tuples(TOOL_ENTRIES)

    BINDINGS = shortcut_bindings(
        TOOL_ENTRIES,
        extra=[
            Binding("escape", "back", "Home"),
            Binding("q", "back", "Home"),
            Binding("?", "help", "Shortcuts"),
        ],
    )

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="screen-hero"):
            yield Static("Tools", id="screen-title")
            yield Static(
                "Maintenance and diagnostics (not part of doc lint).",
                classes="muted",
            )
        yield from compose_menu_grid(TOOL_ENTRIES, id_prefix="tool")
        yield Footer()

    def on_button_pressed(self, event) -> None:
        from textual.widgets import Button

        if not isinstance(event.button, Button):
            return
        if not event.button.id or not event.button.id.startswith("tool-"):
            return
        cmd = event.button.id.removeprefix("tool-")
        self._run_tool(cmd)

    def action_menu_doctor(self) -> None:
        self._run_tool("doctor")

    def action_menu_sync(self) -> None:
        self._run_tool("sync")

    def action_menu_vale_sync(self) -> None:
        self._run_tool("vale-sync")

    def action_menu_checksums(self) -> None:
        self._run_tool("checksums")

    def action_menu_e2e(self) -> None:
        self._run_tool("e2e")

    def _run_tool(self, cmd: str) -> None:
        ctx = RepoContext.from_env()

        if cmd == "doctor":

            def run_doc(on_line):
                ok, rows = doctor.run_doctor(ctx)
                for row in rows:
                    ver = f" ({row.version})" if row.version else ""
                    on_line(f"{row.name}: {row.state}{ver}")
                return 0 if ok else 1

            self.app.push_screen(WorkerScreen("doctor", run_doc))
            return
        if cmd == "sync":
            self.app.push_screen(
                WorkerScreen("sync", lambda on: maintenance.run_sync(ctx, on_line=on))
            )
            return
        if cmd == "vale-sync":
            self.app.push_screen(
                WorkerScreen(
                    "vale-sync",
                    lambda on: maintenance.run_vale_sync(ctx, on_line=on),
                )
            )
            return
        if cmd == "checksums":
            self.app.push_screen(
                WorkerScreen(
                    "checksums",
                    lambda on: maintenance.run_checksums(ctx, on_line=on),
                )
            )
            return
        if cmd == "e2e":
            self.app.push_screen(
                WorkerScreen("e2e", lambda on: e2e.run_e2e(ctx, []))
            )
            return

    def action_help(self) -> None:
        self.notify(
            "1 Doctor · 2 Sync · 3 Vale sync · 4 Checksums · 5 E2E · Esc Home",
            title="Tools shortcuts",
            timeout=8,
        )

    def action_back(self) -> None:
        self.app.pop_screen()
