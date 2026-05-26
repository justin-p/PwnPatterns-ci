from docs_dev.log_util import lines_from_capture, sanitize_log_line, strip_ansi


def test_strip_ansi_sgr() -> None:
    raw = "\x1b[96mSyncing\x1b[0m Google"
    assert strip_ansi(raw) == "Syncing Google"


def test_lines_from_capture_carriage_return() -> None:
    raw = "\x1b[96mA\x1b[0m\r\x1b[96mB\x1b[0m\rSUCCESS done"
    assert lines_from_capture(raw) == ["A", "B", "SUCCESS done"]


def test_sanitize_log_line_multiline() -> None:
    raw = "\x1b[32mline1\x1b[0m\nplain"
    assert sanitize_log_line(raw) == "line1\nplain"
