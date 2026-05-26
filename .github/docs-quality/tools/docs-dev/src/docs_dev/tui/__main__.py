"""Run the docs-dev Textual UI (used by textual-serve / browser mode)."""

from __future__ import annotations

from docs_dev.tui.app import DocsDevApp


def main() -> None:
    DocsDevApp().run()


if __name__ == "__main__":
    main()
