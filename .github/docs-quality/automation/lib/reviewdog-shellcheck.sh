#!/usr/bin/env bash
# Report shellcheck output via reviewdog.
set -euo pipefail

reviewdog_shellcheck_checkstyle() {
  local log_file="$1"
  local name="${2:-shellcheck}"
  shift 2 || true
  if [ ! -s "${log_file}" ]; then
    return 0
  fi
  reviewdog -f=checkstyle -name="${name}" "$@" <"${log_file}" || true
}

reviewdog_shellcheck_gcc() {
  local log_file="$1"
  local name="${2:-shellcheck}"
  shift 2 || true
  if [ ! -s "${log_file}" ]; then
    return 0
  fi
  reviewdog -efm='%f:%l:%c: %t: %m' -name="${name}" "$@" <"${log_file}" || true
}
