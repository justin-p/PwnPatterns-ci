#!/usr/bin/env bash
# Print Harper grammar lint locations (same flags as docs-quality CI).
set -euo pipefail

# shellcheck source=../lib/env.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/lib/env.sh"
cd "${REPO_ROOT}"

export PATH="${DOC_LINT_INSTALL_DIR:-${REPO_ROOT}/.local/doc-linters}:${PATH}"
mapfile -t paths < <(find docs -name '*.md' | sort)

harper-cli lint "${paths[@]}" --format json \
  --user-dict-path "${HARPER_USER_DICT}" \
  --ignore "${HARPER_IGNORE_RULES}" 2>/dev/null |
  jq -r '.[] | select(.lint_count > 0) | .file as $f | .lints[] | "\($f):\(.line):\(.rule): \(.message)"'
