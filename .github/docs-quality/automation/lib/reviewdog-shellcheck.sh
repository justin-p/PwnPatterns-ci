#!/usr/bin/env bash
# Report shellcheck -f gcc output via reviewdog (no built-in shellcheck parser in reviewdog 0.20.x).
set -euo pipefail

reviewdog_shellcheck_gcc() {
  local log_file="$1"
  local name="${2:-shellcheck}"
  shift 2 || true
  if [ ! -s "${log_file}" ]; then
    return 0
  fi
  # reviewdog -efm matches shellcheck -f gcc lines: path:line:col: severity: message
  reviewdog -efm='%f:%l:%c: %t: %m' -name="${name}" "$@" <"${log_file}" || true
}
