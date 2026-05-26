from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, DataTable, Footer, Header, Input, Static, TextArea

from docs_dev.allowlist import (
    add_term,
    allowlist_casing,
    allowlist_hint,
    can_allowlist,
    dual_casing_needed,
    extract_allowlist_term,
    sync_allowlists,
    term_allowlist_status,
    terms_case_pair_from_finding,
)
from docs_dev.context import RepoContext
from docs_dev.models import FileFindings, Finding
from docs_dev.runners.check import CheckOptions, run_check, run_prose_lint
from docs_dev.tui.editor_theme import register_bearded_editor_theme
from docs_dev.tui.file_editor import (
    line_column_for_finding,
    load_file_text,
    resolve_doc_path,
)
from docs_dev.tui.fuzzy import filter_file_findings
from docs_dev.tui.paths import display_path
from docs_dev.tui.save_confirm_modal import SaveConfirmModal


def file_list_row_index(files: list[FileFindings], path: str) -> int | None:
    """Return the files-table row index for *path* after the report file list is built."""
    for idx, ff in enumerate(files):
        if ff.path == path:
            return idx
    return None


class CheckScreen(Screen):
    BINDINGS = [
        Binding("escape", "back", "Close editor / Home", priority=True),
        Binding("q", "back", "Close editor / Home", priority=True),
        Binding("h", "back", "Home"),
        Binding("r", "run", "Run check"),
        Binding("f", "fix", "Fix"),
        Binding("a", "allowlist_term", "Allowlist"),
        Binding("c", "recheck_file", "Recheck file"),
        Binding("e", "open_editor", "Open file"),
        Binding("/", "focus_file_filter", "Filter files", show=False),
        Binding("ctrl+s", "save_editor", "Save file", show=False),
        Binding("?", "help", "Shortcuts"),
    ]

    def __init__(
        self,
        *,
        changed: bool = False,
        fix: bool = False,
        skip_lychee: bool = False,
        skip_actionlint: bool = False,
    ) -> None:
        super().__init__()
        self._opts = CheckOptions(
            changed=changed,
            fix=fix,
            skip_lychee=skip_lychee,
            skip_actionlint=skip_actionlint,
        )
        self._ctx = RepoContext.from_env()
        self._report = None
        self._check_worker = None
        self._allowlist_worker = None
        self._file_lint_worker = None
        self._path_by_row: dict[str, str] = {}
        self._finding_by_row: dict[str, Finding] = {}
        self._current_file: FileFindings | None = None
        self._selected_file_path: str | None = None
        self._editor_abs_path: str | None = None
        self._editor_saved_snapshot = ""
        self._editor_panel_visible = False

    @property
    def _mode_label(self) -> str:
        if self._opts.changed:
            return "changed docs"
        return "all docs"

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(id="title")
        with Horizontal(id="toolbar"):
            yield Button("Run check  [r]", id="run", variant="primary")
            yield Button("Fix  [f]", id="fix", variant="warning")
            yield Button("Allowlist  [a]", id="allowlist", variant="success")
            yield Button("Recheck file  [c]", id="recheck-file")
            yield Button("Home  [h]", id="home")
        with Horizontal(id="results-body", classes="-editor-hidden"):
            with Vertical(id="results-left"):
                with Vertical(id="files-panel"):
                    yield Input(
                        placeholder="Filter files (fuzzy)…  press [/]",
                        id="file-filter",
                    )
                    yield Static("", id="file-filter-status", classes="muted")
                    yield DataTable(id="files", zebra_stripes=True, cursor_type="row")
                with Vertical(id="detail-panel"):
                    yield DataTable(id="findings", zebra_stripes=True, cursor_type="row")
                    with Horizontal(id="detail-actions"):
                        yield Button(
                            "Open at line  [e]",
                            id="open-editor",
                            classes="menu-btn--secondary",
                            disabled=True,
                        )
            with Vertical(id="editor-panel"):
                with Horizontal(id="editor-top"):
                    yield Static(
                        "[dim]Select a finding, then Open[/]",
                        id="editor-header",
                    )
                    yield Button("Close  [esc]", id="close-editor")
                yield TextArea(
                    id="file-editor",
                    language="markdown",
                    show_line_numbers=True,
                    soft_wrap=True,
                    tab_behavior="indent",
                )
        yield Static(id="summary")
        yield Footer()

    def on_mount(self) -> None:
        files = self.query_one("#files", DataTable)
        files.add_column("Issues", width=8, key="issues")
        files.add_column("File", key="file")
        findings = self.query_one("#findings", DataTable)
        findings.add_column("Ln", width=5, key="line")
        findings.add_column("Tool", width=8, key="tool")
        findings.add_column("Message", key="message")
        editor = self.query_one("#file-editor", TextArea)
        register_bearded_editor_theme(editor)
        editor.load_text("")
        self._set_editor_panel_visible(False)
        self._refresh_title()
        self._update_toolbar_buttons()
        self.query_one("#summary", Static).update(
            f"[dim]Press [bold]r[/] to lint or [bold]f[/] to autofix "
            f"{self._mode_label}, then re-check.[/]"
        )

    def _refresh_title(self) -> None:
        mode = "Changed files" if self._opts.changed else "All files"
        self.query_one("#title", Static).update(
            f"[bold]Documentation check[/] — [accent]{mode}[/]"
        )

    def _selected_file_path_for_lint(self) -> str | None:
        if self._current_file is not None:
            return self._current_file.path
        if self._selected_file_path:
            return self._selected_file_path
        table = self.query_one("#files", DataTable)
        if table.row_count == 0 or table.cursor_row is None:
            return None
        key = str(table.cursor_row)
        return self._path_by_row.get(key, key)

    def _worker_busy(self) -> bool:
        if self._check_worker is not None and self._check_worker.is_running:
            return True
        if self._allowlist_worker is not None and self._allowlist_worker.is_running:
            return True
        return self._file_lint_worker is not None and self._file_lint_worker.is_running

    def _update_toolbar_buttons(self) -> None:
        self._update_allowlist_button()
        self._update_open_editor_button()
        recheck_btn = self.query_one("#recheck-file", Button)
        path = self._selected_file_path_for_lint()
        busy = self._worker_busy()
        recheck_btn.disabled = path is None or busy or self._report is None
        if path:
            short = display_path(path, self._ctx.repo_root)
            if len(short) > 36:
                short = "…" + short[-35:]
            recheck_btn.label = f"Recheck  [c]  {short}"
        else:
            recheck_btn.label = "Recheck file  [c]"

    def _update_allowlist_button(self) -> None:
        btn = self.query_one("#allowlist", Button)
        if self._worker_busy():
            btn.disabled = True
            return
        finding = self._selected_finding()
        if finding is None:
            btn.disabled = True
            return
        casing = allowlist_casing(self._ctx)
        term = extract_allowlist_term(finding, casing=casing)
        hint = allowlist_hint(finding, casing=casing)
        if hint:
            btn.disabled = True
            btn.label = "Allowlist  [a]"
            return
        if term is None:
            btn.disabled = True
            btn.label = "Allowlist  [a]"
            return
        btn.disabled = False
        if dual_casing_needed(self._ctx, finding):
            pair = terms_case_pair_from_finding(finding)
            if pair:
                alias, preferred = pair
                btn.label = f"Allow Dual casing {alias} → {preferred}  [a]"
            else:
                btn.label = "Allow Dual casing  [a]"
            return
        covered = term_allowlist_status(self._ctx, term)
        if covered:
            btn.label = f"Allowlist '{term}' (as {covered})  [a]"
        else:
            btn.label = f"Allowlist '{term}'  [a]"

    def _selected_finding(self) -> Finding | None:
        table = self.query_one("#findings", DataTable)
        if table.row_count == 0 or table.cursor_row is None:
            return None
        return self._finding_by_row.get(str(table.cursor_row))

    def _update_open_editor_button(self) -> None:
        btn = self.query_one("#open-editor", Button)
        finding = self._selected_finding()
        btn.disabled = (
            self._worker_busy()
            or finding is None
            or self._current_file is None
        )

    def _set_editor_panel_visible(self, visible: bool) -> None:
        self._editor_panel_visible = visible
        body = self.query_one("#results-body", Horizontal)
        if visible:
            body.remove_class("-editor-hidden")
        else:
            body.add_class("-editor-hidden")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "run":
            self.action_run()
        elif event.button.id == "fix":
            self.action_fix()
        elif event.button.id == "allowlist":
            self.action_allowlist_term()
        elif event.button.id == "recheck-file":
            self.action_recheck_file()
        elif event.button.id == "open-editor":
            self.action_open_editor()
        elif event.button.id == "close-editor":
            self.action_close_editor()
        elif event.button.id == "home":
            self.action_back()

    def action_help(self) -> None:
        self.notify(
            "r Run · / filter · ↑↓ finding · e Open · esc/q close editor · "
            "h Home · a allowlist",
            title="Check screen",
            timeout=8,
        )

    def action_open_editor(self) -> None:
        finding = self._selected_finding()
        if finding is None or self._current_file is None:
            self.notify("Select a finding first", severity="warning", timeout=4)
            return
        self._open_editor(path=self._current_file.path, finding=finding)

    def _save_editor_file(self, *, notify: bool = False) -> bool:
        """Write the editor buffer to disk when a file is open."""
        if self._editor_abs_path is None or not self._editor_panel_visible:
            return True
        editor = self.query_one("#file-editor", TextArea)
        try:
            Path(self._editor_abs_path).write_text(editor.text, encoding="utf-8")
        except OSError as exc:
            if notify:
                self.notify(f"Save failed: {exc}", severity="error", timeout=8)
            return False
        if notify:
            self.notify(
                display_path(self._editor_abs_path, self._ctx.repo_root),
                title="Saved",
                timeout=4,
            )
        return True

    def action_save_editor(self) -> None:
        if self._editor_abs_path is None:
            self.notify("Nothing to save", severity="warning", timeout=3)
            return
        if self._save_editor_file(notify=True):
            self._editor_saved_snapshot = self.query_one(
                "#file-editor", TextArea
            ).text

    def action_close_editor(self) -> None:
        if not self._editor_panel_visible:
            return
        self._confirm_editor_close_if_dirty(self._reset_editor_ui)

    def _editor_is_dirty(self) -> bool:
        if not self._editor_panel_visible or self._editor_abs_path is None:
            return False
        editor = self.query_one("#file-editor", TextArea)
        return editor.text != self._editor_saved_snapshot

    def _revert_editor_to_snapshot(self) -> None:
        editor = self.query_one("#file-editor", TextArea)
        editor.load_text(self._editor_saved_snapshot)

    def _confirm_editor_close_if_dirty(
        self,
        on_done: Callable[[], None],
        *,
        on_cancel: Callable[[], None] | None = None,
    ) -> None:
        if not self._editor_is_dirty():
            on_done()
            return
        path_label = (
            display_path(self._editor_abs_path, self._ctx.repo_root)
            if self._editor_abs_path
            else "file"
        )

        def handle(result: bool | None) -> None:
            if result is None:
                if on_cancel is not None:
                    on_cancel()
                return
            if result:
                if not self._save_editor_file():
                    if on_cancel is not None:
                        on_cancel()
                    return
                self._editor_saved_snapshot = self.query_one(
                    "#file-editor", TextArea
                ).text
            else:
                self._revert_editor_to_snapshot()
            on_done()

        self.app.push_screen(SaveConfirmModal(path_label), handle)

    def _focus_files_table(self) -> None:
        files = self.query_one("#files", DataTable)
        if files.row_count > 0:
            files.focus()

    def _focus_findings_table(self) -> None:
        findings = self.query_one("#findings", DataTable)
        if findings.row_count > 0:
            findings.focus()

    def _reset_editor_ui(self) -> None:
        self._editor_abs_path = None
        self._editor_saved_snapshot = ""
        self._set_editor_panel_visible(False)
        self.query_one("#file-editor", TextArea).load_text("")
        self.query_one("#editor-header", Static).update(
            "[dim]Select a finding, then Open[/]"
        )
        self._focus_findings_table()

    def action_focus_file_filter(self) -> None:
        self.query_one("#file-filter", Input).focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id != "file-filter" or self._report is None:
            return
        self._populate_files_table()

    def action_run(self) -> None:
        self._confirm_editor_close_if_dirty(lambda: self._start_check(fix=False))

    def action_fix(self) -> None:
        self._confirm_editor_close_if_dirty(lambda: self._start_check(fix=True))

    def _start_check(self, *, fix: bool) -> None:
        if self._check_worker is not None and self._check_worker.is_running:
            return
        verb = "autofix" if fix else "check"
        run_btn = self.query_one("#run", Button)
        fix_btn = self.query_one("#fix", Button)
        run_btn.disabled = True
        fix_btn.disabled = True
        self._update_toolbar_buttons()
        self.query_one("#summary", Static).update(
            f"[yellow]Running {verb} on {self._mode_label}…[/]"
        )
        self.query_one("#findings", DataTable).clear()
        self._finding_by_row.clear()
        self._current_file = None
        self.query_one("#file-filter", Input).value = ""
        self.query_one("#file-filter-status", Static).update("")
        table = self.query_one("#files", DataTable)
        table.clear()
        self._path_by_row.clear()
        self._report = None
        self._reset_editor_ui()
        opts = CheckOptions(
            changed=self._opts.changed,
            fix=fix,
            skip_lychee=self._opts.skip_lychee,
            skip_actionlint=self._opts.skip_actionlint,
        )
        self._check_worker = self.run_worker(
            lambda: run_check(self._ctx, opts),
            thread=True,
            exclusive=True,
        )

    def action_allowlist_term(self) -> None:
        finding = self._selected_finding()
        if finding is None:
            self.notify("Select a finding first", severity="warning", timeout=4)
            return
        casing = allowlist_casing(self._ctx)
        term = extract_allowlist_term(finding, casing=casing)
        hint = allowlist_hint(finding, casing=casing)
        if hint:
            self.notify(hint, severity="warning", timeout=10)
            return
        if term is None:
            self.notify(
                "This finding cannot be allowlisted from the TUI.",
                severity="warning",
                timeout=6,
            )
            return
        if self._allowlist_worker is not None and self._allowlist_worker.is_running:
            return

        allow_btn = self.query_one("#allowlist", Button)
        allow_btn.disabled = True
        file_path = self._current_file.path if self._current_file else None
        self.notify(f"Adding '{term}' to allowlist…", timeout=3)

        def work() -> tuple[bool, str, str | None, list[Finding]]:
            added, msg = add_term(self._ctx, term, finding=finding)
            if not added:
                return False, msg, file_path, []
            rc = sync_allowlists(self._ctx)
            if rc != 0:
                return False, f"{msg}; sync exited {rc}", file_path, []
            findings: list[Finding] = []
            if file_path:
                findings = run_prose_lint(self._ctx, [file_path])
            return True, f"{msg}. Re-scanned file.", file_path, findings

        self._allowlist_worker = self.run_worker(
            lambda: work(),
            thread=True,
            exclusive=True,
            name="allowlist",
        )
        self._update_toolbar_buttons()

    def action_recheck_file(self) -> None:
        if self._report is None:
            self.notify("Run a check first ([r])", severity="warning", timeout=4)
            return
        path = self._selected_file_path_for_lint()
        if path is None:
            self.notify("Select a file in the list first", severity="warning", timeout=4)
            return
        if self._worker_busy():
            return

        self.notify(f"Re-linting {display_path(path, self._ctx.repo_root)}…", timeout=3)
        self._update_toolbar_buttons()

        def work() -> tuple[str, list[Finding]]:
            return path, run_prose_lint(self._ctx, [path])

        self._file_lint_worker = self.run_worker(
            lambda: work(),
            thread=True,
            exclusive=True,
            name="recheck-file",
        )

    def on_worker_state_changed(self, event) -> None:
        file_worker = getattr(self, "_file_lint_worker", None)
        if (
            file_worker is not None
            and event.worker == file_worker
            and event.worker.is_finished
        ):
            self._file_lint_worker = None
            self._update_toolbar_buttons()
            try:
                path, findings = event.worker.result
            except Exception as exc:
                self.notify(f"Recheck failed: {exc}", severity="error", timeout=8)
                return
            self._apply_file_rescan(path, findings)
            count = len(findings)
            self.notify(
                f"{display_path(path, self._ctx.repo_root)}: {count} finding(s)",
                title="Recheck",
                timeout=6,
            )
            return

        allow_worker = getattr(self, "_allowlist_worker", None)
        if (
            allow_worker is not None
            and event.worker == allow_worker
            and event.worker.is_finished
        ):
            self._allowlist_worker = None
            self._update_toolbar_buttons()
            try:
                ok, msg, file_path, findings = event.worker.result
            except Exception as exc:
                self.notify(f"Allowlist failed: {exc}", severity="error", timeout=8)
                return
            if ok:
                self.notify(msg, title="Allowlist", timeout=8)
                if file_path is not None:
                    self._apply_file_rescan(file_path, findings)
            else:
                self.notify(msg, severity="warning", timeout=8)
            return

        worker = getattr(self, "_check_worker", None)
        if worker is None or event.worker != worker or not event.worker.is_finished:
            return
        run_btn = self.query_one("#run", Button)
        fix_btn = self.query_one("#fix", Button)
        run_btn.disabled = False
        fix_btn.disabled = False
        try:
            report = event.worker.result
        except Exception as exc:
            self.query_one("#summary", Static).update(f"[red]Error: {exc}[/]")
            return

        self._finding_by_row.clear()
        self._current_file = None
        self.query_one("#findings", DataTable).clear()
        self._report = report
        self._refresh_summary()
        if report.files:
            self._populate_files_table(select_path=report.files[0].path)
        else:
            self._populate_files_table()
        self._focus_files_table()
        self._update_toolbar_buttons()

    def _file_filter_query(self) -> str:
        return self.query_one("#file-filter", Input).value

    def _visible_files(self) -> list[FileFindings]:
        if self._report is None:
            return []
        return filter_file_findings(
            self._report.files,
            self._file_filter_query(),
            repo_root=self._ctx.repo_root,
        )

    def _update_file_filter_status(self, visible: list[FileFindings]) -> None:
        status = self.query_one("#file-filter-status", Static)
        if self._report is None:
            status.update("")
            return
        q = self._file_filter_query().strip()
        total = len(self._report.files)
        shown = len(visible)
        if q:
            status.update(f"Showing {shown} of {total} file(s) matching “{q}”")
        else:
            status.update(f"{total} file(s) with findings")

    def _populate_files_table(self, *, select_path: str | None = None) -> None:
        table = self.query_one("#files", DataTable)
        table.clear()
        self._path_by_row.clear()
        visible = self._visible_files()
        self._update_file_filter_status(visible)

        for ff in visible:
            self._path_by_row[ff.path] = ff.path
            table.add_row(
                str(ff.count),
                display_path(ff.path, self._ctx.repo_root),
                key=ff.path,
            )

        if not visible:
            self._current_file = None
            self._selected_file_path = None
            self.query_one("#findings", DataTable).clear()
            self._finding_by_row.clear()
            self._clear_editor()
            self._update_toolbar_buttons()
            return

        idx = 0
        if select_path is not None:
            found = file_list_row_index(visible, select_path)
            if found is not None:
                idx = found
        table.move_cursor(row=idx)
        path = visible[idx].path
        self._selected_file_path = path
        for ff in visible:
            if ff.path == path:
                self._show_file_findings(ff)
                return
        if self._report is not None:
            for ff in self._report.files:
                if ff.path == path:
                    self._show_file_findings(ff)
                    return

    def _truncate(self, text: str, limit: int = 72) -> str:
        if len(text) <= limit:
            return text
        return text[: limit - 1] + "…"

    def _show_file_findings(self, ff: FileFindings) -> None:
        prior = self._current_file
        if (
            prior is not None
            and prior.path != ff.path
            and self._editor_is_dirty()
        ):

            def proceed() -> None:
                self._apply_file_findings(ff)

            def cancel() -> None:
                table = self.query_one("#files", DataTable)
                idx = file_list_row_index(self._visible_files(), prior.path)
                if idx is not None:
                    table.move_cursor(row=idx)

            self._confirm_editor_close_if_dirty(proceed, on_cancel=cancel)
            return
        self._apply_file_findings(ff)

    def _apply_file_findings(self, ff: FileFindings) -> None:
        self._current_file = ff
        table = self.query_one("#findings", DataTable)
        table.clear()
        self._finding_by_row.clear()
        for idx, f in enumerate(ff.findings):
            row_key = str(idx)
            self._finding_by_row[row_key] = f
            mark = "★ " if can_allowlist(f, casing=allowlist_casing(self._ctx)) else ""
            table.add_row(
                str(f.line),
                f.tool,
                mark + self._truncate(f.message),
                key=row_key,
            )
        if ff.findings:
            table.move_cursor(row=0)
        self._update_toolbar_buttons()

    def _clear_editor(self) -> None:
        self._confirm_editor_close_if_dirty(self._reset_editor_ui)

    def _open_editor(self, *, path: str, finding: Finding | None) -> None:
        abs_path = resolve_doc_path(self._ctx.repo_root, path)
        abs_key = str(abs_path)
        if (
            self._editor_abs_path is not None
            and self._editor_abs_path != abs_key
            and self._editor_panel_visible
            and self._editor_is_dirty()
        ):
            self._confirm_editor_close_if_dirty(
                lambda: self._do_open_editor(
                    path=path, finding=finding, abs_path=abs_path, abs_key=abs_key
                )
            )
            return
        self._do_open_editor(
            path=path, finding=finding, abs_path=abs_path, abs_key=abs_key
        )

    def _do_open_editor(
        self,
        *,
        path: str,
        finding: Finding | None,
        abs_path: Path,
        abs_key: str,
    ) -> None:
        editor = self.query_one("#file-editor", TextArea)
        header = self.query_one("#editor-header", Static)

        self._set_editor_panel_visible(True)

        if not abs_path.is_file():
            self._editor_abs_path = None
            editor.language = "markdown"
            editor.load_text(f"# File not found\n{abs_path}\n")
            header.update(f"[red]{display_path(path, self._ctx.repo_root)}[/]")
            editor.focus()
            return

        if self._editor_abs_path != abs_key:
            try:
                text = load_file_text(abs_path)
            except OSError as exc:
                self._editor_abs_path = None
                editor.language = "markdown"
                editor.load_text(f"# Cannot read file\n{exc}\n")
                header.update(f"[red]{display_path(path, self._ctx.repo_root)}[/]")
                editor.focus()
                return
            editor.language = "markdown"
            editor.load_text(text)
            self._editor_abs_path = abs_key
            self._editor_saved_snapshot = text

        self._jump_editor_to_finding(path, finding)

    def _jump_editor_to_finding(
        self, path: str, finding: Finding | None
    ) -> None:
        editor = self.query_one("#file-editor", TextArea)
        header = self.query_one("#editor-header", Static)
        line_count = editor.document.line_count
        row, col = line_column_for_finding(finding, line_count=line_count)
        line_display = row + 1
        short = display_path(path, self._ctx.repo_root)
        if finding is not None:
            header.update(
                f"[bold]{short}[/] · line {line_display} · {finding.tool}"
            )
        else:
            header.update(f"[bold]{short}[/] · line {line_display}")

        editor.move_cursor((row, col), center=True)
        editor.scroll_cursor_visible(animate=False)
        editor.focus()

    def _sync_editor_to_finding(self, finding: Finding) -> None:
        """Move the open editor to *finding* when it matches the current file."""
        if not self._editor_panel_visible or self._current_file is None:
            return
        path = self._current_file.path
        abs_key = str(resolve_doc_path(self._ctx.repo_root, path))
        if self._editor_abs_path == abs_key:
            self._jump_editor_to_finding(path, finding)
            return
        if self._editor_abs_path is not None:
            self._open_editor(path=path, finding=finding)

    def _refresh_summary(self) -> None:
        if self._report is None:
            return
        total_findings = sum(ff.count for ff in self._report.files)
        if self._report.passed and not self._report.files:
            summary = (
                f"[bold green]✓ PASS[/] — no prose findings in {self._mode_label}"
            )
        elif self._report.passed:
            summary = (
                f"[bold green]✓ PASS[/] — {total_findings} finding(s) in "
                f"{len(self._report.files)} file(s) (non-blocking)"
            )
        else:
            summary = (
                f"[bold red]✗ FAIL[/] — {total_findings} finding(s) in "
                f"{len(self._report.files)} file(s)"
            )
        self.query_one("#summary", Static).update(summary)

    def _apply_file_rescan(self, path: str, findings: list[Finding]) -> None:
        """Update the file list and findings panel after allowlist + single-file lint."""
        if self._report is None:
            return

        sorted_findings = sorted(findings, key=lambda f: (f.line, f.column, f.tool))
        new_ff = FileFindings(path=path, findings=sorted_findings)

        replaced = False
        for idx, ff in enumerate(self._report.files):
            if ff.path == path:
                if new_ff.count == 0:
                    del self._report.files[idx]
                else:
                    self._report.files[idx] = new_ff
                replaced = True
                break
        if not replaced and new_ff.count > 0:
            self._report.files.append(new_ff)
        self._report.files.sort(key=lambda ff: (-ff.count, ff.path))
        self._refresh_summary()

        if new_ff.count > 0:
            self._populate_files_table(select_path=path)
            if (
                self._current_file is not None
                and self._current_file.path == path
                and self._current_file.findings
            ):
                self._focus_findings_table()
            else:
                self._focus_files_table()
            return

        self._populate_files_table()
        self._focus_files_table()
        self.notify(
            "No findings left in this file after re-scan.",
            timeout=6,
        )

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.row_key is None or self._report is None:
            return
        if event.data_table.id == "files":
            path = self._path_by_row.get(
                str(event.row_key.value), str(event.row_key.value)
            )
            self._selected_file_path = path
            for ff in self._report.files:
                if ff.path == path:
                    self._show_file_findings(ff)
                    return
        if event.data_table.id == "findings":
            finding = self._selected_finding()
            if finding is not None:
                self._sync_editor_to_finding(finding)
            self._update_toolbar_buttons()

    def action_back(self) -> None:
        if self._editor_panel_visible:
            self.action_close_editor()
            return
        self._confirm_editor_close_if_dirty(lambda: self.app.pop_screen())
