#!/usr/bin/env bash
# Summarize lint-logs/* failures for CI (stdout). Exit 1 if any tool failed.
set -euo pipefail

LOG_DIR="${1:-lint-logs}"
MAX_LINES="${REPORT_LINT_MAX_LINES:-60}"
fail=0

_require_jq() {
  if ! command -v jq >/dev/null 2>&1; then
    echo "report-lint-failures: jq is required" >&2
    exit 2
  fi
}

_section() {
  echo ""
  echo "========== $* =========="
}

_tail_file() {
  local label="$1"
  local path="$2"
  if [ -s "${path}" ]; then
    echo "--- ${label} (last ${MAX_LINES} lines) ---"
    tail -n "${MAX_LINES}" "${path}"
  fi
}

_report_vale() {
  _section "vale"
  _tail_file "vale.stderr" "${LOG_DIR}/vale.stderr"
  if [ -s "${LOG_DIR}/vale.json" ]; then
    local count
    count="$(
      jq '[to_entries[] | .value[]? | select((.Severity // "") | ascii_downcase == "error")] | length' \
        "${LOG_DIR}/vale.json"
    )"
    echo "Vale errors: ${count}"
    jq -r '
      [to_entries[] | .key as $path | .value[]?
        | select((.Severity // "") | ascii_downcase == "error")
        | "\($path):\(.Line // 1): \(.Check // "vale"): \(.Message // "")"]
      | .[:'"${MAX_LINES}"']
      | .[]
    ' "${LOG_DIR}/vale.json" 2>/dev/null || echo "(could not parse vale.json)"
  else
    echo "(no vale.json)"
  fi
}

_report_typos() {
  _section "typos"
  _tail_file "typos.stderr" "${LOG_DIR}/typos.stderr"
  if [ -s "${LOG_DIR}/typos.json" ]; then
    local count
    count="$(grep -c '"type"[[:space:]]*:[[:space:]]*"typo"' "${LOG_DIR}/typos.json" 2>/dev/null || echo 0)"
    echo "Typos findings: ${count}"
    head -n "${MAX_LINES}" "${LOG_DIR}/typos.json"
  else
    echo "(no typos.json)"
  fi
}

_report_rumdl() {
  _section "rumdl"
  _tail_file "rumdl.stderr" "${LOG_DIR}/rumdl.stderr"
  if [ -s "${LOG_DIR}/rumdl.json" ]; then
    local count
    count="$(jq 'length' "${LOG_DIR}/rumdl.json" 2>/dev/null || echo 0)"
    echo "rumdl findings: ${count}"
    jq -r '
      [.[]? | "\(.file // "?"):\(.line // 1): \(.rule // "rumdl"): \(.message // "")"]
      | .[:'"${MAX_LINES}"']
      | .[]
    ' "${LOG_DIR}/rumdl.json" 2>/dev/null || echo "(could not parse rumdl.json)"
  else
    echo "(no rumdl.json)"
  fi
}

_report_harper() {
  _section "harper (blocking priority >= 127)"
  _tail_file "harper.stderr" "${LOG_DIR}/harper.stderr"
  if [ -s "${LOG_DIR}/harper.json" ]; then
    local blocking total
    blocking="$(
      jq '[.[] | .lints[]? | select((.priority // 0) >= 127)] | length' \
        "${LOG_DIR}/harper.json"
    )"
    total="$(jq '[.[] | .lints[]?] | length' "${LOG_DIR}/harper.json")"
    echo "Harper blocking: ${blocking} (total lints: ${total})"
    jq -r '
      [.[] | .file as $path | .lints[]?
        | select((.priority // 0) >= 127)
        | "\($path):\(.line // 1): \(.rule // "?") [p\(.priority // 0)]: \(.message // "")"
          + (if .matched_text then " — matched: " + .matched_text else "" end)]
      | .[:'"${MAX_LINES}"']
      | .[]
    ' "${LOG_DIR}/harper.json" 2>/dev/null || echo "(could not parse harper.json)"
  else
    echo "(no harper.json)"
  fi
}

_report_languagetool() {
  _section "languagetool"
  _tail_file "languagetool.stderr" "${LOG_DIR}/languagetool.stderr"
  if [ -s "${LOG_DIR}/languagetool.json" ]; then
    local count
    count="$(
      jq '[.[]? | .matches[]?] | length' "${LOG_DIR}/languagetool.json" 2>/dev/null || echo 0
    )"
    echo "LanguageTool matches: ${count}"
    jq -r '
      [.[]? | .file as $path | .matches[]?
        | "\($path):\(.line // 1): \(.rule.id // "?"): \(.message // "")"]
      | .[:'"${MAX_LINES}"']
      | .[]
    ' "${LOG_DIR}/languagetool.json" 2>/dev/null || echo "(could not parse languagetool.json)"
  else
    echo "(no languagetool.json)"
  fi
}

_report_metadata() {
  _section "metadata"
  _tail_file "metadata.stderr" "${LOG_DIR}/metadata.stderr"
  if [ -s "${LOG_DIR}/metadata.rdjsonl" ]; then
    local count
    count="$(grep -c . "${LOG_DIR}/metadata.rdjsonl" 2>/dev/null || echo 0)"
    echo "metadata diagnostics: ${count}"
    head -n "${MAX_LINES}" "${LOG_DIR}/metadata.rdjsonl"
  fi
}

_report_tool() {
  local tool="$1"
  case "${tool}" in
    vale) _report_vale ;;
    typos) _report_typos ;;
    rumdl) _report_rumdl ;;
    harper) _report_harper ;;
    languagetool) _report_languagetool ;;
    metadata) _report_metadata ;;
    *) echo "unknown tool: ${tool}" >&2 ;;
  esac
}

_require_jq

for tool in vale typos rumdl harper languagetool metadata; do
  exit_file="${LOG_DIR}/${tool}.exit"
  if [ -f "${exit_file}" ] && [ "$(tr -d '[:space:]' <"${exit_file}")" -ne 0 ]; then
    echo "::error title=${tool}::${tool} reported issues (details below)"
    echo "::group::${tool} lint log summary"
    _report_tool "${tool}"
    echo "::endgroup::"
    fail=1
  fi
done

if [ "${fail}" -ne 0 ]; then
  echo ""
  echo "One or more content linters failed. Full artifacts under ${LOG_DIR}/"
fi

exit "${fail}"
