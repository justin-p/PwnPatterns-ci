#!/usr/bin/env bash
# Set lint-logs/*.exit from tool output (CLI exit codes are not reliable for all linters).
#
# Policy (matches docs-dev parsers / CI fail policy):
#   vale     — Severity == error in vale.json (after template-list merge)
#   typos    — any JSONL record with type == typo
#   textlint — any message in textlint.json
#   rumdl    — any issue in rumdl.json (matches rumdl CLI)
#   harper   — lints with priority >= 127 only
#   languagetool — any match in languagetool.json
#   metadata — non-empty metadata.rdjsonl or verify_metadata exit != 0
set -euo pipefail

LOG_DIR="${1:-lint-logs}"
HARPER_BLOCKING_PRIORITY="${HARPER_BLOCKING_PRIORITY:-127}"

_write_exit() {
  local tool="$1"
  local code="$2"
  local detail="$3"
  echo "${code}" >"${LOG_DIR}/${tool}.exit"
  echo "${tool}: ${detail} (${tool}.exit=${code})" >&2
}

_require_jq() {
  command -v jq >/dev/null 2>&1 || {
    echo "record-lint-exits: jq is required" >&2
    exit 2
  }
}

_record_vale() {
  local json="${LOG_DIR}/vale.json"
  if [ ! -s "${json}" ]; then
    _write_exit vale 0 "no vale.json"
    return
  fi
  local count
  count="$(
    jq '[to_entries[] | .value[]? | select((.Severity // "") | ascii_downcase == "error")] | length' \
      "${json}"
  )"
  if [ "${count}" -gt 0 ]; then
    _write_exit vale 1 "${count} error(s) in JSON"
  else
    _write_exit vale 0 "0 errors in JSON"
  fi
}

_record_typos() {
  local json="${LOG_DIR}/typos.json"
  if [ ! -s "${json}" ]; then
    _write_exit typos 0 "no typos.json"
    return
  fi
  local count
  count="$(
    jq -s '[.[] | select(.type == "typo")] | length' "${json}" 2>/dev/null || echo 0
  )"
  if [ "${count}" -gt 0 ]; then
    _write_exit typos 1 "${count} typo(s) in JSON"
  else
    _write_exit typos 0 "0 typos in JSON"
  fi
}

_record_rumdl() {
  local json="${LOG_DIR}/rumdl.json"
  if [ ! -s "${json}" ]; then
    _write_exit rumdl 0 "no rumdl.json"
    return
  fi
  local count errors
  count="$(jq 'length' "${json}" 2>/dev/null || echo 0)"
  errors="$(jq '[.[] | select(.severity == "error")] | length' "${json}" 2>/dev/null || echo 0)"
  if [ "${count}" -gt 0 ]; then
    _write_exit rumdl 1 "${count} issue(s) (${errors} error, $((count - errors)) warning)"
  else
    _write_exit rumdl 0 "0 issues in JSON"
  fi
}

_record_textlint() {
  local json="${LOG_DIR}/textlint.json"
  if [ ! -s "${json}" ]; then
    _write_exit textlint 0 "no textlint.json"
    return
  fi
  local count
  count="$(
    jq '[.[]? | .messages[]?] | length' "${json}" 2>/dev/null || echo 0
  )"
  if [ "${count}" -gt 0 ]; then
    _write_exit textlint 1 "${count} message(s) in JSON"
  else
    _write_exit textlint 0 "0 messages in JSON"
  fi
}

_record_harper() {
  local json="${LOG_DIR}/harper.json"
  if [ ! -s "${json}" ]; then
    _write_exit harper 0 "no harper.json"
    return
  fi
  local blocking total
  blocking="$(
    jq --argjson p "${HARPER_BLOCKING_PRIORITY}" \
      '[.[] | .lints[]? | select((.priority // 0) >= $p)] | length' \
      "${json}"
  )"
  total="$(jq '[.[] | .lints[]?] | length' "${json}")"
  if [ "${blocking}" -gt 0 ]; then
    _write_exit harper 1 "${blocking} blocking (priority >= ${HARPER_BLOCKING_PRIORITY}), ${total} total"
  else
    _write_exit harper 0 "0 blocking (${total} non-blocking)"
  fi
}

_record_languagetool() {
  local json="${LOG_DIR}/languagetool.json"
  if [ ! -s "${json}" ]; then
    _write_exit languagetool 0 "no languagetool.json"
    return
  fi
  local count
  count="$(
    jq '[.[]? | .matches[]?] | length' "${json}" 2>/dev/null || echo 0
  )"
  if [ "${count}" -gt 0 ]; then
    _write_exit languagetool 1 "${count} match(es) in JSON"
  else
    _write_exit languagetool 0 "0 matches in JSON"
  fi
}

_record_metadata() {
  local rdjsonl="${LOG_DIR}/metadata.rdjsonl"
  local cli_exit=0
  if [ -f "${LOG_DIR}/metadata.exit" ]; then
    cli_exit="$(tr -d '[:space:]' <"${LOG_DIR}/metadata.exit")"
  fi
  local count=0
  if [ -s "${rdjsonl}" ]; then
    count="$(grep -c . "${rdjsonl}" 2>/dev/null || echo 0)"
  fi
  if [ "${cli_exit}" -ne 0 ] || [ "${count}" -gt 0 ]; then
    _write_exit metadata 1 "verify exit=${cli_exit}, ${count} rdjsonl diagnostic(s)"
  else
    _write_exit metadata 0 "ok"
  fi
}

_require_jq
_record_vale
_record_typos
_record_textlint
_record_rumdl
_record_harper
_record_languagetool
_record_metadata
