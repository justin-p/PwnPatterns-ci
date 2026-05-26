from __future__ import annotations

import sys

from docs_dev.cli import dispatch, should_use_tui


def run() -> None:
    argv = sys.argv[1:]
    if should_use_tui(argv):
        from docs_dev.tui.app import DocsDevApp

        DocsDevApp().run()
        return
    raise SystemExit(dispatch(argv))


if __name__ == "__main__":
    run()
