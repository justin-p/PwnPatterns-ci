#!/usr/bin/env bash
# Shared lychee paths (source from automation/* scripts and workflows).
set -euo pipefail

if [ -n "${LYCHEE_ENV_LOADED:-}" ]; then
  if [ "${BASH_SOURCE[0]}" != "${0}" ]; then
    return 0
  fi
  exit 0
fi
export LYCHEE_ENV_LOADED=1

AUTOMATION_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LYCHEE_DIR="$(cd "${AUTOMATION_DIR}/.." && pwd)"
if [ -z "${REPO_ROOT:-}" ]; then
  REPO_ROOT="$(cd "${LYCHEE_DIR}/../.." && pwd)"
fi

export AUTOMATION_DIR LYCHEE_DIR REPO_ROOT

_resolve_lychee_config_file() {
  local name="$1"
  for dir in \
    "${REPO_ROOT}/.github/lychee/config" \
    "${LYCHEE_DIR}/config"; do
    if [ -f "${dir}/${name}" ]; then
      echo "${dir}/${name}"
      return 0
    fi
  done
  echo "lychee: missing ${name} (expected under ${REPO_ROOT}/.github/lychee/config/)" >&2
  return 1
}

_resolve_lychee_jq_lib() {
  for dir in \
    "${AUTOMATION_DIR}/filters/lib" \
    "${REPO_ROOT}/.github/pwnpatterns-ci/.github/lychee/automation/filters/lib" \
    "${REPO_ROOT}/.github/lychee/automation/filters/lib" \
    "${REPO_ROOT}/.github/pwnpatterns-ci/.github/docs-quality/automation/filters/lib" \
    "${REPO_ROOT}/.github/docs-quality/automation/filters/lib"; do
    if [ -f "${dir}/lychee-message.jq" ]; then
      echo "${dir}"
      return 0
    fi
  done
  echo "lychee: missing docs-quality automation/filters/lib/lychee-message.jq" >&2
  return 1
}

LYCHEE_CI_403_HOSTS="$(_resolve_lychee_config_file ci-403-hosts.txt)"
LYCHEE_JQ_LIB="$(_resolve_lychee_jq_lib)"
if LYCHEE_DASHBOARD_ENV="$(_resolve_lychee_config_file link-check-dashboard-issue.env)"; then
  :
else
  LYCHEE_DASHBOARD_ENV="${LYCHEE_DIR}/config/link-check-dashboard-issue.env"
fi
export LYCHEE_CI_403_HOSTS LYCHEE_JQ_LIB LYCHEE_DASHBOARD_ENV
export LYCHEE_FILTER_403_JQ="${AUTOMATION_DIR}/filters/filter-datacenter-403.jq"
export LYCHEE_TO_RDJSONL_JQ="${AUTOMATION_DIR}/filters/to-rdjsonl.jq"
export LYCHEE_DASHBOARD_BODY_JQ="${AUTOMATION_DIR}/filters/dashboard-issue-body.jq"
