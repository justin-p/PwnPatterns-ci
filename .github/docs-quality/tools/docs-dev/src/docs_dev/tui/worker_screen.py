from __future__ import annotations

from collections.abc import Callable

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, RichLog, Static

from docs_dev.log_util import sanitize_log_line


class WorkerScreen(Screen):
    """Run a blocking task in a thread and stream log lines."""

    BINDINGS = [
        Binding("escape", "back", "Home"),
        Binding("q", "back", "Home"),
        Binding("h", "back", "Home"),
    ]

    def __init__(
        self,
        command: str,
        runner: Callable[[Callable[[str], None]], int],
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.command = command
        self._runner = runner

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(id="status", classes="-running")
        yield RichLog(id="log", highlight=True, markup=False)
        with Horizontal(id="toolbar"):
            yield Button("Home  [h]", id="home")
        yield Footer()

    def on_mount(self) -> None:
        status = self.query_one("#status", Static)
        status.update(f"[bold yellow]▶[/] [bold]{self.command}[/] — starting…")
        self._worker = self.run_worker(self._work, thread=True, exclusive=True)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "home":
            self.action_back()

    def _work(self) -> int:
        log = self.query_one("#log", RichLog)
        lines_written = 0

        def on_line(msg: str) -> None:
            nonlocal lines_written
            text = sanitize_log_line(msg)
            if not text:
                return
            for line in text.splitlines():
                if line:
                    lines_written += 1
                    self.app.call_from_thread(log.write, line)

        code = self._runner(on_line)
        if code != 0 and lines_written == 0:
            self.app.call_from_thread(
                log.write,
                "Command failed before producing output. "
                "Check scripts/ensure-platform.sh and .github/platform.ref.",
            )
        return code

    def on_worker_state_changed(self, event) -> None:
        worker = getattr(self, "_worker", None)
        if worker is None or event.worker != worker or not event.worker.is_finished:
            return
        status = self.query_one("#status", Static)
        status.remove_class("-running", "-ok", "-fail")
        try:
            code = event.worker.result
        except Exception as exc:
            status.add_class("-fail")
            status.update(f"[bold red]✗[/] [bold]{self.command}[/] failed: {exc}")
            return
        if code == 0:
            status.add_class("-ok")
            status.update(
                f"[bold green]✓[/] [bold]{self.command}[/] — finished successfully"
            )
        else:
            status.add_class("-fail")
            log = self.query_one("#log", RichLog)
            hint = (
                " See log below for details."
                if log.lines
                else " No log output was captured."
            )
            status.update(
                f"[bold red]✗[/] [bold]{self.command}[/] — exited with code {code}.{hint}"
            )

    def action_back(self) -> None:
        self.app.pop_screen()
