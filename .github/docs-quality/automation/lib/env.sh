#!/usr/bin/env bash
# Shared docs-quality paths and manifest (source from automation/* scripts).
set -euo pipefail

_docs_quality_repo_root() {
  if [ -n "${REPO_ROOT:-}" ]; then
    echo "${REPO_ROOT}"
    return
  fi
  cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd
}

# Defined before the load guard so re-source (e.g. sync-allowlists after ci-steps) still works.
uv_run_tool() {
  local project_dir="$1"
  local root
  shift
  root="$(_docs_quality_repo_root)"
  (
    unset VIRTUAL_ENV
    cd "${root}"
    uv run --directory "${project_dir}" "$@"
  )
}

if [ -n "${DOCS_QUALITY_ENV_LOADED:-}" ]; then
  if [ "${BASH_SOURCE[0]}" != "${0}" ]; then
    return 0
  fi
  exit 0
fi
export DOCS_QUALITY_ENV_LOADED=1

REPO_ROOT="${REPO_ROOT:-$(_docs_quality_repo_root)}"

if [ -n "${DOCS_QUALITY_DIR:-}" ]; then
  DOCS_QUALITY_DIR="$(cd "${DOCS_QUALITY_DIR}" && pwd)"
elif [ -d "${REPO_ROOT}/.github/pwnpatterns-ci/.github/docs-quality" ]; then
  DOCS_QUALITY_DIR="$(cd "${REPO_ROOT}/.github/pwnpatterns-ci/.github/docs-quality" && pwd)"
else
  DOCS_QUALITY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
fi

AUTOMATION_DIR="${DOCS_QUALITY_DIR}/automation"
MANIFEST="${DOCS_QUALITY_DIR}/config/manifest.env"

# Consumer-specific config (allowlists, repo.yml, harper.ignore-rules) stays on the pattern repo.
CONSUMER_CONFIG_DIR="${REPO_ROOT}/.github/docs-quality/config"
if [ ! -d "${CONSUMER_CONFIG_DIR}" ]; then
  CONSUMER_CONFIG_DIR="${DOCS_QUALITY_DIR}/config"
fi
export CONSUMER_CONFIG_DIR

if [ ! -f "${MANIFEST}" ]; then
  echo "Missing ${MANIFEST}" >&2
  exit 1
fi

_saved_install_dir="${DOC_LINT_INSTALL_DIR:-}"
set -a
# shellcheck source=/dev/null
source "${MANIFEST}"
set +a
if [ -n "${_saved_install_dir}" ]; then
  export DOC_LINT_INSTALL_DIR="${_saved_install_dir}"
fi

export AUTOMATION_DIR DOCS_QUALITY_DIR REPO_ROOT MANIFEST

_harper_ignore="${REPO_ROOT}/${HARPER_IGNORE_RULES_FILE}"
if [ -f "${CONSUMER_CONFIG_DIR}/harper.ignore-rules" ]; then
  _harper_ignore="${CONSUMER_CONFIG_DIR}/harper.ignore-rules"
fi
if [ -f "${_harper_ignore}" ]; then
  HARPER_IGNORE_RULES="$(
    grep -vE '^\s*(#|$)' "${_harper_ignore}" | paste -sd, -
  )"
  export HARPER_IGNORE_RULES
fi

export HARPER_USER_DICT="${REPO_ROOT}/${HARPER_USER_DICT}"
