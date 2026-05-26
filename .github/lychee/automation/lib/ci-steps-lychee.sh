#!/usr/bin/env bash
# Shared lychee CI steps (source from ci-steps.sh / run-ci-e2e.sh; do not execute).
set -euo pipefail

if [ -n "${CI_STEPS_LYCHEE_LOADED:-}" ]; then
  return 0
fi
export CI_STEPS_LYCHEE_LOADED=1

# shellcheck source=env.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/env.sh"

LYCHEE_VERSION="${LYCHEE_VERSION:-0.24.2}"
LYCHEE_INSTALL_DIR="${LYCHEE_INSTALL_DIR:-${DOC_LINT_INSTALL_DIR:-/tmp}}"

_lychee_runnable() {
  local bin="$1"
  [ -n "${bin}" ] && [ -x "${bin}" ] && "${bin}" --version >/dev/null 2>&1
}

_lychee_version_matches_pin() {
  local bin="$1"
  local got
  got="$("${bin}" --version 2>/dev/null | head -1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)" || return 1
  [ "${got}" = "${LYCHEE_VERSION}" ]
}

lychee_install_cli() {
  mkdir -p "${LYCHEE_INSTALL_DIR}"
  export PATH="${LYCHEE_INSTALL_DIR}:${PATH}"
  if _lychee_runnable "${LYCHEE_INSTALL_DIR}/lychee" &&
    _lychee_version_matches_pin "${LYCHEE_INSTALL_DIR}/lychee"; then
    return 0
  fi
  if command -v lychee >/dev/null 2>&1; then
    local system_lychee
    system_lychee="$(command -v lychee)"
    if _lychee_runnable "${system_lychee}" && _lychee_version_matches_pin "${system_lychee}"; then
      return 0
    fi
  fi
  : "${LYCHEE_VERSION:?LYCHEE_VERSION is required}"
  : "${LYCHEE_LINUX_AMD64_SHA256:?LYCHEE_LINUX_AMD64_SHA256 is required}"
  local asset="${LYCHEE_LINUX_AMD64_ASSET:-lychee-x86_64-unknown-linux-musl.tar.gz}"
  local url="https://github.com/lycheeverse/lychee/releases/download/lychee-v${LYCHEE_VERSION}/${asset}"
  local tmp archive
  tmp="$(mktemp -d)"
  archive="${tmp}/${asset}"
  curl -fsSL -o "${archive}" "${url}"
  echo "${LYCHEE_LINUX_AMD64_SHA256}  ${asset}" | (cd "${tmp}" && sha256sum -c -)
  tar -xzf "${archive}" -C "${tmp}"
  local bin
  bin="$(find "${tmp}" -maxdepth 2 -type f -name lychee | head -1)"
  if [ -z "${bin}" ]; then
    echo "lychee binary not found in ${archive}" >&2
    return 1
  fi
  install -m 0755 "${bin}" "${LYCHEE_INSTALL_DIR}/lychee"
  rm -rf "${tmp}"
  export PATH="${LYCHEE_INSTALL_DIR}:${PATH}"
  if ! _lychee_runnable "${LYCHEE_INSTALL_DIR}/lychee"; then
    echo "lychee: installed binary is not runnable on this host (check glibc)" >&2
    return 1
  fi
}

ci_lychee_hosts_json() {
  grep -vE '^\s*(#|$)' "${LYCHEE_CI_403_HOSTS}" | jq -Rsc 'split("\n") | map(select(length > 0))'
}

ci_lychee_filter_403() {
  local report="${1:-lychee/report.json}"
  local hosts_json tmp
  hosts_json="$(ci_lychee_hosts_json)"
  tmp="$(mktemp)"
  jq -f "${LYCHEE_FILTER_403_JQ}" --slurpfile hosts <(echo "${hosts_json}") \
    "${report}" >"${tmp}"
  mv "${tmp}" "${report}"
  local errors suppressed
  errors="$(jq '.errors // 0' "${report}")"
  suppressed="$(jq '.datacenter_403_suppressed // 0' "${report}")"
  echo "Filtered datacenter 403: suppressed=${suppressed}, remaining errors=${errors}" >&2
  if [ "${errors}" -eq 0 ]; then
    return 0
  fi
  return 1
}

ci_lychee_report_reviewdog() {
  local report="${1:-lychee/report.json}"
  if [ ! -f "${report}" ]; then
    echo "lychee report not found at ${report}" >&2
    return 1
  fi
  local reporter fail_level filter_mode
  if type -t ci_reviewdog_reporter >/dev/null 2>&1; then
    reporter="$(ci_reviewdog_reporter)"
    fail_level="$(ci_reviewdog_fail_level)"
    filter_mode="$(ci_reviewdog_filter_mode)"
  else
    reporter=local
    fail_level=none
    filter_mode=nofilter
  fi
  jq -r -L "${LYCHEE_JQ_LIB}" \
    -f "${LYCHEE_TO_RDJSONL_JQ}" "${report}" |
    reviewdog -f=rdjsonl -name=lychee \
      -reporter="${reporter}" -fail-level="${fail_level}" -filter-mode="${filter_mode}" ||
    true
}

ci_lychee_offline() {
  local -a paths=("$@")
  local report="${LYCHEE_OFFLINE_REPORT:-lychee/report-offline.json}"

  if [ "${#paths[@]}" -eq 0 ]; then
    echo "lychee offline: no paths" >&2
    return 0
  fi

  lychee_install_cli
  mkdir -p "$(dirname "${report}")"
  set +e
  lychee --config .lychee.toml --offline --no-progress --format json \
    --output "${report}" "${paths[@]}"
  local lychee_exit=$?
  set -e
  echo "${lychee_exit}" >"${CI_LINT_LOG_DIR:-lint-logs}/lychee.exit" 2>/dev/null || true

  if [ ! -f "${report}" ]; then
    echo "lychee offline: no report at ${report} (exit ${lychee_exit})" >&2
    return 1
  fi
  return "${lychee_exit}"
}

ci_lychee_pr() {
  local -a paths=("$@")
  if [ "${#paths[@]}" -eq 0 ]; then
    mapfile -t paths < <(find docs -type f -name '*.md' | sort)
  fi

  lychee_install_cli
  mkdir -p lychee
  set +e
  lychee --config .lychee.toml --max-cache-age 1d --format json \
    --output lychee/report.json --no-progress "${paths[@]}"
  local lychee_exit=$?
  echo "${lychee_exit}" >"${CI_LINT_LOG_DIR:-lint-logs}/lychee.exit" 2>/dev/null || true

  if [ ! -f lychee/report.json ]; then
    echo "lychee did not produce lychee/report.json" >&2
    return 1
  fi

  local filter_exit=0
  ci_lychee_filter_403 lychee/report.json || filter_exit=$?
  echo "${filter_exit}" >"${CI_LINT_LOG_DIR:-lint-logs}/lychee-filter.exit" 2>/dev/null || true

  ci_lychee_report_reviewdog lychee/report.json || true
  return "${filter_exit}"
}

ci_lychee_dashboard() {
  lychee_install_cli
  mkdir -p lychee
  set +e
  lychee --config .lychee.toml --max-cache-age 1d --format json \
    --output lychee/report.json --no-progress './docs/**/*.md'
  set -e

  if [ ! -f lychee/report.json ]; then
    echo "lychee dashboard: report missing" >&2
    return 1
  fi

  ci_lychee_filter_403 lychee/report.json >/dev/null

  local body_file="${REPO_ROOT}/lint-logs/dashboard-body.md"
  mkdir -p "$(dirname "${body_file}")"
  jq -r -f "${LYCHEE_DASHBOARD_BODY_JQ}" lychee/report.json >"${body_file}"

  if [ ! -s "${body_file}" ]; then
    echo "dashboard body empty" >&2
    return 1
  fi

  if [ -n "${GH_TOKEN:-}" ] && command -v gh >/dev/null 2>&1; then
    # shellcheck source=/dev/null
    source "${LYCHEE_DASHBOARD_ENV}" 2>/dev/null || true
    if [ -n "${DASHBOARD_ISSUE_NUMBER:-}" ]; then
      gh issue edit "${DASHBOARD_ISSUE_NUMBER}" --body-file "${body_file}" || true
    fi
  fi
  echo "Dashboard body written to ${body_file}"
  return 0
}
