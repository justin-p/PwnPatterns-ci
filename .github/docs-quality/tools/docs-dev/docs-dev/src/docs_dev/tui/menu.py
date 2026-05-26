"""Shared menu layout and styling for Textual screens."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Grid, Vertical
from textual.widgets import Button, Static


@dataclass(frozen=True, slots=True)
class MenuEntry:
    cmd: str
    label: str
    desc: str
    variant: str = "default"
    shortcut: str | None = None


def entries_as_tuples(entries: Iterable[MenuEntry]) -> list[tuple[str, str, str]]:
    return [(e.cmd, e.label, e.desc) for e in entries]


def menu_action_id(cmd: str) -> str:
    return f"menu_{cmd.replace('-', '_')}"


def button_label(entry: MenuEntry) -> str:
    if entry.shortcut:
        return f"{entry.label}  [{entry.shortcut}]"
    return entry.label


def shortcut_bindings(
    entries: Iterable[MenuEntry],
    *,
    extra: list[Binding] | None = None,
) -> list[Binding]:
    out: list[Binding] = []
    if extra:
        out.extend(extra)
    for entry in entries:
        if entry.shortcut:
            out.append(
                Binding(
                    entry.shortcut,
                    menu_action_id(entry.cmd),
                    entry.label,
                    show=True,
                )
            )
    return out


def compose_menu_grid(
    entries: Iterable[MenuEntry],
    *,
    id_prefix: str,
) -> ComposeResult:
    with Grid(id=f"{id_prefix}-menu", classes="action-menu"):
        for entry in entries:
            classes = f"menu-card menu-card--{entry.variant}"
            btn_classes = f"menu-btn menu-btn--{entry.variant}"
            with Vertical(classes=classes):
                yield Button(
                    button_label(entry),
                    id=f"{id_prefix}-{entry.cmd}",
                    classes=btn_classes,
                    variant=_textual_variant(entry.variant),
                )
                yield Static(entry.desc, classes="menu-desc")


def _textual_variant(variant: str) -> str:
    if variant in ("primary", "success", "warning", "error"):
        return variant
    if variant in ("secondary", "accent"):
        return "default"
    return "default"
