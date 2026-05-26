#!/usr/bin/env bash
# Vendored into pattern repos as scripts/ensure-platform.sh (copy from PwnPatterns-ci when bumping platform.ref).
# Bootstrap: clone platform if missing, then delegate to .github/pwnpatterns-ci/scripts/ensure-platform.sh.
set -euo pipefail

export REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="${REPO_ROOT}/.github/pwnpatterns-ci"
REF_FILE="${REPO_ROOT}/.github/platform.ref"
REPO="${PWNPATTERNS_CI_REPO:-ocd-nl/PwnPatterns-ci}"
PLATFORM_ENSURE="${DEST}/scripts/ensure-platform.sh"

read_ref() {
  if [ ! -f "${REF_FILE}" ]; then
    echo "ensure-platform: missing ${REF_FILE}" >&2
    return 1
  fi
  tr -d '[:space:]' <"${REF_FILE}" | head -1
}

REF="$(read_ref || true)"
if [ -z "${REF}" ]; then
  echo "ensure-platform: invalid platform.ref" >&2
  exit 1
fi

if [ -f "${PLATFORM_ENSURE}" ]; then
  CURRENT="$(git -C "${DEST}" rev-parse HEAD 2>/dev/null || echo "")"
  if [ "${CURRENT}" = "${REF}" ]; then
    env REPO_ROOT="${REPO_ROOT}" bash "${PLATFORM_ENSURE}"
    exit $?
  fi
fi

if ! command -v git >/dev/null 2>&1; then
  echo "ensure-platform: git is required" >&2
  exit 1
fi

TMP="$(mktemp -d)"
trap 'rm -rf "${TMP}"' EXIT

if ! git clone --depth 1 "https://github.com/${REPO}.git" "${TMP}/repo" 2>/dev/null; then
  echo "ensure-platform: failed to clone https://github.com/${REPO}.git" >&2
  echo "Platform CI is maintained in PwnPatterns-ci only. Fix network/auth or update .github/platform.ref." >&2
  exit 1
fi

git -C "${TMP}/repo" fetch --depth 1 origin "${REF}" 2>/dev/null || true
if ! git -C "${TMP}/repo" checkout "${REF}" 2>/dev/null; then
  echo "ensure-platform: could not checkout ${REF} on ${REPO}" >&2
  exit 1
fi

rm -rf "${DEST}"
mkdir -p "$(dirname "${DEST}")"
cp -a "${TMP}/repo/." "${DEST}/"
trap - EXIT
rm -rf "${TMP}"

echo "ensure-platform: ${REPO} @ ${REF} -> ${DEST}"
env REPO_ROOT="${REPO_ROOT}" bash "${DEST}/scripts/ensure-platform.sh"
