#!/usr/bin/env bash
# Build lint-logs/path-index.json: basename -> repo-relative path (for reviewdog filter-mode=file).
set -euo pipefail

LOG_DIR="${1:-lint-logs}"
LST="${LOG_DIR}/lint-paths.lst"
OUT="${LOG_DIR}/path-index.json"

if [ ! -s "${LST}" ]; then
  echo '{}' >"${OUT}"
  exit 0
fi

jq -R 'select(length > 0)' "${LST}" |
  jq -s 'reduce .[] as $p ({}; .[($p | split("/") | .[-1])] = $p)' \
    >"${OUT}"
