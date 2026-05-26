"""textual-serve entrypoint for browser-based docs-dev UI."""

from __future__ import annotations

import argparse
import os
import shlex
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve docs-dev in a web browser")
    parser.add_argument("--host", default=os.environ.get("DOCS_DEV_WEB_HOST", "127.0.0.1"))
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("DOCS_DEV_WEB_PORT", "8765")),
    )
    args = parser.parse_args()

    repo_root = Path(os.environ.get("REPO_ROOT", Path.cwd())).resolve()
    tool_dir = Path(__file__).resolve().parents[3]
    doc_lint = os.environ.get(
        "DOC_LINT_INSTALL_DIR", str(repo_root / ".local" / "doc-linters")
    )

    launch = (
        f"cd {shlex.quote(str(tool_dir))} && "
        f"REPO_ROOT={shlex.quote(str(repo_root))} "
        f"DOC_LINT_INSTALL_DIR={shlex.quote(doc_lint)} "
        "uv run python -m docs_dev.tui"
    )

    from textual_serve.server import Server

    Server(launch, host=args.host, port=args.port, title="docs-dev").serve()


if __name__ == "__main__":
    main()
