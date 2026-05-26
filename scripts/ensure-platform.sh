#!/usr/bin/env bash
# Materialize ocd-nl/PwnPatterns-ci at REPO_ROOT/.github/pwnpatterns-ci/ (see REPO_ROOT/.github/platform.ref).
# Run from a pattern repo (REPO_ROOT set) or after consumer bootstrap delegates here.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLATFORM_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

if [ -n "${REPO_ROOT:-}" ]; then
  ROOT="${REPO_ROOT}"
else
  # Invoked directly from a platform checkout used as REPO_ROOT/.github/pwnpatterns-ci
  ROOT="$(cd "${PLATFORM_ROOT}/../.." && pwd)"
fi

DEST="${ROOT}/.github/pwnpatterns-ci"
REF_FILE="${ROOT}/.github/platform.ref"
REPO="${PWNPATTERNS_CI_REPO:-ocd-nl/PwnPatterns-ci}"

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

if [ -d "${DEST}/.github/docs-quality/automation" ]; then
  CURRENT="$(git -C "${DEST}" rev-parse HEAD 2>/dev/null || echo "")"
  if [ "${CURRENT}" = "${REF}" ]; then
    exit 0
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
  echo "Fix network/auth or update .github/platform.ref." >&2
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
