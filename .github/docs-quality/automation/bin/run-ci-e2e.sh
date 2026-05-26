#!/usr/bin/env bash
# Full CI parity E2E: same steps as docs-quality.yml with reviewdog local reporter.
set -euo pipefail

_AUTOMATION_BIN="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# shellcheck source=../lib/env.sh
source "${_AUTOMATION_BIN}/lib/env.sh"
export REPO_ROOT="${REPO_ROOT:-$(_docs_quality_repo_root)}"
export DOC_LINT_INSTALL_DIR="${DOC_LINT_INSTALL_DIR:-${REPO_ROOT}/.local/doc-linters}"
# shellcheck source=../lib/ci-steps.sh
source "${AUTOMATION_DIR}/lib/ci-steps.sh"

cd "${REPO_ROOT}"

job=all
smoke_docs=false
skip_lychee=false
include_dashboard=false
component_only=false

while [ $# -gt 0 ]; do
  case "$1" in
    --job)
      job="${2:?}"
      shift 2
      ;;
    --smoke-docs)
      smoke_docs=true
      shift
      ;;
    --skip-lychee)
      skip_lychee=true
      shift
      ;;
    --include-dashboard)
      include_dashboard=true
      shift
      ;;
    --component-tests-only)
      component_only=true
      shift
      ;;
    -h | --help)
      cat <<'EOF'
Usage: run-ci-e2e.sh [options]

  --job all|lint|lychee|actionlint|dashboard   Job slice (default: all)
  --smoke-docs                                  Lint first 5 docs/*.md only
  --skip-lychee                                 Skip live lychee
  --include-dashboard                           Full-tree lychee + dashboard body jq
  --component-tests-only                        Run .github/tests only and exit

E2E uses reviewdog -reporter=local. Exit codes are checked against
.github/docs-quality/config/ci-e2e-expectations.env (machinery, not content debt).

Developer helper: ./scripts/docs-dev.sh e2e [options]
EOF
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      exit 2
      ;;
  esac
done

export CI_REVIEWDOG_MODE=local
export CI_LINT_LOG_DIR="${REPO_ROOT}/lint-logs"
export CI_E2E_SKIP_SYNC="${CI_E2E_SKIP_SYNC:-true}"
export CI_E2E_SKIP_PREK="${CI_E2E_SKIP_PREK:-true}"
export PATH="${DOC_LINT_INSTALL_DIR}:${PATH}"

declare -A E2E_RESULTS=()
declare -A E2E_EXPECTED=()

load_expectations() {
  local exp="${DOCS_QUALITY_DIR}/config/ci-e2e-expectations.env"
  if [ ! -f "${exp}" ]; then
    echo "Missing ${exp}" >&2
    exit 1
  fi
  # shellcheck source=/dev/null
  source "${exp}"
  E2E_EXPECTED[vale]=${EXPECT_VALE_EXIT:-0}
  E2E_EXPECTED[typos]=${EXPECT_TYPOS_EXIT:-0}
  E2E_EXPECTED[textlint]=${EXPECT_TEXTLINT_EXIT:-0}
  E2E_EXPECTED[rumdl]=${EXPECT_RUMDL_EXIT:-0}
  E2E_EXPECTED[harper]=${EXPECT_HARPER_EXIT:-0}
  E2E_EXPECTED[metadata]=${EXPECT_METADATA_EXIT:-0}
  E2E_EXPECTED[prek]=${EXPECT_PREK_EXIT:-0}
  E2E_EXPECTED[lychee]=${EXPECT_LYCHEE_FILTER_EXIT:-0}
  E2E_EXPECTED[shellcheck]=${EXPECT_SHELLCHECK_EXIT:-0}
  E2E_EXPECTED[shfmt]=${EXPECT_SHFMT_EXIT:-0}
  E2E_EXPECTED[actionlint]=${EXPECT_ACTIONLINT_EXIT:-0}
}

record_result() {
  local name="$1"
  local actual="$2"
  E2E_RESULTS["${name}"]="${actual}"
}

check_expectation() {
  local name="$1"
  local actual="${E2E_RESULTS[${name}]:-missing}"
  local expected="${E2E_EXPECTED[${name}]:-0}"
  if [ "${actual}" = missing ]; then
    echo "  ${name}: (not run)"
    return 0
  fi
  if [ "${actual}" -eq "${expected}" ]; then
    echo "  ${name}: exit=${actual} expected=${expected} PASS"
    return 0
  fi
  echo "  ${name}: exit=${actual} expected=${expected} FAIL" >&2
  return 1
}

print_summary() {
  local fail=0
  echo ""
  echo "==> E2E summary (reviewdog=local)"
  for name in vale typos textlint rumdl harper languagetool metadata prek lychee shellcheck shfmt actionlint; do
    check_expectation "${name}" || fail=1
  done
  return "${fail}"
}

run_component_tests() {
  local script=""
  for candidate in \
    "${REPO_ROOT}/.github/pwnpatterns-ci/.github/tests/run-component-tests.sh" \
    "${REPO_ROOT}/.github/tests/run-component-tests.sh" \
    "${DOCS_QUALITY_DIR}/../tests/run-component-tests.sh"; do
    if [ -f "${candidate}" ]; then
      script="${candidate}"
      break
    fi
  done
  if [ -z "${script}" ]; then
    echo "run-ci-e2e: missing run-component-tests.sh (run scripts/ensure-platform.sh)" >&2
    exit 1
  fi
  bash "${script}"
}

run_lint_job() {
  local -a paths=()

  if [ "${smoke_docs}" = true ]; then
    echo "CI_E2E smoke-docs: linting first 5 docs/*.md"
    mapfile -t paths < <(find "${REPO_ROOT}/docs" -type f -name '*.md' 2>/dev/null | sort | head -5)
  else
    ci_doc_targets
    if [ "${CI_DOC_SKIP}" = true ] && [ "${CI_E2E_FULL_LINT:-false}" = true ]; then
      echo "CI_E2E_FULL_LINT: linting all docs/*.md (doc-targets skip ignored for machinery E2E)"
      mapfile -t paths < <(find "${REPO_ROOT}/docs" -type f -name '*.md' 2>/dev/null | sort)
      CI_DOC_SKIP=false
    fi
    if [ "${CI_DOC_SKIP}" = true ]; then
      echo "No documentation targets; skipping lint job."
      return 0
    fi
    paths=("${CI_DOC_PATHS[@]}")
  fi

  if [ "${#paths[@]}" -eq 0 ]; then
    echo "No paths to lint." >&2
    return 1
  fi

  ci_setup_lint_job
  bash "${AUTOMATION_DIR}/install/reviewdog.sh"
  export PATH="${DOC_LINT_INSTALL_DIR}:${PATH}"

  ci_parallel_lint "${paths[@]}"
  record_result vale "$(cat "${CI_LINT_LOG_DIR}/vale.exit")"
  record_result typos "$(cat "${CI_LINT_LOG_DIR}/typos.exit")"
  record_result textlint "$(cat "${CI_LINT_LOG_DIR}/textlint.exit")"
  record_result rumdl "$(cat "${CI_LINT_LOG_DIR}/rumdl.exit")"
  record_result harper "$(cat "${CI_LINT_LOG_DIR}/harper.exit")"
  record_result languagetool "$(cat "${CI_LINT_LOG_DIR}/languagetool.exit")"

  ci_report_reviewdog

  ci_verify_metadata "${paths[@]}"
  record_result metadata "$(cat "${CI_LINT_LOG_DIR}/metadata.exit")"
  ci_report_reviewdog

  if [ "${CI_E2E_SKIP_PREK}" = true ]; then
    echo "Skipping prek (CI_E2E_SKIP_PREK=true)"
    echo 0 >"${CI_LINT_LOG_DIR}/prek.exit"
  else
    ci_prek
    ci_report_prek
  fi
  record_result prek "$(cat "${CI_LINT_LOG_DIR}/prek.exit")"
}

run_lychee_job() {
  if [ "${skip_lychee}" = true ]; then
    echo "Skipping lychee (--skip-lychee)"
    return 0
  fi
  bash "${AUTOMATION_DIR}/install/reviewdog.sh"
  export PATH="${DOC_LINT_INSTALL_DIR}:${PATH}"

  local -a lychee_paths=()
  if [ "${smoke_docs}" = true ]; then
    mapfile -t lychee_paths < <(find docs -type f -name '*.md' | sort | head -3)
  else
    lychee_paths=('./docs/**/*.md')
  fi

  set +e
  ci_lychee_pr "${lychee_paths[@]}"
  local ec=$?
  set -e
  if [ -f "${CI_LINT_LOG_DIR}/lychee-filter.exit" ]; then
    record_result lychee "$(cat "${CI_LINT_LOG_DIR}/lychee-filter.exit")"
  else
    record_result lychee "${ec}"
  fi
}

run_actionlint_job() {
  bash "${AUTOMATION_DIR}/install/reviewdog.sh"
  export PATH="${DOC_LINT_INSTALL_DIR}:${PATH}"
  set +e
  ci_actionlint_job
  local ec=$?
  set -e
  record_result shellcheck "$(cat "${CI_LINT_LOG_DIR}/shellcheck.exit" 2>/dev/null || echo 0)"
  record_result shfmt "$(cat "${CI_LINT_LOG_DIR}/shfmt.exit" 2>/dev/null || echo 0)"
  record_result actionlint "$(cat "${CI_LINT_LOG_DIR}/actionlint.exit" 2>/dev/null || echo 0)"
}

run_dashboard_job() {
  bash "${AUTOMATION_DIR}/install/reviewdog.sh"
  export PATH="${DOC_LINT_INSTALL_DIR}:${PATH}"
  ci_lychee_dashboard
}

load_expectations
mkdir -p "${CI_LINT_LOG_DIR}"

echo "==> component tests"
run_component_tests

if [ "${component_only}" = true ]; then
  exit 0
fi

case "${job}" in
  all)
    set +e
    run_lint_job
    run_lychee_job
    run_actionlint_job
    [ "${include_dashboard}" = true ] && run_dashboard_job || true
    set -e
    ;;
  lint)
    run_lint_job
    ;;
  lychee)
    run_lychee_job
    ;;
  actionlint)
    run_actionlint_job
    ;;
  dashboard)
    run_dashboard_job
    ;;
  *)
    echo "Unknown job: ${job}" >&2
    exit 2
    ;;
esac

if ! print_summary; then
  exit 1
fi
echo "CI E2E machinery checks passed."
