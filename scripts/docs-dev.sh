#!/usr/bin/env bash
# Bootstrap and run docs-dev (Textual TUI, CLI check, or browser UI via textual-serve).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLATFORM_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_ROOT="${REPO_ROOT:-$(cd "${PLATFORM_ROOT}/../.." && pwd)}"

export REPO_ROOT
# shellcheck source=ensure-platform.sh
source "${REPO_ROOT}/scripts/ensure-platform.sh"

export DOCS_QUALITY_DIR="${DOCS_QUALITY_DIR:-${REPO_ROOT}/.github/pwnpatterns-ci/.github/docs-quality}"
TOOL_DIR="${DOCS_QUALITY_DIR}/tools/docs-dev"

export DOC_LINT_INSTALL_DIR="${DOC_LINT_INSTALL_DIR:-${REPO_ROOT}/.local/doc-linters}"

HOST="${DOCS_DEV_WEB_HOST:-127.0.0.1}"
PORT="${DOCS_DEV_WEB_PORT:-8765}"
MODE=cli

usage() {
  cat <<'EOF' >&2
Usage: .github/pwnpatterns-ci/scripts/docs-dev.sh [COMMAND] [OPTIONS]

Run scripts/ensure-platform.sh first if .github/pwnpatterns-ci/ is missing.

Interactive TUI when stdout is a TTY. Otherwise runs check in CLI mode.

Commands:
  check                Lint changed docs vs origin/main (implies --no-ui --changed)
  fix                  Auto-fix changed docs, then re-check (implies --no-ui --changed --fix)
  setup                Install pinned CLIs, lychee, prek hooks (implies --no-ui)
  web                  Serve Textual UI in a browser (textual-serve)
  (default)            Textual TUI when stdout is a TTY; otherwise CLI check (all docs)

Options (check, fix, or --no-ui):
  --no-ui              Run check without Textual (required for scripts/CI)
  --format FORMAT      rich | json | plain  (json/plain imply --no-ui)
  --changed            Lint only docs changed vs origin/main
  --fix                Apply typos/rumdl/shfmt fixes, then re-check
  --skip-lychee        Skip offline lychee step
  --skip-actionlint    Skip workflow lint step

Options (web only):
  --host HOST          Bind address (default: 127.0.0.1, or DOCS_DEV_WEB_HOST)
  --port PORT          Bind port (default: 8765, or DOCS_DEV_WEB_PORT)

Other tools (doctor, sync, e2e, …) are available in the TUI menu.
Web UI: open the printed URL and click the docs-dev tile to start a session.
EOF
}

if ! command -v uv >/dev/null 2>&1; then
  echo "uv is required (https://docs.astral.sh/uv/)" >&2
  exit 1
fi

DOCS_DEV_ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    -h | --help)
      usage
      exit 0
      ;;
    web)
      MODE=web
      shift
      ;;
    --host)
      if [[ $# -lt 2 ]]; then
        echo "error: --host requires a value" >&2
        exit 2
      fi
      HOST="$2"
      shift 2
      ;;
    --port)
      if [[ $# -lt 2 ]]; then
        echo "error: --port requires a value" >&2
        exit 2
      fi
      PORT="$2"
      shift 2
      ;;
    --no-ui | --changed | --fix | --skip-lychee | --skip-actionlint)
      DOCS_DEV_ARGS+=("$1")
      shift
      ;;
    --format)
      if [[ $# -lt 2 ]]; then
        echo "error: --format requires a value (rich, json, plain)" >&2
        exit 2
      fi
      DOCS_DEV_ARGS+=("$1" "$2")
      shift 2
      ;;
    --format=*)
      DOCS_DEV_ARGS+=("$1")
      shift
      ;;
    check)
      DOCS_DEV_ARGS+=(--no-ui --changed)
      shift
      ;;
    fix)
      DOCS_DEV_ARGS+=(--no-ui --changed --fix)
      shift
      ;;
    setup)
      DOCS_DEV_ARGS+=(--no-ui setup)
      shift
      ;;
    *)
      echo "error: unknown argument: $1" >&2
      echo "       Use --help for allowed options." >&2
      exit 2
      ;;
  esac
done

cd "${TOOL_DIR}"
if [[ "${DOCS_DEV_VERBOSE:-}" == "1" ]]; then
  uv sync
else
  uv sync -q
fi

if [[ "${MODE}" == web ]]; then
  uv pip install -q textual-serve
  echo "Starting docs-dev web UI at http://${HOST}:${PORT}/"
  exec uv run python -m docs_dev.tui.serve --host "${HOST}" --port "${PORT}"
fi

exec uv run docs-dev "${DOCS_DEV_ARGS[@]}"
