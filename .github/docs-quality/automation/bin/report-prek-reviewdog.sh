#!/usr/bin/env bash
# Send prek failure output to reviewdog (unified diff + parsed log lines).
set -euo pipefail

# shellcheck source=../lib/env.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/lib/env.sh"
# shellcheck source=../lib/reviewdog-invoke.sh
source "${AUTOMATION_DIR}/lib/reviewdog-invoke.sh"

reporter="${1:-$(ci_reviewdog_reporter)}"
lint_log_dir="${CI_LINT_LOG_DIR:-lint-logs}"
exit_file="${2:-${lint_log_dir}/prek.exit}"
log_file="${3:-${lint_log_dir}/prek.log}"

fail_level="$(ci_reviewdog_fail_level)"
filter_mode="$(ci_reviewdog_filter_mode)"
reviewdog_diff=()
if [ "${reporter}" = local ]; then
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

  # Avoid pipefail terminating the script when verify-metadata prints no ❌ docs/ lines
  # while other hooks still failed (grep exit 1 in a pipeline aborted the reporter).
  while IFS= read -r line; do
    # Match verify_metadata.py stderr shape: ❌ docs/…: … (optional indentation).
    [[ "${line}" =~ ^[[:blank:]]*❌[[:blank:]]+(docs/.+\.md):\ *(.*)$ ]] || continue
    path="${BASH_REMATCH[1]}"
    msg="${BASH_REMATCH[2]}"
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
  done >"${metadata_jsonl}" < <(grep --text -E '❌[[:blank:]]+docs/.+\.md:' "${log_file}" || true)

  grep --text -E '^\.github/.*\.sh:[0-9]+:[0-9]+:' "${log_file}" >"${shellcheck_txt}" || true

  if [ -s "${metadata_jsonl}" ]; then
    reviewdog -f=rdjsonl -name=prek \
      -reporter="${reporter}" -fail-level="${fail_level}" -filter-mode="${filter_mode}" \
      <"${metadata_jsonl}" || true
    reported=1
  fi

  if [ -s "${shellcheck_txt}" ]; then
    # shellcheck source=../lib/reviewdog-shellcheck.sh
    source "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/lib/reviewdog-shellcheck.sh"
    reviewdog_shellcheck_gcc "${shellcheck_txt}" prek-shellcheck \
      -reporter="${reporter}" -fail-level="${fail_level}" -filter-mode="${filter_mode}" || true
    reported=1
  fi
fi

if [ "${reported}" -eq 0 ] && [ -f "${log_file}" ]; then
  echo "prek failed but produced no diff or parseable diagnostics; see ${log_file}" >&2
  tail -n 80 "${log_file}" >&2 || true
fi
