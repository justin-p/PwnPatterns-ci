#!/usr/bin/env bash
# Emit one reviewdog review per CI run for prose linters + metadata (avoids per-tool
# outdated-comment churn and races). prek is reported separately (diff + gcc formats).
set -euo pipefail

# shellcheck source=../lib/env.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/lib/env.sh"
# shellcheck source=../lib/reviewdog-invoke.sh
source "${AUTOMATION_DIR}/lib/reviewdog-invoke.sh"

reporter="${1:-$(ci_reviewdog_reporter)}"

LOG_DIR="${CI_LINT_LOG_DIR:-${LINT_LOG_DIR:-lint-logs}}"
combined="$(mktemp)"
trap 'rm -f "${combined}"' EXIT

for tool in vale typos textlint rumdl harper languagetool; do
  log="${LOG_DIR}/${tool}.json"
  if [ ! -s "${log}" ]; then
    continue
  fi
  if ! jq -e . "${log}" >/dev/null 2>&1; then
    continue
  fi
  bash "${AUTOMATION_DIR}/bin/prose-to-rdjsonl.sh" "${tool}" "${LOG_DIR}" >>"${combined}" || true
done

if [ -s "${LOG_DIR}/metadata.rdjsonl" ]; then
  cat "${LOG_DIR}/metadata.rdjsonl" >>"${combined}"
fi

if [ -s "${combined}" ]; then
  reviewdog_rdjsonl docs-quality "${reporter}" <"${combined}"
fi
