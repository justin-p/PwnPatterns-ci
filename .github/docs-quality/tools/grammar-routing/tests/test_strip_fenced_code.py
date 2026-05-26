from __future__ import annotations

from run_languagetool_batch import prose_body_and_line_offset, strip_fenced_code_blocks


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
