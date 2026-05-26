#!/usr/bin/env bash
# Shared reviewdog reporter settings for docs-quality CI.
set -euo pipefail

ci_reviewdog_reporter() {
  if [ "${CI_REVIEWDOG_MODE:-}" = local ] || [ -z "${GITHUB_ACTIONS:-}" ]; then
    echo local
  elif [ "${GITHUB_EVENT_NAME:-}" = pull_request ]; then
    echo github-pr-review
  else
    echo github-check
  fi
}

ci_reviewdog_fail_level() {
  if [ "$(ci_reviewdog_reporter)" = local ]; then
    echo none
  else
    echo error
  fi
}

# Post every diagnostic on each run (nofilter). github-pr-review falls back to check
# annotations for lines outside the diff hunk; filter-mode=file often dropped findings
# when paths were absolute or unchanged lines were not in the latest diff.
ci_reviewdog_filter_mode() {
  if [ "$(ci_reviewdog_reporter)" = local ]; then
    echo nofilter
  else
    echo nofilter
  fi
}

reviewdog_rdjsonl() {
  local name="$1"
  local reporter="${2:-$(ci_reviewdog_reporter)}"
  reviewdog -f=rdjsonl -name="${name}" \
    -reporter="${reporter}" \
    -fail-level="$(ci_reviewdog_fail_level)" \
    -filter-mode="$(ci_reviewdog_filter_mode)" \
    "$@" || true
}
