from __future__ import annotations

from lt_preprocess import (
    prepare_md_for_languagetool,
    prose_body_and_line_offset,
    strip_fenced_code_blocks,
)


def test_strip_fenced_code_preserves_line_numbers() -> None:
    text = "---\ntitle: x\nlanguage: nl\n---\nIntro line.\n\n```bash\necho secret typo\n```\n\nAfter fence.\n"
    body, offset = prose_body_and_line_offset(text)
    stripped = strip_fenced_code_blocks(body)
    lines = stripped.splitlines()
    assert offset == 4
    assert lines[0] == "Intro line."
    assert lines[1] == ""
    assert lines[2] == ""
    assert lines[3] == ""
    assert lines[4] == ""
    assert lines[6] == "After fence."


def test_prepare_md_blanks_lines_with_bbcode_color_callout() -> None:
    raw = (
        "---\r\nlanguage: nl\r\n---\r\n"
        "[color=sl-orange][b]Let op[/b][/color]: Idealiter ...\n"
        "Normal prose line.\n"
    )
    body, offset = prepare_md_for_languagetool(raw)
    assert offset == 3
    assert "sl-orange" not in body
    assert "Let op" not in body
    assert "Idealiter" not in body
    lines = body.splitlines()
    assert lines[0] == ""
    assert lines[1] == "Normal prose line."


def test_prepare_md_blanks_html_comments_preserving_newlines() -> None:
    raw = "---\nlanguage: nl\n---\nline1\n<!-- secret\nmulti\nline -->\nline2\n"
    body, _ = prepare_md_for_languagetool(raw)
    assert "secret" not in body
    assert "multi" not in body
    # Newlines should remain, so the final line still exists.
    assert body.splitlines()[-1] == "line2"
