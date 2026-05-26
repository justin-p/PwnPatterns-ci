"""LanguageTool markdown preprocessing shared by batch runner and routing.

This module aims to keep LanguageTool results focused on human prose by:
- stripping YAML frontmatter (metadata)
- blanking fenced code blocks (keep line count)
- blanking HTML comments (keep line breaks)
- blanking lines that use BBCode color callouts (e.g. [color=sl-orange]... so LT does not
  see label text like "Let op :")
- removing remaining BBCode-style tags on other lines (e.g. [b]...[/b])

The transformations preserve line breaks so line numbers remain stable.
"""

from __future__ import annotations

import re

# Optional UTF-8 BOM + CRLF/LF tolerant frontmatter matcher.
FRONTMATTER_RE = re.compile(r"^\ufeff?---\r?\n(.*?)\r?\n---\r?\n", re.DOTALL)

FENCE_OPEN_RE = re.compile(r"^(```+|~~~+)")

# HTML comments can span multiple lines.
HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)

# Closed-world BBCode tags actually used in PwnPatterns docs.
BBCODE_TAG_RE = re.compile(
    r"\[(?:/?b|/?i|/?color(?:=[^\]]+)?|/?color(?:=\"[^\"]+\")?)\]",
    re.IGNORECASE,
)

# Opening [color markers on a line denote a formatted callout; blank the whole line for LT
# so stripping tags alone cannot leave typography like "Let op :" for Dutch punctuation rules.
BBCODE_COLOR_OPEN_RE = re.compile(r"\[color", re.IGNORECASE)


def blank_bbcode_color_lines(text: str) -> str:
    """Replace each line containing a [color opener with spaces (preserve line endings)."""

    lines = text.splitlines(keepends=True)
    out: list[str] = []
    for line in lines:
        body = line.rstrip("\r\n")
        newline = line[len(body) :]
        if BBCODE_COLOR_OPEN_RE.search(body):
            out.append(" " * len(body) + newline)
        else:
            out.append(line)
    return "".join(out)


def prose_body_and_line_offset(text: str) -> tuple[str, int]:
    """Return markdown body (no YAML frontmatter) and 1-based line offset for diagnostics."""
    match = FRONTMATTER_RE.match(text)
    if not match:
        return text, 0
    prefix = text[: match.end()]
    line_offset = prefix.count("\n")
    return text[match.end() :], line_offset


def strip_fenced_code_blocks(text: str) -> str:
    """Blank fenced code blocks while preserving line count for LanguageTool offsets."""
    lines = text.splitlines(keepends=True)
    out: list[str] = []
    in_fence = False
    for line in lines:
        body = line.rstrip("\r\n")
        newline = line[len(body) :]
        open_match = FENCE_OPEN_RE.match(body) if not in_fence else None
        if open_match:
            in_fence = True
            out.append(newline)
            continue
        if in_fence:
            if FENCE_OPEN_RE.match(body):
                in_fence = False
            out.append(newline)
            continue
        out.append(line)
    return "".join(out)


def _blank_span_keep_newlines(span: str) -> str:
    """Replace all non-newline chars with spaces."""
    return "".join("\n" if ch == "\n" else " " for ch in span)


def strip_html_comments(text: str) -> str:
    """Blank HTML comments while preserving newlines."""

    def repl(m: re.Match[str]) -> str:
        return _blank_span_keep_newlines(m.group(0))

    return HTML_COMMENT_RE.sub(repl, text)


def strip_bbcode_tags(text: str) -> str:
    """Blank BBCode tags (keep content between tags)."""

    def repl(m: re.Match[str]) -> str:
        return " " * len(m.group(0))

    return BBCODE_TAG_RE.sub(repl, text)


def prepare_md_for_languagetool(full_text: str) -> tuple[str, int]:
    """Return (prepared_body, line_offset_from_frontmatter)."""
    body, line_offset = prose_body_and_line_offset(full_text)
    body = strip_fenced_code_blocks(body)
    body = strip_html_comments(body)
    body = blank_bbcode_color_lines(body)
    body = strip_bbcode_tags(body)
    return body, line_offset

