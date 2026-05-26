#!/usr/bin/env bash
# Run an automation script from the materialized platform checkout.
# Usage (from pattern repo root, after ensure-platform):
#   .github/pwnpatterns-ci/scripts/run-with-platform.sh .github/docs-quality/automation/bin/sync-allowlists.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLATFORM_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_ROOT="${REPO_ROOT:-$(cd "${PLATFORM_ROOT}/../.." && pwd)}"
REL="${1:?path under platform root (e.g. .github/docs-quality/automation/bin/sync-allowlists.sh)}"
shift

export REPO_ROOT
# shellcheck source=ensure-platform.sh
source "${REPO_ROOT}/scripts/ensure-platform.sh"

TARGET="${PLATFORM_ROOT}/${REL}"
if [ ! -f "${TARGET}" ]; then
  echo "run-with-platform: not found: ${TARGET}" >&2
  echo "Run scripts/ensure-platform.sh or check .github/platform.ref" >&2
  exit 1
fi

exec bash "${TARGET}" "$@"
