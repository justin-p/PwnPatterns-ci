"""Sanitize subprocess output for Textual RichLog."""

from __future__ import annotations

import re

# CSI and related ANSI escape sequences (SGR, cursor, etc.)
_ANSI_ESCAPE = re.compile(r"\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")


def strip_ansi(text: str) -> str:
    return _ANSI_ESCAPE.sub("", text)


def lines_from_capture(text: str) -> list[str]:
    """Split captured stdout/stderr into display lines (handles \\r progress updates)."""
    if not text:
        return []
    out: list[str] = []
    for raw_line in text.splitlines():
        for segment in strip_ansi(raw_line).split("\r"):
            line = segment.strip()
            if line:
                out.append(line)
    return out


def sanitize_log_line(msg: str) -> str:
    """Prepare one log line for RichLog (plain text, no markup)."""
    if "\n" in msg or "\r" in msg:
        return "\n".join(lines_from_capture(msg))
    return strip_ansi(msg).strip()
