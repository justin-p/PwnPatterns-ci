#!/usr/bin/env bash
# Source dashboard issue env and export issue_number/issue_title to GITHUB_ENV.
set -euo pipefail

# shellcheck source=../lib/env.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/lib/env.sh"

if [ ! -f "${LYCHEE_DASHBOARD_ENV}" ]; then
  echo "Missing ${LYCHEE_DASHBOARD_ENV}" >&2
  exit 1
fi

set -a
# shellcheck source=/dev/null
source "${LYCHEE_DASHBOARD_ENV}"
set +a

if [ -n "${GITHUB_ENV:-}" ]; then
  echo "issue_number=${LINK_CHECK_DASHBOARD_ISSUE_NUMBER}" >>"${GITHUB_ENV}"
  echo "issue_title=${LINK_CHECK_DASHBOARD_ISSUE_TITLE}" >>"${GITHUB_ENV}"
fi
