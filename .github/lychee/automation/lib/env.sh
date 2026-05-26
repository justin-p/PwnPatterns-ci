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
REPO_ROOT="$(cd "${LYCHEE_DIR}/../.." && pwd)"

export AUTOMATION_DIR LYCHEE_DIR REPO_ROOT
export LYCHEE_CI_403_HOSTS="${LYCHEE_DIR}/config/ci-403-hosts.txt"
export LYCHEE_DASHBOARD_ENV="${LYCHEE_DIR}/config/link-check-dashboard-issue.env"
export LYCHEE_FILTER_403_JQ="${AUTOMATION_DIR}/filters/filter-datacenter-403.jq"
export LYCHEE_TO_RDJSONL_JQ="${AUTOMATION_DIR}/filters/to-rdjsonl.jq"
export LYCHEE_DASHBOARD_BODY_JQ="${AUTOMATION_DIR}/filters/dashboard-issue-body.jq"
