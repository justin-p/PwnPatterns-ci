"""Command palette entries (Ctrl+P) for docs-dev screens."""

from __future__ import annotations

from collections.abc import Callable, Iterable

from textual.app import App, SystemCommand
from textual.screen import Screen

from docs_dev.context import RepoContext
from docs_dev.runners import setup
from docs_dev.tui.menu import MenuEntry
from docs_dev.tui.screens.check_screen import CheckScreen
from docs_dev.tui.screens.home import HOME_ENTRIES, HomeScreen
from docs_dev.tui.screens.tools_screen import TOOL_ENTRIES, ToolsScreen
from docs_dev.tui.worker_screen import WorkerScreen


def _menu_commands(
    entries: Iterable[MenuEntry],
    run: Callable[[str], None],
) -> Iterable[SystemCommand]:
    for entry in entries:
        cmd = entry.cmd

        def action(*, _cmd: str = cmd) -> None:
            run(_cmd)

        yield SystemCommand(entry.label, entry.desc, action)


def iter_docs_dev_commands(app: App, screen: Screen) -> Iterable[SystemCommand]:
    """Commands shown in the palette for the active screen."""

    if isinstance(screen, HomeScreen):
        yield from _menu_commands(HOME_ENTRIES, screen._open_command)
        return

    if isinstance(screen, ToolsScreen):
        yield from _menu_commands(TOOL_ENTRIES, screen._run_tool)
        yield SystemCommand("Home", "Return to the main menu", app.action_nav_home)
        return

    if isinstance(screen, CheckScreen):
        yield SystemCommand(
            "Run check",
            f"Lint {screen._mode_label}",
            screen.action_run,
        )
        yield SystemCommand(
            "Run fix",
            f"Autofix {screen._mode_label}, then re-check",
            screen.action_fix,
        )
        yield SystemCommand(
            "Allowlist term",
            "Add selected spelling/typo word to terms.txt and sync",
            screen.action_allowlist_term,
        )
        if screen._opts.changed:
            yield SystemCommand(
                "Check All",
                "Lint all documentation",
                app.action_nav_check_all,
            )
        else:
            yield SystemCommand(
                "Check Changed",
                "Lint files changed vs main",
                app.action_nav_check_changed,
            )
        yield SystemCommand("Home", "Return to the main menu", app.action_nav_home)
        return

    if isinstance(screen, WorkerScreen):
        yield SystemCommand("Home", "Return to the main menu", app.action_nav_home)
        return

    yield SystemCommand("Home", "Return to the main menu", app.action_nav_home)
    yield SystemCommand("Setup", "Install linters and prek hooks", app.action_nav_setup)
    yield SystemCommand(
        "Check Changed",
        "Lint files changed vs main",
        app.action_nav_check_changed,
    )
    yield SystemCommand("Check All", "Lint all documentation", app.action_nav_check_all)
    yield SystemCommand("Tools", "Doctor, sync, e2e, and more", app.action_nav_tools)


def nav_setup(app: App) -> None:
    ctx = RepoContext.from_env()
    app.push_screen(
        WorkerScreen(
            "setup",
            lambda on: setup.run_setup(ctx, on_line=on),
        )
    )
