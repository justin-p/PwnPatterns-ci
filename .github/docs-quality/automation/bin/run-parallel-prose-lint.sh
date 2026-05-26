#!/usr/bin/env bash
# Run vale, typos, rumdl, and grammar tools (Harper / LanguageTool) on DOC_PATHS.
# Grammar routing: config/language-tools.yml + route-grammar-paths.sh
# Usage: DOC_PATHS=<multiline> HARPER_USER_DICT=... HARPER_IGNORE_RULES=... \
#   bash run-parallel-prose-lint.sh [lint-logs-dir]
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)}"
LOG_DIR="${1:-lint-logs}"
AUTOMATION_DIR="${REPO_ROOT}/.github/docs-quality/automation"

mapfile -t paths < <(bash "${AUTOMATION_DIR}/bin/load-doc-paths.sh")

grammar_smoke=".github/tests/fixtures/nl-languagetool-smoke.md"
if [ -f "${REPO_ROOT}/${grammar_smoke}" ]; then
  if [ "${#paths[@]}" -eq 0 ] || ! printf '%s\n' "${paths[@]}" | grep -qxF "${grammar_smoke}"; then
    paths+=("${grammar_smoke}")
  fi
fi

if [ "${#paths[@]}" -eq 0 ]; then
  echo "run-parallel-prose-lint: no documentation paths to lint" >&2
  exit 1
fi

mkdir -p "${LOG_DIR}"
export CI_LINT_LOG_DIR="${LOG_DIR}"
printf '%s\n' "${paths[@]}" >"${LOG_DIR}/lint-paths.lst"
bash "${AUTOMATION_DIR}/bin/build-path-index.sh" "${LOG_DIR}"
bash "${AUTOMATION_DIR}/bin/route-grammar-paths.sh" "${LOG_DIR}"

mapfile -t harper_paths < <(
  if [ -s "${LOG_DIR}/grammar-harper-paths.lst" ]; then
    cat "${LOG_DIR}/grammar-harper-paths.lst"
  fi
)

echo "Linting ${#paths[@]} documentation file(s) (harper: ${#harper_paths[@]}, languagetool: $(grep -c . "${LOG_DIR}/grammar-languagetool.tsv" 2>/dev/null || echo 0))"

export PATH="${DOC_LINT_INSTALL_DIR:-/tmp}:${PATH}"

(
  echo "==> vale"
  set +e
  vale --output=JSON "${paths[@]}" >"${LOG_DIR}/vale.json" 2>"${LOG_DIR}/vale.stderr"
  set -e
) &
(
  echo "==> typos"
  set +e
  typos --format json "${paths[@]}" >"${LOG_DIR}/typos.json" 2>"${LOG_DIR}/typos.stderr"
  set -e
) &
(
  echo "==> rumdl"
  set +e
  rumdl check --output json "${paths[@]}" >"${LOG_DIR}/rumdl.json" 2>"${LOG_DIR}/rumdl.stderr"
  set -e
) &
(
  echo "==> harper"
  set +e
  if [ "${#harper_paths[@]}" -gt 0 ]; then
    harper-cli lint "${harper_paths[@]}" --format json \
      --user-dict-path "${HARPER_USER_DICT:?HARPER_USER_DICT not set}" \
      --ignore "${HARPER_IGNORE_RULES:-}" \
      >"${LOG_DIR}/harper.json" 2>"${LOG_DIR}/harper.stderr" || true
  else
    echo "[]" >"${LOG_DIR}/harper.json"
    : >"${LOG_DIR}/harper.stderr"
  fi
  set -e
) &
(
  echo "==> languagetool"
  set +e
  if [ -s "${LOG_DIR}/grammar-languagetool.tsv" ] && command -v java >/dev/null 2>&1; then
    # shellcheck source=../lib/env.sh
    source "${AUTOMATION_DIR}/lib/env.sh"
    if [ -z "${LANGUAGETOOL_HOME:-}" ] || [ ! -f "${LANGUAGETOOL_HOME}/languagetool-commandline.jar" ]; then
      bash "${AUTOMATION_DIR}/install/doc-linters.sh" >/dev/null 2>&1 || true
    fi
    export LANGUAGETOOL_HOME="${LANGUAGETOOL_HOME:-${DOC_LINT_INSTALL_DIR:-/tmp}/LanguageTool-${LANGUAGETOOL_VERSION:-}}"
    uv_run_tool "${DOCS_QUALITY_DIR}/tools/grammar-routing" \
      python run_languagetool_batch.py \
      --log-dir "${LOG_DIR}" \
      --repo-root "${REPO_ROOT}" \
      >"${LOG_DIR}/languagetool.stderr" 2>&1 || true
  else
    echo "[]" >"${LOG_DIR}/languagetool.json"
    : >"${LOG_DIR}/languagetool.stderr"
  fi
  set -e
) &
wait

if command -v uv >/dev/null 2>&1; then
  uv run --directory "${REPO_ROOT}/.github/docs-quality/tools/docs-dev" python \
    "${AUTOMATION_DIR}/bin/merge-template-list-vale.py" || true
fi

bash "${AUTOMATION_DIR}/bin/record-lint-exits.sh" "${LOG_DIR}"

echo "Vale exit: $(cat "${LOG_DIR}/vale.exit")"
echo "Typos exit: $(cat "${LOG_DIR}/typos.exit")"
echo "rumdl exit: $(cat "${LOG_DIR}/rumdl.exit")"
echo "Harper exit: $(cat "${LOG_DIR}/harper.exit")"
echo "LanguageTool exit: $(cat "${LOG_DIR}/languagetool.exit")"
