#!/usr/bin/env bash
# Regenerate allowlist outputs from config/allowlists/terms.txt and patterns.txt.
set -euo pipefail

# shellcheck source=../lib/env.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/lib/env.sh"
cd "${REPO_ROOT}"

uv_run_tool "${DOCS_QUALITY_DIR}/tools/sync-allowlists" python sync_allowlists.py
