#!/usr/bin/env bash
# Shared docs-quality CI steps (source from run-ci-e2e.sh / workflows; do not execute).
set -euo pipefail

if [ -n "${CI_STEPS_LOADED:-}" ]; then
  return 0
fi
export CI_STEPS_LOADED=1

# shellcheck source=env.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/env.sh"

_DQ_AUTOMATION_DIR="${AUTOMATION_DIR}"
_DQ_DOCS_QUALITY_DIR="${DOCS_QUALITY_DIR}"
_DQ_REPO_ROOT="${REPO_ROOT}"
_LYCHEE_LIB=""
for _lychee_candidate in \
  "${REPO_ROOT}/.github/pwnpatterns-ci/.github/lychee/automation/lib" \
  "${REPO_ROOT}/.github/lychee/automation/lib" \
  "${DOCS_QUALITY_DIR}/../lychee/automation/lib"; do
  if [ -f "${_lychee_candidate}/ci-steps-lychee.sh" ]; then
    _LYCHEE_LIB="$(cd "${_lychee_candidate}" && pwd)"
    break
  fi
done
if [ -z "${_LYCHEE_LIB}" ]; then
  echo "ci-steps: missing lychee automation lib (platform checkout required)" >&2
  exit 1
fi
LYCHEE_CI_LIB="${_LYCHEE_LIB}/ci-steps-lychee.sh"
# shellcheck source=/dev/null
source "${LYCHEE_CI_LIB}"
export AUTOMATION_DIR="${_DQ_AUTOMATION_DIR}"
export DOCS_QUALITY_DIR="${_DQ_DOCS_QUALITY_DIR}"
export REPO_ROOT="${_DQ_REPO_ROOT}"
unset _DQ_AUTOMATION_DIR _DQ_DOCS_QUALITY_DIR _DQ_REPO_ROOT

CI_LINT_LOG_DIR="${CI_LINT_LOG_DIR:-lint-logs}"
CI_DOC_SKIP="${CI_DOC_SKIP:-false}"
CI_DOC_SCAN_MODE="${CI_DOC_SCAN_MODE:-all}"
declare -a CI_DOC_PATHS=()

ci_load_manifest() {
  if [ -n "${GITHUB_ENV:-}" ] && [ -w "${GITHUB_ENV}" ]; then
    {
      grep -vE '^\s*(#|$)' "${MANIFEST}"
      echo "HARPER_IGNORE_RULES<<EOF"
      grep -vE '^\s*(#|$)' "${CONSUMER_CONFIG_DIR}/harper.ignore-rules" | paste -sd, -
      echo "EOF"
      echo "HARPER_USER_DICT=${HARPER_USER_DICT}"
    } >>"${GITHUB_ENV}"
  fi
  export HARPER_USER_DICT
  if [ -f "${CONSUMER_CONFIG_DIR}/harper.ignore-rules" ]; then
    HARPER_IGNORE_RULES="$(
      grep -vE '^\s*(#|$)' "${CONSUMER_CONFIG_DIR}/harper.ignore-rules" | paste -sd, -
    )"
    export HARPER_IGNORE_RULES
  fi
}

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

ci_reviewdog_filter_mode() {
  if [ "$(ci_reviewdog_reporter)" = local ]; then
    echo nofilter
  else
    echo file
  fi
}

ci_parse_github_output() {
  local out_file="$1"
  local key="$2"
  if grep -q "^${key}=" "${out_file}" 2>/dev/null; then
    grep "^${key}=" "${out_file}" | head -1 | cut -d= -f2-
    return 0
  fi
  if grep -q "^${key}<<EOF" "${out_file}" 2>/dev/null; then
    awk -v k="${key}" '
      $0 ~ "^" k "<<EOF" { capture=1; next }
      capture && $0 == "EOF" { exit }
      capture { print }
    ' "${out_file}"
    return 0
  fi
  return 1
}

ci_doc_targets() {
  local out
  out="$(mktemp)"
  export GITHUB_OUTPUT="${out}"
  export GITHUB_EVENT_NAME="${GITHUB_EVENT_NAME:-push}"
  export GITHUB_EVENT_PULL_REQUEST_BASE_SHA="${GITHUB_EVENT_PULL_REQUEST_BASE_SHA:-origin/main}"
  export GITHUB_EVENT_PULL_REQUEST_HEAD_SHA="${GITHUB_EVENT_PULL_REQUEST_HEAD_SHA:-HEAD}"

  bash "${AUTOMATION_DIR}/bin/doc-targets.sh"

  CI_DOC_SKIP="$(ci_parse_github_output "${out}" skip || echo false)"
  CI_DOC_SCAN_MODE="$(ci_parse_github_output "${out}" scan_mode || echo all)"
  mapfile -t CI_DOC_PATHS < <(ci_parse_github_output "${out}" paths || true)
  rm -f "${out}"
  export CI_DOC_SKIP CI_DOC_SCAN_MODE CI_DOC_PATHS
}

ci_prepare_harper() {
  mkdir -p "${HOME}/.config/harper-ls" "${HOME}/.local/share/harper-ls/file_dictionaries"
  touch "${HOME}/.config/harper-ls/dictionary.txt"
}

ci_setup_lint_job() {
  ci_load_manifest
  export PATH="${DOC_LINT_INSTALL_DIR:-/tmp}:${PATH}"
  if [ "${CI_E2E_SKIP_SYNC:-false}" != true ]; then
    bash "${AUTOMATION_DIR}/bin/sync-allowlists.sh"
  else
    echo "Skipping allowlist sync (CI_E2E_SKIP_SYNC=true)"
  fi
  ci_prepare_harper
  bash "${AUTOMATION_DIR}/install/doc-linters.sh"
  bash "${AUTOMATION_DIR}/bin/vale-sync.sh"
  if command -v uv >/dev/null 2>&1; then
    uv tool install prek 2>/dev/null || true
  fi
}

ci_parallel_lint() {
  local -a paths=("$@")
  if [ "${#paths[@]}" -eq 0 ]; then
    echo "ci_parallel_lint: no paths" >&2
    return 1
  fi

  DOC_PATHS="$(printf '%s\n' "${paths[@]}")"
  export DOC_PATHS REPO_ROOT

  bash "${AUTOMATION_DIR}/bin/run-parallel-prose-lint.sh" "${CI_LINT_LOG_DIR}"
}

# Apply CLI autofix for doc tools that support it (local docs-dev check --fix).
ci_apply_doc_autofix() {
  local -a paths=("$@")
  if [ "${#paths[@]}" -eq 0 ]; then
    return 0
  fi

  echo "==> autofix (typos, rumdl)"
  echo "  typos --write-changes"
  set +e
  typos --write-changes "${paths[@]}" >"${CI_LINT_LOG_DIR}/typos-fix.log" 2>&1
  local typos_ec=$?
  set -e
  if [ -s "${CI_LINT_LOG_DIR}/typos-fix.log" ]; then
    tail -5 "${CI_LINT_LOG_DIR}/typos-fix.log" | sed 's/^/    /'
  fi
  if [ "${typos_ec}" -ne 0 ]; then
    echo "    typos: some issues need manual correction (ambiguous or blocked typos)"
  fi

  echo "  rumdl check --fix"
  set +e
  rumdl check --fix "${paths[@]}" >"${CI_LINT_LOG_DIR}/rumdl-fix.log" 2>&1
  local rumdl_ec=$?
  set -e
  if [ -s "${CI_LINT_LOG_DIR}/rumdl-fix.log" ]; then
    tail -8 "${CI_LINT_LOG_DIR}/rumdl-fix.log" | sed 's/^/    /'
  fi
  if [ "${rumdl_ec}" -ne 0 ]; then
    echo "    rumdl: unfixable markdown issues remain (see log above)"
  fi

  echo "  not autofixed: vale, harper, languagetool (report-only), lychee, metadata, actionlint"
}

ci_lint_tools_failed() {
  local tool
  for tool in vale typos rumdl harper languagetool; do
    if [ -f "${CI_LINT_LOG_DIR}/${tool}.exit" ] && [ "$(cat "${CI_LINT_LOG_DIR}/${tool}.exit")" -ne 0 ]; then
      return 0
    fi
  done
  return 1
}

ci_verify_metadata() {
  local -a paths=("$@")
  if [ "${CI_DOC_SCAN_MODE}" = all ] && [ "${#paths[@]}" -gt 0 ]; then
    mapfile -t paths < <(find docs -type f -name '*.md' | sort)
  fi
  set +e
  uv_run_tool "${DOCS_QUALITY_DIR}/tools/verify-metadata" \
    python verify_metadata.py --rdjsonl "${paths[@]}" \
    >"${CI_LINT_LOG_DIR}/metadata.rdjsonl" 2>"${CI_LINT_LOG_DIR}/metadata.stderr"
  echo "$?" >"${CI_LINT_LOG_DIR}/metadata.exit"
  set -e
  bash "${AUTOMATION_DIR}/bin/record-lint-exits.sh" "${CI_LINT_LOG_DIR}"
}

ci_report_reviewdog() {
  local reporter fail_level filter_mode
  reporter="$(ci_reviewdog_reporter)"
  fail_level="$(ci_reviewdog_fail_level)"
  filter_mode="$(ci_reviewdog_filter_mode)"

  for tool in vale typos rumdl harper languagetool; do
    log="${CI_LINT_LOG_DIR}/${tool}.json"
    if [ ! -s "${log}" ]; then
      continue
    fi
    bash "${AUTOMATION_DIR}/bin/prose-to-rdjsonl.sh" "${tool}" "${CI_LINT_LOG_DIR}" |
      reviewdog -f=rdjsonl -name="${tool}" \
        -reporter="${reporter}" -fail-level="${fail_level}" -filter-mode="${filter_mode}" || true
  done

  if [ -s "${CI_LINT_LOG_DIR}/metadata.rdjsonl" ]; then
    reviewdog -f=rdjsonl -name=metadata \
      -reporter="${reporter}" -fail-level="${fail_level}" -filter-mode="${filter_mode}" \
      <"${CI_LINT_LOG_DIR}/metadata.rdjsonl" || true
  fi
}

ci_fail_content_linters() {
  bash "${AUTOMATION_DIR}/bin/report-lint-failures.sh" "${CI_LINT_LOG_DIR}"
}

ci_prek() {
  set +e
  prek run --all-files --show-diff-on-failure 2>&1 | tee "${CI_LINT_LOG_DIR}/prek.log"
  echo "${PIPESTATUS[0]}" >"${CI_LINT_LOG_DIR}/prek.exit"
  set -e
}

ci_report_prek() {
  bash "${AUTOMATION_DIR}/bin/report-prek-reviewdog.sh" "$(ci_reviewdog_reporter)"
}

ci_fail_prek() {
  if [ -f "${CI_LINT_LOG_DIR}/prek.exit" ] && [ "$(cat "${CI_LINT_LOG_DIR}/prek.exit")" -ne 0 ]; then
    cat "${CI_LINT_LOG_DIR}/prek.log" 2>/dev/null || true
    return 1
  fi
  return 0
}

ci_actionlint_job() {
  ci_load_manifest
  export PATH="${DOC_LINT_INSTALL_DIR:-/tmp}:${PATH}"
  bash "${AUTOMATION_DIR}/install/shell-linters.sh"
  mkdir -p "${CI_LINT_LOG_DIR}"

  mapfile -t scripts < <(find .github -type f -name '*.sh' | sort)
  if [ "${#scripts[@]}" -eq 0 ]; then
    echo 0 >"${CI_LINT_LOG_DIR}/shellcheck.exit"
    return 0
  fi

  local shellcheck_rc="${DOCS_QUALITY_DIR}/config/shellcheckrc"
  local -a shellcheck_args=(-f checkstyle -x)
  if [ -f "${shellcheck_rc}" ]; then
    shellcheck_args+=(--rcfile="${shellcheck_rc}")
  fi

  set +e
  shellcheck "${shellcheck_args[@]}" "${scripts[@]}" >"${CI_LINT_LOG_DIR}/shellcheck.txt" 2>"${CI_LINT_LOG_DIR}/shellcheck.stderr"
  echo "$?" >"${CI_LINT_LOG_DIR}/shellcheck.exit"
  set -e

  local reporter fail_level filter_mode
  reporter="$(ci_reviewdog_reporter)"
  fail_level="$(ci_reviewdog_fail_level)"
  filter_mode="$(ci_reviewdog_filter_mode)"
  if [ -s "${CI_LINT_LOG_DIR}/shellcheck.txt" ]; then
    # shellcheck source=reviewdog-shellcheck.sh
    source "${AUTOMATION_DIR}/lib/reviewdog-shellcheck.sh"
    reviewdog_shellcheck_checkstyle "${CI_LINT_LOG_DIR}/shellcheck.txt" shellcheck \
      -reporter="${reporter}" -fail-level="${fail_level}" -filter-mode="${filter_mode}"
  fi

  shfmt -d -ln bash -i 2 -ci "${scripts[@]}"
  echo $? >"${CI_LINT_LOG_DIR}/shfmt.exit"

  if command -v actionlint >/dev/null 2>&1; then
    set +e
    actionlint .github/workflows/*.yml >"${CI_LINT_LOG_DIR}/actionlint.txt" 2>"${CI_LINT_LOG_DIR}/actionlint.stderr"
    echo "$?" >"${CI_LINT_LOG_DIR}/actionlint.exit"
    set -e
    if [ -s "${CI_LINT_LOG_DIR}/actionlint.txt" ]; then
      reviewdog -f=actionlint -name=actionlint \
        -reporter="${reporter}" -fail-level="${fail_level}" -filter-mode="${filter_mode}" \
        <"${CI_LINT_LOG_DIR}/actionlint.txt" || true
    fi
  else
    echo 0 >"${CI_LINT_LOG_DIR}/actionlint.exit"
  fi
}

ci_fail_actionlint() {
  local fail=0
  if [ -f "${CI_LINT_LOG_DIR}/shellcheck.exit" ] && [ "$(cat "${CI_LINT_LOG_DIR}/shellcheck.exit")" -ne 0 ]; then
    cat "${CI_LINT_LOG_DIR}/shellcheck.stderr" 2>/dev/null || true
    fail=1
  fi
  if [ -f "${CI_LINT_LOG_DIR}/shfmt.exit" ] && [ "$(cat "${CI_LINT_LOG_DIR}/shfmt.exit")" -ne 0 ]; then
    fail=1
  fi
  if [ -f "${CI_LINT_LOG_DIR}/actionlint.exit" ] && [ "$(cat "${CI_LINT_LOG_DIR}/actionlint.exit")" -ne 0 ]; then
    cat "${CI_LINT_LOG_DIR}/actionlint.stderr" 2>/dev/null || true
    fail=1
  fi
  return "${fail}"
}
