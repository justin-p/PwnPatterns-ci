#!/usr/bin/env bash
# Fast offline smoke tests for jq filters, sync-allowlists, and reviewdog local reporter.
# shellcheck disable=SC2015
set -euo pipefail

TESTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -z "${REPO_ROOT:-}" ]; then
  if git rev-parse --show-toplevel >/dev/null 2>&1; then
    REPO_ROOT="$(git rev-parse --show-toplevel)"
  else
    REPO_ROOT="$(cd "${TESTS_DIR}/../.." && pwd)"
  fi
fi
export REPO_ROOT
FIXTURES="${TESTS_DIR}/fixtures"
cd "${REPO_ROOT}"

# shellcheck source=../docs-quality/automation/lib/env.sh
if [ -f "${REPO_ROOT}/.github/pwnpatterns-ci/.github/docs-quality/automation/lib/env.sh" ]; then
  DOCS_QUALITY_DIR="$(cd "${REPO_ROOT}/.github/pwnpatterns-ci/.github/docs-quality" && pwd)"
  export DOCS_QUALITY_DIR
  # shellcheck source=/dev/null
  source "${DOCS_QUALITY_DIR}/automation/lib/env.sh"
elif [ -f "${REPO_ROOT}/.github/docs-quality/automation/lib/env.sh" ]; then
  # shellcheck source=/dev/null
  source "${REPO_ROOT}/.github/docs-quality/automation/lib/env.sh"
elif [ -f "${TESTS_DIR}/../docs-quality/automation/lib/env.sh" ]; then
  DOCS_QUALITY_DIR="$(cd "${TESTS_DIR}/../docs-quality" && pwd)"
  export DOCS_QUALITY_DIR
  # shellcheck source=/dev/null
  source "${DOCS_QUALITY_DIR}/automation/lib/env.sh"
else
  echo "run-component-tests: cannot find docs-quality automation/lib/env.sh" >&2
  exit 1
fi

DOCS_DEV_FIXTURES="${DOCS_QUALITY_DIR}/tools/docs-dev/tests/fixtures"
FILTERS_LIB="${DOCS_QUALITY_DIR}/automation/filters/lib"

_resolve_lychee_automation() {
  for d in \
    "${REPO_ROOT}/.github/pwnpatterns-ci/.github/lychee/automation" \
    "${REPO_ROOT}/.github/lychee/automation" \
    "${DOCS_QUALITY_DIR}/../lychee/automation"; do
    if [ -d "${d}/filters" ]; then
      cd "${d}" && pwd
      return 0
    fi
  done
  echo "run-component-tests: lychee automation dir missing (ensure-platform)" >&2
  return 1
}

_resolve_lychee_config() {
  if [ -d "${REPO_ROOT}/.github/lychee/config" ]; then
    echo "${REPO_ROOT}/.github/lychee/config"
    return 0
  fi
  echo "run-component-tests: ${REPO_ROOT}/.github/lychee/config missing" >&2
  return 1
}

LYCHEE_AUTOMATION="$(_resolve_lychee_automation)"
LYCHEE_CONFIG="$(_resolve_lychee_config)"

failures=0
pass() { echo "PASS: $*"; }
fail() {
  echo "FAIL: $*" >&2
  failures=$((failures + 1))
}

require_cmd() {
  for c in "$@"; do
    if ! command -v "${c}" >/dev/null 2>&1; then
      fail "missing required command: ${c}"
      return 1
    fi
  done
}

require_cmd jq

reviewdog_local() {
  if ! command -v reviewdog >/dev/null 2>&1; then
    if [ -x "${REPO_ROOT}/.local/doc-linters/reviewdog" ]; then
      export PATH="${REPO_ROOT}/.local/doc-linters:${PATH}"
    elif [ -f "${REPO_ROOT}/.github/docs-quality/config/manifest.env" ]; then
      # shellcheck source=/dev/null
      source "${REPO_ROOT}/.github/docs-quality/automation/lib/env.sh"
      bash "${REPO_ROOT}/.github/docs-quality/automation/install/reviewdog.sh" >/dev/null 2>&1 || true
      export PATH="${DOC_LINT_INSTALL_DIR:-/tmp}:${PATH}"
    fi
  fi
  command -v reviewdog >/dev/null 2>&1
}

assert_jsonl_nonempty() {
  local label="$1"
  local file="$2"
  if [ ! -s "${file}" ]; then
    fail "${label}: expected non-empty JSONL"
    return 1
  fi
  while IFS= read -r line; do
    echo "${line}" | jq -e . >/dev/null || {
      fail "${label}: invalid JSON line"
      return 1
    }
  done <"${file}"
  pass "${label} JSONL valid"
}

test_lychee_403_filter() {
  local hosts_json tmp
  hosts_json="$(grep -vE '^\s*(#|$)' "${LYCHEE_CONFIG}/ci-403-hosts.txt" | jq -Rsc 'split("\n") | map(select(length > 0))')"
  tmp="$(mktemp)"
  jq -f "${LYCHEE_AUTOMATION}/filters/filter-datacenter-403.jq" \
    --slurpfile hosts <(echo "${hosts_json}") \
    "${FIXTURES}/lychee/report-with-403.json" >"${tmp}"
  local errors suppressed
  errors="$(jq '.errors' "${tmp}")"
  suppressed="$(jq '.datacenter_403_suppressed' "${tmp}")"
  if [ "${errors}" -eq 1 ] && [ "${suppressed}" -ge 1 ]; then
    pass "lychee 403 filter (errors=${errors}, suppressed=${suppressed})"
  else
    fail "lychee 403 filter (errors=${errors}, suppressed=${suppressed})"
  fi
  jq -r -L "${FILTERS_LIB}" -f "${LYCHEE_AUTOMATION}/filters/to-rdjsonl.jq" "${tmp}" >"${tmp}.rdjsonl"
  assert_jsonl_nonempty "lychee to-rdjsonl" "${tmp}.rdjsonl"
  if ! jq -se '.[0].message | contains("[lychee]") and contains("Broken link")' "${tmp}.rdjsonl" |
    grep -q true; then
    fail "lychee to-rdjsonl: expected enriched message"
  else
    pass "lychee to-rdjsonl contextual message"
  fi
  if reviewdog_local; then
    if reviewdog -f=rdjsonl -name=lychee -reporter=local -fail-level=none -filter-mode=nofilter \
      <"${tmp}.rdjsonl" >/dev/null 2>&1; then
      pass "reviewdog lychee"
    else
      fail "reviewdog lychee"
    fi
  else
    echo "SKIP: reviewdog not installed"
  fi
  rm -f "${tmp}" "${tmp}.rdjsonl"
}

test_vale_jq() {
  local out tmp vale_fixture
  tmp="$(mktemp -d)"
  vale_fixture="${DOCS_DEV_FIXTURES}/vale_sample.json"
  cp "${vale_fixture}" "${tmp}/vale.json"
  out="$(mktemp)"
  bash "${DOCS_QUALITY_DIR}/automation/bin/prose-to-rdjsonl.sh" vale "${tmp}" >"${out}"
  assert_jsonl_nonempty "vale-to-rdjsonl" "${out}"
  vale_fixture="${DOCS_DEV_FIXTURES}/vale_contractions_sample.json"
  if ! jq -r -L "${FILTERS_LIB}" --argjson path_index '{}' \
    -f "${DOCS_QUALITY_DIR}/automation/filters/vale-to-rdjsonl.jq" \
    "${vale_fixture}" | jq -se 'map(select(.message | startswith("[vale]"))) | length > 0' |
    grep -q true; then
    fail "vale-to-rdjsonl: expected [vale]-prefixed messages"
  fi
  if ! jq -r -L "${FILTERS_LIB}" --argjson path_index '{}' \
    -f "${DOCS_QUALITY_DIR}/automation/filters/vale-to-rdjsonl.jq" \
    "${DOCS_DEV_FIXTURES}/vale_contractions_sample.json" |
    jq -se 'map(select(.suggestions | length > 0)) | length > 0' |
    grep -q true; then
    fail "vale-to-rdjsonl: expected suggestions for PwnPatterns.Contractions"
  fi
  pass "vale-to-rdjsonl enriched messages"
  pass "vale-to-rdjsonl suggestions"
  if reviewdog_local; then
    reviewdog -f=rdjsonl -name=vale -reporter=local -fail-level=none -filter-mode=nofilter \
      <"${out}" >/dev/null 2>&1 && pass "reviewdog vale" || fail "reviewdog vale"
  fi
  rm -f "${out}"
  rm -rf "${tmp}"
}

test_harper_jq() {
  local out tmp
  tmp="$(mktemp -d)"
  cp "${DOCS_DEV_FIXTURES}/harper_sample.json" "${tmp}/harper.json"
  cp "${DOCS_DEV_FIXTURES}/lint-paths.lst" "${tmp}/lint-paths.lst"
  out="$(mktemp)"
  bash "${DOCS_QUALITY_DIR}/automation/bin/prose-to-rdjsonl.sh" harper "${tmp}" >"${out}"
  assert_jsonl_nonempty "harper-to-rdjsonl" "${out}"
  if ! jq -se 'map(.location.path) | all(test("^docs/"))' "${out}" | grep -q true; then
    fail "harper-to-rdjsonl: expected repo-relative paths under docs/"
  fi
  pass "harper-to-rdjsonl resolves basenames to docs/ paths"
  if ! jq -se 'map(select(.message | contains("InflectedVerbAfterTo"))) | .[0].message' "${out}" |
    grep -q 'In text: «to Protected»'; then
    fail "harper-to-rdjsonl: expected matched text in reviewdog message"
  else
    pass "harper-to-rdjsonl contextual message"
  fi
  if reviewdog_local; then
    reviewdog -f=rdjsonl -name=harper -reporter=local -fail-level=none -filter-mode=nofilter \
      <"${out}" >/dev/null 2>&1 && pass "reviewdog harper" || fail "reviewdog harper"
  fi
  rm -f "${out}"
  rm -rf "${tmp}"
}

test_typos_jq() {
  local out tmp
  tmp="$(mktemp -d)"
  cp "${DOCS_DEV_FIXTURES}/typos_sample.jsonl" "${tmp}/typos.json"
  printf '%s\n' "docs/ad/general/Account_Password_Extraction_Via_Kerberoasting/Account_Password_Extraction_Via_Kerberoasting.md" >"${tmp}/lint-paths.lst"
  out="$(mktemp)"
  bash "${DOCS_QUALITY_DIR}/automation/bin/prose-to-rdjsonl.sh" typos "${tmp}" >"${out}"
  assert_jsonl_nonempty "typos-to-rdjsonl" "${out}"
  if ! jq -se '.[0].message | contains("«Identifing»") and contains("Suggested")' "${out}" | grep -q true; then
    fail "typos-to-rdjsonl: expected matched typo and suggestion in message"
  else
    pass "typos-to-rdjsonl contextual message"
  fi
  rm -f "${out}"
  rm -rf "${tmp}"
}

test_rumdl_jq() {
  local out
  out="$(mktemp)"
  jq -r -L "${FILTERS_LIB}" --argjson path_index '{}' \
    -f "${DOCS_QUALITY_DIR}/automation/filters/rumdl-to-rdjsonl.jq" \
    "${FIXTURES}/rumdl/sample.json" >"${out}"
  assert_jsonl_nonempty "rumdl-to-rdjsonl" "${out}"
  if ! jq -se '.[0].message | startswith("[rumdl]")' "${out}" | grep -q true; then
    fail "rumdl-to-rdjsonl: expected enriched message prefix"
  else
    pass "rumdl-to-rdjsonl contextual message"
  fi
  if reviewdog_local; then
    reviewdog -f=rdjsonl -name=rumdl -reporter=local -fail-level=none -filter-mode=nofilter \
      <"${out}" >/dev/null 2>&1 && pass "reviewdog rumdl" || fail "reviewdog rumdl"
  fi
  rm -f "${out}"
}

test_verify_metadata_rdjsonl() {
  if ! command -v uv >/dev/null 2>&1; then
    echo "SKIP: uv not installed (verify_metadata)"
    return 0
  fi
  local doc="${REPO_ROOT}/docs/.ci-e2e-metadata-invalid.md"
  mkdir -p "$(dirname "${doc}")"
  cp "${FIXTURES}/metadata-invalid.md" "${doc}"
  trap 'rm -f "${doc}"' RETURN
  local out
  out="$(mktemp)"
  set +e
  uv_run_tool "${DOCS_QUALITY_DIR}/tools/verify-metadata" \
    python verify_metadata.py --rdjsonl "docs/.ci-e2e-metadata-invalid.md" >"${out}" 2>/dev/null
  local ec=$?
  set -e
  if [ "${ec}" -eq 0 ]; then
    fail "verify_metadata expected failure on invalid fixture"
    rm -f "${out}"
    return 1
  fi
  assert_jsonl_nonempty "verify_metadata --rdjsonl" "${out}"
  if reviewdog_local; then
    reviewdog -f=rdjsonl -name=metadata -reporter=local -fail-level=none -filter-mode=nofilter \
      <"${out}" >/dev/null 2>&1 && pass "reviewdog metadata" || fail "reviewdog metadata"
  fi
  rm -f "${out}"
  trap - RETURN
  rm -f "${doc}"
}

test_sync_allowlists_smoke() {
  if ! command -v uv >/dev/null 2>&1; then
    echo "SKIP: uv not installed (sync_allowlists)"
    return 0
  fi
  if uv_run_tool "${DOCS_QUALITY_DIR}/tools/sync-allowlists" \
    python -c "from sync_allowlists import read_terms; from pathlib import Path; t=read_terms(Path('${REPO_ROOT}/.github/docs-quality/config/allowlists/terms.txt')); assert len(t) >= 0"; then
    pass "sync-allowlists import and read_terms"
  else
    fail "sync-allowlists smoke"
  fi
}

test_languagetool_jq() {
  local out tmp
  tmp="$(mktemp -d)"
  cp "${DOCS_DEV_FIXTURES}/languagetool_sample.json" "${tmp}/languagetool.json"
  printf '%s\n' "docs/example/nl_pattern.md" >"${tmp}/lint-paths.lst"
  out="$(mktemp)"
  bash "${DOCS_QUALITY_DIR}/automation/bin/prose-to-rdjsonl.sh" languagetool "${tmp}" >"${out}"
  assert_jsonl_nonempty "languagetool-to-rdjsonl" "${out}"
  if ! jq -se 'map(.location.path) | all(test("^docs/"))' "${out}" | grep -q true; then
    fail "languagetool-to-rdjsonl: expected repo-relative paths"
  else
    pass "languagetool-to-rdjsonl paths"
  fi
  if ! jq -se '.[0].message | contains("[languagetool]")' "${out}" | grep -q true; then
    fail "languagetool-to-rdjsonl: expected enriched message"
  else
    pass "languagetool-to-rdjsonl contextual message"
  fi
  rm -f "${out}"
  rm -rf "${tmp}"
}

test_route_grammar_paths() {
  if ! command -v uv >/dev/null 2>&1; then
    echo "SKIP: uv not installed (route_grammar_paths)"
    return 0
  fi
  local tmp log_dir
  tmp="$(mktemp -d)"
  log_dir="$(mktemp -d)"
  mkdir -p "${tmp}/docs"
  cat >"${tmp}/docs/en.md" <<'EOF'
---
language: "en"
title: "t"
---
English.
EOF
  cat >"${tmp}/docs/nl.md" <<'EOF'
---
language: "nl"
title: "t"
---
Nederlands.
EOF
  # Isolated routing config (do not use consumer language-tools.yml; repos may disable LT).
  cat >"${tmp}/language-tools.yml" <<'EOF'
default_language: en
fallback_tool: languagetool
grammar_tools:
  en: harper
  nl: languagetool
languagetool_codes:
  en: en-US
  nl: nl
languagetool_enabled: true
grammar_from_frontmatter: true
EOF
  uv_run_tool "${DOCS_QUALITY_DIR}/tools/grammar-routing" \
    python route_grammar_paths.py \
    --repo-root "${tmp}" \
    --config "${tmp}/language-tools.yml" \
    --log-dir "${log_dir}" \
    docs/en.md docs/nl.md
  if ! grep -qx 'docs/en.md' "${log_dir}/grammar-harper-paths.lst"; then
    fail "route_grammar_paths: expected en.md on harper lane"
  else
    pass "route_grammar_paths harper lane"
  fi
  if ! grep -q '^docs/nl.md' "${log_dir}/grammar-languagetool.tsv"; then
    fail "route_grammar_paths: expected nl.md on languagetool lane"
  else
    pass "route_grammar_paths languagetool lane"
  fi
  rm -rf "${tmp}" "${log_dir}"
}

test_record_lint_exits() {
  local log_dir script
  script="${DOCS_QUALITY_DIR}/automation/bin/record-lint-exits.sh"
  log_dir="$(mktemp -d)"
  cp "${DOCS_DEV_FIXTURES}/vale_sample.json" "${log_dir}/vale.json"
  cp "${DOCS_DEV_FIXTURES}/typos_sample.jsonl" "${log_dir}/typos.json"
  cp "${DOCS_DEV_FIXTURES}/rumdl_sample.json" "${log_dir}/rumdl.json"
  cp "${DOCS_DEV_FIXTURES}/harper_sample.json" "${log_dir}/harper.json"
  echo '[]' >"${log_dir}/languagetool.json"
  echo 0 >"${log_dir}/metadata.exit"
  : >"${log_dir}/metadata.rdjsonl"
  bash "${script}" "${log_dir}" 2>/dev/null
  assert_exit "record-lint-exits vale" "${log_dir}/vale.exit" 1
  assert_exit "record-lint-exits typos" "${log_dir}/typos.exit" 1
  assert_exit "record-lint-exits rumdl" "${log_dir}/rumdl.exit" 1
  assert_exit "record-lint-exits harper" "${log_dir}/harper.exit" 1
  assert_exit "record-lint-exits languagetool" "${log_dir}/languagetool.exit" 0
  echo '[{"file":"docs/x.md","matches":[{"message":"x","rule":{"id":"R","issueType":"misspelling"}}]}]' \
    >"${log_dir}/languagetool.json"
  bash "${script}" "${log_dir}" 2>/dev/null
  assert_exit "record-lint-exits languagetool (matches)" "${log_dir}/languagetool.exit" 1
  bash "${script}" "${log_dir}" 2>/dev/null
  assert_exit "record-lint-exits metadata" "${log_dir}/metadata.exit" 0
  rm -rf "${log_dir}"
}

test_load_doc_paths() {
  local -a paths=()
  export DOC_PATHS=$'docs/a.md\ndocs/b.md\n'
  mapfile -t paths < <(bash "${DOCS_QUALITY_DIR}/automation/bin/load-doc-paths.sh")
  if [ "${#paths[@]}" -ne 2 ] || [ "${paths[0]}" != "docs/a.md" ] || [ "${paths[1]}" != "docs/b.md" ]; then
    fail "load-doc-paths: expected 2 paths, got ${#paths[@]}: ${paths[*]-}"
  else
    pass "load-doc-paths multiline DOC_PATHS"
  fi
}

test_dashboard_body_jq() {
  local hosts_json tmp body
  hosts_json="$(grep -vE '^\s*(#|$)' "${LYCHEE_CONFIG}/ci-403-hosts.txt" | jq -Rsc 'split("\n") | map(select(length > 0))')"
  tmp="$(mktemp)"
  jq -f "${LYCHEE_AUTOMATION}/filters/filter-datacenter-403.jq" \
    --slurpfile hosts <(echo "${hosts_json}") \
    "${FIXTURES}/lychee/report-with-403.json" >"${tmp}"
  body="$(mktemp)"
  jq -r -f "${LYCHEE_AUTOMATION}/filters/dashboard-issue-body.jq" \
    --arg repo "ocd-nl/PwnPatterns" \
    --arg ref main \
    --arg rerun "https://github.com/ocd-nl/PwnPatterns/actions" \
    --arg outcome failure \
    "${tmp}" >"${body}"
  if [ -s "${body}" ]; then
    pass "dashboard-issue-body.jq"
  else
    fail "dashboard-issue-body.jq empty"
  fi
  rm -f "${tmp}" "${body}"
}

run_docs_quality_tools_e2e() {
  test_verify_metadata_rdjsonl
  test_sync_allowlists_smoke
}

if [ "${DOCS_QUALITY_TOOLS_E2E_ONLY:-}" = "1" ]; then
  echo "==> docs-quality tools e2e"
  run_docs_quality_tools_e2e
  if [ "${failures}" -gt 0 ]; then
    echo "${failures} docs-quality tools e2e test(s) failed" >&2
    exit 1
  fi
  echo "All docs-quality tools e2e tests passed."
  exit 0
fi

assert_exit() {
  local label="$1"
  local path="$2"
  local want="$3"
  local got
  got="$(tr -d '[:space:]' <"${path}")"
  if [ "${got}" != "${want}" ]; then
    fail "${label}: expected exit ${want}, got ${got}"
  else
    pass "${label}"
  fi
}

echo "==> component tests"
test_load_doc_paths
test_route_grammar_paths
test_record_lint_exits
test_lychee_403_filter
test_vale_jq
test_typos_jq
test_harper_jq
test_languagetool_jq
test_rumdl_jq
test_verify_metadata_rdjsonl
test_sync_allowlists_smoke
test_dashboard_body_jq

if [ "${failures}" -gt 0 ]; then
  echo "${failures} component test(s) failed" >&2
  exit 1
fi
echo "All component tests passed."
