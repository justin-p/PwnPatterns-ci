#!/usr/bin/env bash
# Convert lint-logs/{vale,typos,rumdl,harper,languagetool}.json to reviewdog rdjsonl on stdout.
# Resolves Harper basename paths via lint-logs/path-index.json.
# Usage: prose-to-rdjsonl.sh <tool> [log-dir]
set -euo pipefail

TOOL="${1:?tool required (vale|typos|rumdl|harper|languagetool)}"
LOG_DIR="${2:-lint-logs}"

# shellcheck source=../lib/env.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/lib/env.sh"

FILTERS="${AUTOMATION_DIR}/filters"
LIB="${FILTERS}/lib"
INPUT="${LOG_DIR}/${TOOL}.json"
IDX="${LOG_DIR}/path-index.json"
FILTER="${FILTERS}/${TOOL}-to-rdjsonl.jq"

if [ ! -s "${INPUT}" ]; then
  exit 0
fi

if [ ! -f "${FILTER}" ]; then
  echo "prose-to-rdjsonl: missing filter ${FILTER}" >&2
  exit 1
fi

bash "${AUTOMATION}/bin/build-path-index.sh" "${LOG_DIR}"
PATH_INDEX="$(cat "${IDX}")"

JQ_BASE=(-r -L "${LIB}" --argjson path_index "${PATH_INDEX}")
case "${TOOL}" in
  harper)
    JQ_BASE+=(--argjson blocking "${HARPER_BLOCKING_PRIORITY:-127}")
    jq "${JQ_BASE[@]}" -f "${FILTER}" "${INPUT}"
    ;;
  typos)
    jq -c -R 'fromjson | select(.type == "typo")' "${INPUT}" | jq -s '.' |
      jq "${JQ_BASE[@]}" -f "${FILTER}"
    ;;
  vale | rumdl | languagetool)
    jq "${JQ_BASE[@]}" -f "${FILTER}" "${INPUT}"
    ;;
  *)
    echo "prose-to-rdjsonl: unknown tool ${TOOL}" >&2
    exit 1
    ;;
esac
