#!/usr/bin/env bash
# Send prek failure output to reviewdog (unified diff + parsed log lines).
set -euo pipefail

reporter="${1:?reviewdog reporter required (e.g. github-pr-review)}"
exit_file="${2:-lint-logs/prek.exit}"
log_file="${3:-lint-logs/prek.log}"

fail_level="error"
filter_mode="file"
reviewdog_diff=()
if [ "${reporter}" = local ]; then
  fail_level=none
  filter_mode=nofilter
  reviewdog_diff=(-diff="git diff")
fi

if [ ! -f "${exit_file}" ] || [ "$(cat "${exit_file}")" -eq 0 ]; then
  exit 0
fi

reported=0

if ! git diff --quiet; then
  git --no-pager diff | reviewdog -f=diff -name=prek \
    -reporter="${reporter}" -fail-level="${fail_level}" -filter-mode="${filter_mode}" \
    "${reviewdog_diff[@]}" || true
  reported=1
fi

if [ -f "${log_file}" ]; then
  metadata_jsonl="$(mktemp)"
  shellcheck_txt="$(mktemp)"
  trap 'rm -f "${metadata_jsonl}" "${shellcheck_txt}"' EXIT

  grep -E '^❌ docs/.*\.md:' "${log_file}" | while IFS= read -r line; do
    rest="${line#❌ }"
    path="${rest%%:*}"
    msg="${rest#"${path}": }"
    msg="${msg#: }"
    jq -nc \
      --arg path "${path}" \
      --arg msg "${msg}" \
      '{
        message: (
          "[prek] metadata: " + $msg
          + " — File: " + $path
          + " — Fix YAML frontmatter / pattern metadata (see verify-metadata)."
        ),
        location: {path: $path, range: {start: {line: 1, column: 1}}},
        severity: "ERROR"
      }'
  done >"${metadata_jsonl}"

  grep -E '^\.github/.*\.sh:[0-9]+:[0-9]+:' "${log_file}" >"${shellcheck_txt}" || true

  if [ -s "${metadata_jsonl}" ]; then
    reviewdog -f=rdjsonl -name=prek \
      -reporter="${reporter}" -fail-level="${fail_level}" -filter-mode="${filter_mode}" \
      <"${metadata_jsonl}" || true
    reported=1
  fi

  if [ -s "${shellcheck_txt}" ]; then
    reviewdog -f=shellcheck -name=prek-shellcheck \
      -reporter="${reporter}" -fail-level="${fail_level}" -filter-mode="${filter_mode}" \
      <"${shellcheck_txt}" || true
    reported=1
  fi
fi

if [ "${reported}" -eq 0 ] && [ -f "${log_file}" ]; then
  echo "prek failed but produced no diff or parseable diagnostics; see ${log_file}" >&2
  tail -n 80 "${log_file}" >&2 || true
fi
