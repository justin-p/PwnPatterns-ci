"""Textual Pilot e2e: home menu and tools submenu buttons."""

from __future__ import annotations

import time

import pytest
from textual.command import CommandPalette
from textual.widgets import Button, Checkbox, DataTable, Input, Static, TextArea

from docs_dev.tui.app import DocsDevApp
from docs_dev.tui.screens.check_screen import CheckScreen
from docs_dev.tui.screens.home import HomeScreen
from docs_dev.tui.screens.tools_screen import ToolsScreen
from docs_dev.tui.worker_screen import WorkerScreen

from tests.manifest_fixtures import tui_check_repo_context


class DocsDevTestApp(DocsDevApp):
    """Always start on home (ignore sys.argv from pytest)."""

    def on_mount(self) -> None:
        self.push_screen(HomeScreen())


HOME_COMMANDS = [cmd for cmd, _, _ in HomeScreen.MENU_ITEMS]
TOOL_COMMANDS = [cmd for cmd, _, _ in ToolsScreen.MENU_ITEMS]


def _home(app) -> HomeScreen:
    assert isinstance(app.screen, HomeScreen)
    return app.screen


def _tools(app) -> ToolsScreen:
    assert isinstance(app.screen, ToolsScreen)
    return app.screen


def _static_text(widget: Static) -> str:
    for attr in ("_content", "content"):
        val = getattr(widget, attr, None)
        if val:
            return str(val)
    return str(widget)


async def _activate_button(pilot, btn: Button) -> None:
    """Focus + Enter avoids pilot.click typing keys (e.g. 'e' from E2E)."""
    btn.focus()
    await pilot.press("enter")


async def _click_home_button(pilot, app, command: str) -> None:
    home = _home(app)
    btn = home.query_one(f"#cmd-{command}", Button)
    await _activate_button(pilot, btn)
    deadline = time.monotonic() + 3.0
    while time.monotonic() < deadline:
        if command in ("check", "changed") and isinstance(
            app.screen, CheckScreen
        ):
            return
        if command == "tools" and isinstance(app.screen, ToolsScreen):
            return
        if command == "setup" and isinstance(app.screen, WorkerScreen):
            return
        await pilot.pause(0.05)
    pytest.fail(
        f"Expected screen for '{command}', still on {type(app.screen).__name__}"
    )


async def _click_tool_button(pilot, app, command: str) -> None:
    tools = _tools(app)
    btn = tools.query_one(f"#tool-{command}", Button)
    await _activate_button(pilot, btn)
    deadline = time.monotonic() + 3.0
    while time.monotonic() < deadline:
        if isinstance(app.screen, WorkerScreen):
            return
        await pilot.pause(0.05)
    pytest.fail(
        f"Expected WorkerScreen for '{command}', still on {type(app.screen).__name__}"
    )


async def _wait_worker_done(pilot, command: str, timeout: float = 5.0) -> None:
    app = pilot.app
    assert isinstance(app.screen, WorkerScreen)
    assert app.screen.command == command
    loops = max(1, int(timeout / 0.05))
    for _ in range(loops):
        if isinstance(app.screen, WorkerScreen):
            text = _static_text(app.screen.query_one("#status", Static))
            if any(
                token in text.lower()
                for token in (
                    "finished",
                    "successfully",
                    "exited with code",
                    "failed",
                )
            ):
                return
        await pilot.pause(0.05)
    pytest.fail(f"Worker '{command}' did not finish within {timeout}s")


async def _wait_check_summary(pilot, timeout: float = 5.0) -> str:
    app = pilot.app
    loops = max(1, int(timeout / 0.05))
    for _ in range(loops):
        if isinstance(app.screen, CheckScreen):
            text = _static_text(app.screen.query_one("#summary", Static))
            if "PASS" in text or "FAIL" in text or "Error" in text:
                return text
        await pilot.pause(0.05)
    pytest.fail(f"Check summary did not update within {timeout}s")


@pytest.mark.parametrize("command", HOME_COMMANDS)
async def test_home_menu_button_opens_screen(command: str) -> None:
    app = DocsDevTestApp()

    async with app.run_test(size=(120, 52)) as pilot:
        await pilot.pause()
        home = _home(app)
        assert home.query_one(f"#cmd-{command}") is not None

        await _click_home_button(pilot, app, command)

        if command == "check":
            assert isinstance(app.screen, CheckScreen)
            assert app.screen._opts.changed is False
        elif command == "changed":
            assert isinstance(app.screen, CheckScreen)
            assert app.screen._opts.changed is True
        elif command == "tools":
            _tools(app)
        elif command == "setup":
            assert isinstance(app.screen, WorkerScreen)
            assert app.screen.command == "setup"
            await _wait_worker_done(pilot, "setup")
        else:
            pytest.fail(f"Unhandled command: {command}")

        await pilot.press("escape")
        await pilot.pause(0.1)
        if isinstance(app.screen, ToolsScreen):
            await pilot.press("escape")
            await pilot.pause(0.1)
        _home(app)


@pytest.mark.parametrize("command", TOOL_COMMANDS)
async def test_tools_submenu_button_opens_worker(command: str) -> None:
    app = DocsDevTestApp()

    async with app.run_test(size=(120, 52)) as pilot:
        await pilot.pause()
        await _click_home_button(pilot, app, "tools")
        await _click_tool_button(pilot, app, command)
        assert isinstance(app.screen, WorkerScreen)
        assert app.screen.command == command
        await _wait_worker_done(pilot, command)
        await pilot.press("escape")
        await pilot.pause(0.1)
        _tools(app)
        await pilot.press("escape")
        await pilot.pause(0.1)
        _home(app)


async def test_check_screen_run_and_home_buttons() -> None:
    app = DocsDevTestApp()

    async with app.run_test(size=(100, 32)) as pilot:
        await pilot.pause()
        await _click_home_button(pilot, app, "check")

        check = app.screen
        assert isinstance(check, CheckScreen)
        assert check.query_one("#fix", Button) is not None
        await _activate_button(pilot, check.query_one("#run", Button))
        summary = await _wait_check_summary(pilot)
        assert "PASS" in summary

        await _activate_button(pilot, check.query_one("#home", Button))
        await pilot.pause(0.1)
        _home(app)


async def test_allowlist_rescan_does_not_crash_files_table(monkeypatch) -> None:
    """Regression: _apply_file_rescan must use int row index, not path string keys."""
    from docs_dev.models import (
        CheckReport,
        FileFindings,
        Finding,
        StepResult,
        StepStatus,
    )

    tiering = (
        "docs/ad/general/No_Slash_Ineffective_Active_Directory_Tiering_Model_Implemented/"
        "No_Slash_Ineffective_Active_Directory_Tiering_Model_Implemented/"
        "No_Slash_Ineffective_Active_Directory_Tiering_Model_Implemented.md"
    )
    other = "docs/workstation/general/Unrestricted_Command_Line_Interface_Access/Unrestricted_Command_Line_Interface_Access.md"

    def mock_check(_ctx, _opts, **_kwargs):
        return CheckReport(
            steps=[StepResult("prose lint", StepStatus.FAIL)],
            files=[
                FileFindings(
                    path=other,
                    findings=[
                        Finding(
                            tool="vale",
                            path=other,
                            line=35,
                            column=1,
                            severity="error",
                            message="Use 'it is' instead of 'it's'.",
                            rule="PwnPatterns.Contractions",
                        )
                    ],
                ),
                FileFindings(
                    path=tiering,
                    findings=[
                        Finding(
                            tool="vale",
                            path=tiering,
                            line=78,
                            column=1,
                            severity="error",
                            message="Use 'adminAAsrv' instead of 'AdminAAsrv'.",
                            rule="Vale.Terms",
                        )
                    ],
                ),
            ],
        )

    def mock_prose(_ctx, paths, **_kwargs):
        assert paths == [tiering]
        return [
            Finding(
                tool="vale",
                path=tiering,
                line=23,
                column=1,
                severity="error",
                message="Use 'were not' instead of 'weren't'.",
                rule="PwnPatterns.Contractions",
            ),
            Finding(
                tool="vale",
                path=tiering,
                line=78,
                column=1,
                severity="error",
                message="Use 'adminAAsrv' instead of 'AdminAAsrv'.",
                rule="Vale.Terms",
            ),
        ]

    def mock_add_term(_ctx, term, *, finding=None):
        return True, f"Added '{term}'"

    def mock_sync(_ctx):
        return 0

    monkeypatch.setattr(
        "docs_dev.tui.screens.check_screen.run_check", mock_check
    )
    monkeypatch.setattr(
        "docs_dev.tui.screens.check_screen.run_prose_lint", mock_prose
    )
    monkeypatch.setattr(
        "docs_dev.tui.screens.check_screen.add_term", mock_add_term
    )
    monkeypatch.setattr(
        "docs_dev.tui.screens.check_screen.sync_allowlists", mock_sync
    )

    app = DocsDevTestApp()

    async with app.run_test(size=(120, 52)) as pilot:
        await pilot.pause()
        await _click_home_button(pilot, app, "check")

        check = app.screen
        assert isinstance(check, CheckScreen)
        await _activate_button(pilot, check.query_one("#run", Button))
        await _wait_check_summary(pilot)

        files = check.query_one("#files")
        assert files.row_count >= 2
        # Select tiering file (second row after sort by count).
        check._report.files.sort(key=lambda ff: (-ff.count, ff.path))
        tiering_index = next(
            i for i, ff in enumerate(check._report.files) if ff.path == tiering
        )
        files.move_cursor(row=tiering_index)
        await pilot.pause(0.1)
        check._show_file_findings(check._report.files[tiering_index])

        allow_btn = check.query_one("#allowlist", Button)
        assert not allow_btn.disabled
        await _activate_button(pilot, allow_btn)

        deadline = time.monotonic() + 8.0
        while time.monotonic() < deadline:
            if not check._worker_busy():
                break
            await pilot.pause(0.05)

        assert isinstance(app.screen, CheckScreen)
        assert check._current_file is not None
        assert check._current_file.path == tiering
        assert files.cursor_row == tiering_index


async def test_allowlist_auto_refresh_toggle_skips_rescan(monkeypatch) -> None:
    """When refresh-after-allowlist is off, prose lint is skipped; finding drops from UI."""
    from docs_dev.models import (
        CheckReport,
        FileFindings,
        Finding,
        StepResult,
        StepStatus,
    )

    doc = "docs/example.md"

    def mock_check(_ctx, _opts, **_kwargs):
        return CheckReport(
            steps=[StepResult("prose lint", StepStatus.FAIL)],
            files=[
                FileFindings(
                    path=doc,
                    findings=[
                        Finding(
                            tool="vale",
                            path=doc,
                            line=10,
                            column=1,
                            severity="error",
                            message="Use 'Prometheus' instead of 'prometheus'.",
                            rule="Vale.Terms",
                        )
                    ],
                )
            ],
        )

    prose_calls: list[list[str]] = []

    def mock_prose(_ctx, paths, **_kwargs):
        prose_calls.append(list(paths))
        return []

    def mock_add_term(_ctx, term, *, finding=None):
        return True, f"Added '{term}'"

    def mock_sync(_ctx):
        return 0

    monkeypatch.setattr(
        "docs_dev.tui.screens.check_screen.run_check", mock_check
    )
    monkeypatch.setattr(
        "docs_dev.tui.screens.check_screen.run_prose_lint", mock_prose
    )
    monkeypatch.setattr(
        "docs_dev.tui.screens.check_screen.add_term", mock_add_term
    )
    monkeypatch.setattr(
        "docs_dev.tui.screens.check_screen.sync_allowlists", mock_sync
    )

    app = DocsDevTestApp()

    async with app.run_test(size=(120, 52)) as pilot:
        await pilot.pause()
        await _click_home_button(pilot, app, "check")

        check = app.screen
        assert isinstance(check, CheckScreen)
        app.auto_refresh_after_allowlist = False
        check.query_one("#auto-refresh-after-allowlist", Checkbox).value = False

        await _activate_button(pilot, check.query_one("#run", Button))
        await _wait_check_summary(pilot)

        await _activate_button(pilot, check.query_one("#allowlist", Button))

        deadline = time.monotonic() + 8.0
        while time.monotonic() < deadline:
            if not check._worker_busy():
                break
            await pilot.pause(0.05)

        assert prose_calls == []
        assert check._report is not None
        assert all(ff.path != doc for ff in check._report.files)

        await _activate_button(pilot, check.query_one("#home", Button))
        await pilot.pause(0.1)
        await _click_home_button(pilot, app, "changed")
        check_changed = app.screen
        assert isinstance(check_changed, CheckScreen)
        assert check_changed._opts.changed is True
        assert (
            check_changed.query_one("#auto-refresh-after-allowlist", Checkbox).value
            is False
        )


async def test_allowlist_auto_sync_toggle_skips_sync(monkeypatch) -> None:
    """When auto-sync-after-allowlist is off, sync_allowlists isn't called."""
    from docs_dev.models import (
        CheckReport,
        FileFindings,
        Finding,
        StepResult,
        StepStatus,
    )

    doc = "docs/example.md"

    def mock_check(_ctx, _opts, **_kwargs):
        return CheckReport(
            steps=[StepResult("prose lint", StepStatus.FAIL)],
            files=[
                FileFindings(
                    path=doc,
                    findings=[
                        Finding(
                            tool="vale",
                            path=doc,
                            line=10,
                            column=1,
                            severity="error",
                            message="Use 'Prometheus' instead of 'prometheus'.",
                            rule="Vale.Terms",
                        )
                    ],
                )
            ],
        )

    prose_calls: list[list[str]] = []

    def mock_prose(_ctx, paths, **_kwargs):
        prose_calls.append(list(paths))
        return []

    def mock_add_term(_ctx, term, *, finding=None):
        return True, f"Added '{term}'"

    sync_calls: list[bool] = []

    def mock_sync(_ctx):
        sync_calls.append(True)
        return 0

    monkeypatch.setattr(
        "docs_dev.tui.screens.check_screen.run_check", mock_check
    )
    monkeypatch.setattr(
        "docs_dev.tui.screens.check_screen.run_prose_lint", mock_prose
    )
    monkeypatch.setattr(
        "docs_dev.tui.screens.check_screen.add_term", mock_add_term
    )
    monkeypatch.setattr(
        "docs_dev.tui.screens.check_screen.sync_allowlists", mock_sync
    )

    app = DocsDevTestApp()

    async with app.run_test(size=(120, 52)) as pilot:
        await pilot.pause()
        await _click_home_button(pilot, app, "check")

        check = app.screen
        assert isinstance(check, CheckScreen)

        app.auto_refresh_after_allowlist = False
        check.query_one("#auto-refresh-after-allowlist", Checkbox).value = False

        app.auto_sync_after_allowlist = False
        check.query_one("#auto-sync-after-allowlist", Checkbox).value = False

        await _activate_button(pilot, check.query_one("#run", Button))
        await _wait_check_summary(pilot)

        await _activate_button(pilot, check.query_one("#allowlist", Button))

        deadline = time.monotonic() + 8.0
        while time.monotonic() < deadline:
            if not check._worker_busy():
                break
            await pilot.pause(0.05)

        assert prose_calls == []
        assert sync_calls == []
        assert check._report is not None
        assert all(ff.path != doc for ff in check._report.files)


async def test_sync_allowlists_button_refreshes_selected_file(monkeypatch):
    """Sync allowlists via toolbar button and refresh the selected file."""
    from docs_dev.models import (
        CheckReport,
        FileFindings,
        Finding,
        StepResult,
        StepStatus,
    )

    doc = "docs/example.md"

    def mock_check(_ctx, _opts, **_kwargs):
        return CheckReport(
            steps=[StepResult("prose lint", StepStatus.FAIL)],
            files=[
                FileFindings(
                    path=doc,
                    findings=[
                        Finding(
                            tool="vale",
                            path=doc,
                            line=10,
                            column=1,
                            severity="error",
                            message="Use 'Prometheus' instead of 'prometheus'.",
                            rule="Vale.Terms",
                        )
                    ],
                )
            ],
        )

    prose_calls: list[list[str]] = []

    def mock_prose(_ctx, paths, **_kwargs):
        prose_calls.append(list(paths))
        return []

    def mock_sync(_ctx):
        return 0

    monkeypatch.setattr(
        "docs_dev.tui.screens.check_screen.run_check", mock_check
    )
    monkeypatch.setattr(
        "docs_dev.tui.screens.check_screen.run_prose_lint", mock_prose
    )
    monkeypatch.setattr(
        "docs_dev.tui.screens.check_screen.sync_allowlists", mock_sync
    )

    app = DocsDevTestApp()

    async with app.run_test(size=(120, 52)) as pilot:
        await pilot.pause()
        await _click_home_button(pilot, app, "check")

        check = app.screen
        assert isinstance(check, CheckScreen)

        await _activate_button(pilot, check.query_one("#run", Button))
        await _wait_check_summary(pilot)

        assert check._current_file is not None
        assert check._current_file.path == doc

        sync_btn = check.query_one("#sync-allowlists", Button)
        assert not sync_btn.disabled
        await _activate_button(pilot, sync_btn)

        deadline = time.monotonic() + 8.0
        while time.monotonic() < deadline:
            if not check._worker_busy():
                break
            await pilot.pause(0.05)

        assert prose_calls == [[doc]]
        assert check._report is not None
        assert all(ff.path != doc for ff in check._report.files)


async def test_check_screen_editor_jumps_to_finding_line(
    monkeypatch, tmp_path: Path
) -> None:
    from docs_dev.models import (
        CheckReport,
        FileFindings,
        Finding,
        StepResult,
        StepStatus,
    )

    doc_rel = "docs/sample/sample.md"
    doc_abs = tmp_path / doc_rel
    doc_abs.parent.mkdir(parents=True)
    lines = ["# Title", "", "line two", "", "line four"]
    doc_abs.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def mock_check(ctx, _opts, **_kwargs):
        return CheckReport(
            steps=[StepResult("prose lint", StepStatus.FAIL)],
            files=[
                FileFindings(
                    path=doc_rel,
                    findings=[
                        Finding(
                            tool="vale",
                            path=doc_rel,
                            line=3,
                            column=1,
                            severity="error",
                            message="issue on line three",
                        ),
                        Finding(
                            tool="vale",
                            path=doc_rel,
                            line=5,
                            column=3,
                            severity="error",
                            message="test issue",
                        ),
                    ],
                )
            ],
        )

    monkeypatch.setattr(
        "docs_dev.tui.screens.check_screen.run_check", mock_check
    )
    monkeypatch.setattr(
        "docs_dev.tui.screens.check_screen.RepoContext.from_env",
        lambda: tui_check_repo_context(tmp_path),
    )

    app = DocsDevTestApp()

    async with app.run_test(size=(140, 52)) as pilot:
        await pilot.pause()
        await _click_home_button(pilot, app, "check")

        check = app.screen
        assert isinstance(check, CheckScreen)
        await _activate_button(pilot, check.query_one("#run", Button))
        await _wait_check_summary(pilot)

        files = check.query_one("#files", DataTable)
        assert files.has_focus
        assert files.cursor_row == 0

        body = check.query_one("#results-body")
        assert body.has_class("-editor-hidden")

        findings = check.query_one("#findings", DataTable)
        findings.move_cursor(row=1)
        await pilot.pause(0.05)

        await _activate_button(pilot, check.query_one("#open-editor", Button))
        await pilot.pause(0.1)

        assert not body.has_class("-editor-hidden")
        editor = check.query_one("#file-editor", TextArea)
        assert editor.has_focus
        assert "line four" in editor.text
        assert editor.cursor_location[0] == 4  # line 5 → 0-based row 4

        findings.move_cursor(row=0)
        await pilot.pause(0.1)
        assert editor.cursor_location[0] == 2  # line 3 → row 2

        check.query_one("#file-editor", TextArea).focus()
        await pilot.press("escape")
        await pilot.pause(0.1)

        assert isinstance(app.screen, CheckScreen)
        assert body.has_class("-editor-hidden")
        assert check.query_one("#findings", DataTable).has_focus


async def _dismiss_save_modal(pilot, *, save: bool) -> None:
    from docs_dev.tui.save_confirm_modal import SaveConfirmModal

    screen = pilot.app.screen
    if not isinstance(screen, SaveConfirmModal):
        await pilot.pause(0.05)
        screen = pilot.app.screen
    assert isinstance(screen, SaveConfirmModal)
    btn_id = "save" if save else "discard"
    await _activate_button(pilot, screen.query_one(f"#{btn_id}", Button))


async def test_check_screen_editor_prompts_save_on_file_change(
    monkeypatch, tmp_path: Path
) -> None:
    from docs_dev.models import (
        CheckReport,
        FileFindings,
        Finding,
        StepResult,
        StepStatus,
    )

    paths = ["docs/a/a.md", "docs/b/b.md"]
    for rel in paths:
        p = tmp_path / rel
        p.parent.mkdir(parents=True)
        p.write_text(f"# {rel}\n", encoding="utf-8")

    def finding_for(path: str, line: int) -> Finding:
        return Finding(
            tool="vale",
            path=path,
            line=line,
            column=1,
            severity="error",
            message="issue",
        )

    def mock_check(ctx, _opts, **_kwargs):
        return CheckReport(
            steps=[StepResult("prose lint", StepStatus.FAIL)],
            files=[
                FileFindings(path=paths[0], findings=[finding_for(paths[0], 1)]),
                FileFindings(path=paths[1], findings=[finding_for(paths[1], 1)]),
            ],
        )

    monkeypatch.setattr(
        "docs_dev.tui.screens.check_screen.run_check", mock_check
    )
    monkeypatch.setattr(
        "docs_dev.tui.screens.check_screen.RepoContext.from_env",
        lambda: tui_check_repo_context(tmp_path),
    )

    app = DocsDevTestApp()

    async with app.run_test(size=(140, 52)) as pilot:
        await pilot.pause()
        await _click_home_button(pilot, app, "check")

        check = app.screen
        assert isinstance(check, CheckScreen)
        await _activate_button(pilot, check.query_one("#run", Button))
        await _wait_check_summary(pilot)

        await _activate_button(pilot, check.query_one("#open-editor", Button))
        await pilot.pause(0.1)

        editor = check.query_one("#file-editor", TextArea)
        editor.insert("EDITED-A\n")

        files = check.query_one("#files", DataTable)
        files.move_cursor(row=1)
        await pilot.pause(0.1)
        await _dismiss_save_modal(pilot, save=True)
        await pilot.pause(0.1)

        assert (tmp_path / paths[0]).read_text(encoding="utf-8").startswith(
            "EDITED-A"
        )


async def test_check_screen_editor_prompt_discard_on_close(
    monkeypatch, tmp_path: Path
) -> None:
    from docs_dev.models import (
        CheckReport,
        FileFindings,
        Finding,
        StepResult,
        StepStatus,
    )

    doc_rel = "docs/sample/sample.md"
    doc_abs = tmp_path / doc_rel
    doc_abs.parent.mkdir(parents=True)
    original = "# Title\n\nbody\n"
    doc_abs.write_text(original, encoding="utf-8")

    def mock_check(ctx, _opts, **_kwargs):
        return CheckReport(
            steps=[StepResult("prose lint", StepStatus.FAIL)],
            files=[
                FileFindings(
                    path=doc_rel,
                    findings=[
                        Finding(
                            tool="vale",
                            path=doc_rel,
                            line=1,
                            column=1,
                            severity="error",
                            message="issue",
                        )
                    ],
                )
            ],
        )

    monkeypatch.setattr(
        "docs_dev.tui.screens.check_screen.run_check", mock_check
    )
    monkeypatch.setattr(
        "docs_dev.tui.screens.check_screen.RepoContext.from_env",
        lambda: tui_check_repo_context(tmp_path),
    )

    app = DocsDevTestApp()

    async with app.run_test(size=(140, 52)) as pilot:
        await pilot.pause()
        await _click_home_button(pilot, app, "check")

        check = app.screen
        assert isinstance(check, CheckScreen)
        await _activate_button(pilot, check.query_one("#run", Button))
        await _wait_check_summary(pilot)
        await _activate_button(pilot, check.query_one("#open-editor", Button))
        await pilot.pause(0.1)

        check.query_one("#file-editor", TextArea).insert("CHANGED\n")
        await _activate_button(pilot, check.query_one("#close-editor", Button))
        await pilot.pause(0.1)
        await _dismiss_save_modal(pilot, save=False)
        await pilot.pause(0.1)

        assert doc_abs.read_text(encoding="utf-8") == original
        assert check.query_one("#results-body").has_class("-editor-hidden")


async def test_check_screen_file_filter(monkeypatch) -> None:
    from docs_dev.models import (
        CheckReport,
        FileFindings,
        Finding,
        StepResult,
        StepStatus,
    )

    def mock_check(_ctx, _opts, **_kwargs):
        return CheckReport(
            steps=[StepResult("prose lint", StepStatus.FAIL)],
            files=[
                FileFindings(
                    path="docs/wifi/general/WPA2_Protocol_In_Use/WPA2_Protocol_In_Use.md",
                    findings=[
                        Finding(
                            tool="vale",
                            path="docs/wifi/general/WPA2_Protocol_In_Use/WPA2_Protocol_In_Use.md",
                            line=1,
                            column=1,
                            severity="error",
                            message="test",
                        )
                    ],
                ),
                FileFindings(
                    path=(
                        "docs/infra/general/Inadequate_Prometheus_Exporter_Implementation/"
                        "Inadequate_Prometheus_Exporter_Implementation.md"
                    ),
                    findings=[
                        Finding(
                            tool="vale",
                            path=(
                                "docs/infra/general/Inadequate_Prometheus_Exporter_Implementation/"
                                "Inadequate_Prometheus_Exporter_Implementation.md"
                            ),
                            line=1,
                            column=1,
                            severity="error",
                            message="test",
                        )
                    ],
                ),
            ],
        )

    monkeypatch.setattr(
        "docs_dev.tui.screens.check_screen.run_check", mock_check
    )

    app = DocsDevTestApp()

    async with app.run_test(size=(120, 52)) as pilot:
        await pilot.pause()
        await _click_home_button(pilot, app, "check")

        check = app.screen
        assert isinstance(check, CheckScreen)
        await _activate_button(pilot, check.query_one("#run", Button))
        await _wait_check_summary(pilot)

        files = check.query_one("#files")
        assert files.row_count == 2

        filt = check.query_one("#file-filter", Input)
        filt.value = "prometheus"
        await pilot.pause(0.15)

        assert files.row_count == 1
        status = _static_text(check.query_one("#file-filter-status", Static))
        assert "1 of 2" in status


async def test_check_screen_recheck_file_button(monkeypatch) -> None:
    from docs_dev.models import (
        CheckReport,
        FileFindings,
        Finding,
        StepResult,
        StepStatus,
    )

    recheck_paths: list[str] = []

    def mock_check(_ctx, _opts, **_kwargs):
        return CheckReport(
            steps=[StepResult("prose lint", StepStatus.PASS)],
            files=[
                FileFindings(
                    path="docs/example.md",
                    findings=[
                        Finding(
                            tool="vale",
                            path="docs/example.md",
                            line=1,
                            column=1,
                            severity="warning",
                            message="test",
                        )
                    ],
                ),
                FileFindings(
                    path="docs/other.md",
                    findings=[
                        Finding(
                            tool="vale",
                            path="docs/other.md",
                            line=2,
                            column=1,
                            severity="warning",
                            message="other",
                        )
                    ],
                ),
            ],
        )

    def mock_prose(_ctx, paths, **_kwargs):
        recheck_paths.extend(paths)
        return []

    monkeypatch.setattr(
        "docs_dev.tui.screens.check_screen.run_check", mock_check
    )
    monkeypatch.setattr(
        "docs_dev.tui.screens.check_screen.run_prose_lint", mock_prose
    )

    app = DocsDevTestApp()

    async with app.run_test(size=(100, 32)) as pilot:
        await pilot.pause()
        await _click_home_button(pilot, app, "check")

        check = app.screen
        assert isinstance(check, CheckScreen)
        await _activate_button(pilot, check.query_one("#run", Button))
        await _wait_check_summary(pilot)

        files = check.query_one("#files", DataTable)
        files.move_cursor(row=0)
        await pilot.pause(0.05)

        recheck_btn = check.query_one("#recheck-file", Button)
        assert not recheck_btn.disabled
        await _activate_button(pilot, recheck_btn)

        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline:
            if recheck_paths == ["docs/example.md"]:
                break
            await pilot.pause(0.05)
        assert recheck_paths == ["docs/example.md"]
        await pilot.pause(0.1)

        assert files.has_focus
        assert files.cursor_row == 0
        assert files.row_count == 1


async def test_check_screen_recheck_focuses_first_finding(monkeypatch) -> None:
    from docs_dev.models import (
        CheckReport,
        FileFindings,
        Finding,
        StepResult,
        StepStatus,
    )

    path = "docs/example.md"

    def mock_check(_ctx, _opts, **_kwargs):
        return CheckReport(
            steps=[StepResult("prose lint", StepStatus.FAIL)],
            files=[
                FileFindings(
                    path=path,
                    findings=[
                        Finding(
                            tool="vale",
                            path=path,
                            line=10,
                            column=1,
                            severity="error",
                            message="old",
                        )
                    ],
                )
            ],
        )

    def mock_prose(_ctx, paths, **_kwargs):
        return [
            Finding(
                tool="harper",
                path=path,
                line=3,
                column=1,
                severity="error",
                message="new first",
            ),
            Finding(
                tool="vale",
                path=path,
                line=12,
                column=1,
                severity="error",
                message="new second",
            ),
        ]

    monkeypatch.setattr(
        "docs_dev.tui.screens.check_screen.run_check", mock_check
    )
    monkeypatch.setattr(
        "docs_dev.tui.screens.check_screen.run_prose_lint", mock_prose
    )

    app = DocsDevTestApp()

    async with app.run_test(size=(100, 32)) as pilot:
        await pilot.pause()
        await _click_home_button(pilot, app, "check")

        check = app.screen
        assert isinstance(check, CheckScreen)
        await _activate_button(pilot, check.query_one("#run", Button))
        await _wait_check_summary(pilot)

        await _activate_button(pilot, check.query_one("#recheck-file", Button))
        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline:
            if not check._worker_busy():
                break
            await pilot.pause(0.05)
        await pilot.pause(0.1)

        findings = check.query_one("#findings", DataTable)
        assert findings.has_focus
        assert findings.cursor_row == 0
        assert check._selected_finding() is not None
        assert check._selected_finding().line == 3


async def test_check_screen_fix_button_runs_autofix() -> None:
    app = DocsDevTestApp()

    async with app.run_test(size=(100, 32)) as pilot:
        await pilot.pause()
        await _click_home_button(pilot, app, "changed")

        check = app.screen
        assert isinstance(check, CheckScreen)
        assert check._opts.changed is True
        await _activate_button(pilot, check.query_one("#fix", Button))
        summary = await _wait_check_summary(pilot, timeout=120.0)
        assert "PASS" in summary or "FAIL" in summary


async def test_command_palette_search_runs_check_all() -> None:
    app = DocsDevTestApp()

    async with app.run_test(size=(120, 52)) as pilot:
        await pilot.pause()
        _home(app)
        await pilot.press("ctrl+p")
        await pilot.pause(0.15)
        assert CommandPalette.is_open(app)
        # Discovery list is title-sorted; "Check All" is the first docs-dev action.
        await pilot.press("enter")
        await pilot.pause(0.1)
        assert isinstance(app.screen, CheckScreen)
        assert app.screen._opts.changed is False


async def test_home_keyboard_shortcut_opens_check() -> None:
    app = DocsDevTestApp()

    async with app.run_test(size=(120, 52)) as pilot:
        await pilot.pause()
        _home(app)
        await pilot.press("3")
        await pilot.pause(0.1)
        assert isinstance(app.screen, CheckScreen)
        assert app.screen._opts.changed is False
        await pilot.press("escape")
        await pilot.pause(0.1)
        _home(app)


async def test_home_quit_binding() -> None:
    app = DocsDevTestApp()

    async with app.run_test(size=(80, 24)) as pilot:
        await pilot.pause()
        _home(app)
        await pilot.press("q")
        await pilot.pause(0.1)
        assert not app.is_running


async def test_all_home_buttons_exist() -> None:
    app = DocsDevTestApp()

    async with app.run_test(size=(120, 48)) as pilot:
        await pilot.pause()
        home = _home(app)
        for command, _, _ in HomeScreen.MENU_ITEMS:
            btn = home.query_one(f"#cmd-{command}")
            assert btn.id == f"cmd-{command}"
