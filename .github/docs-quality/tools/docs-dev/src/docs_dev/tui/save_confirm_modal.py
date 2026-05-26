"""Ask to save unsaved editor changes before closing or navigating away."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Static


class SaveConfirmModal(ModalScreen[bool | None]):
    """Dismiss ``True`` = save, ``False`` = discard, ``None`` = cancel."""

    DEFAULT_CSS = """
    SaveConfirmModal {
        align: center middle;
    }
    #save-dialog {
        width: 52;
        height: auto;
        padding: 1 2;
        border: solid $primary;
        background: $panel;
    }
    #save-dialog Static {
        margin-bottom: 1;
    }
    #save-dialog Horizontal {
        height: auto;
        align: center middle;
    }
    #save-dialog Button {
        margin: 0 1 0 0;
        min-width: 12;
    }
    """

    def __init__(self, path_label: str) -> None:
        super().__init__()
        self._path_label = path_label

    def compose(self) -> ComposeResult:
        with Vertical(id="save-dialog"):
            yield Static(
                f"Save changes to [bold]{self._path_label}[/] before closing?"
            )
            with Horizontal():
                yield Button("Save", id="save", variant="primary")
                yield Button("Don't save", id="discard")
                yield Button("Cancel", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save":
            self.dismiss(True)
        elif event.button.id == "discard":
            self.dismiss(False)
        elif event.button.id == "cancel":
            self.dismiss(None)
