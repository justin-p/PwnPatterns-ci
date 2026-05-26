#!/usr/bin/env bash
# Copy a PwnPatterns-ci tree to PWNPATTERNS_CI_DEST (local dev when git clone is unavailable).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE="${PWNPATTERNS_CI_SOURCE:-$(cd "${SCRIPT_DIR}/.." && pwd)}"
DEST="${PWNPATTERNS_CI_DEST:?set PWNPATTERNS_CI_DEST to the consumer .github/pwnpatterns-ci path}"

if [ ! -d "${SOURCE}/.github/docs-quality" ]; then
  echo "export-pwnpatterns-ci: not a PwnPatterns-ci root: ${SOURCE}" >&2
  exit 1
fi

copy_git_paths() {
  local dest_root="$1"
  shift
  cd "${SOURCE}"
  while IFS= read -r rel; do
    [ -z "${rel}" ] && continue
    [ ! -e "${rel}" ] && continue
    mkdir -p "${dest_root}/$(dirname "${rel}")"
    cp -a "${rel}" "${dest_root}/${rel}"
  done < <(git -C "${SOURCE}" ls-files -co --exclude-standard "$@")
}

copy_tool_pkg() {
  local pkg="$1"
  local src="${SOURCE}/.github/docs-quality/tools/${pkg}"
  local out="${DEST}/.github/docs-quality/tools/${pkg}"
  if [ ! -d "${src}" ]; then
    return 0
  fi
  rm -rf "${out}"
  mkdir -p "${out}"
  tar -C "${src}" \
    --exclude='./.venv' \
    --exclude='./__pycache__' \
    --exclude='./.pytest_cache' \
    --exclude='./.coverage' \
    --exclude='*.pyc' \
    -cf - . | tar -C "${out}" -xf -
}

rm -rf "${DEST}"
mkdir -p "${DEST}"

copy_git_paths "${DEST}" \
  .github/docs-quality/automation \
  .github/docs-quality/config/manifest.env \
  .github/docs-quality/config/ci-e2e-expectations.env \
  .github/docs-quality/config/shellcheckrc \
  .github/docs-quality/styles-base \
  .github/lychee/automation \
  .github/tests \
  .github/workflows \
  .github/actions \
  scripts \
  renovate.json \
  README.md \
  .gitignore

mkdir -p "${DEST}/.github/docs-quality/tools"
for pkg in pwnpatterns-ci grammar-routing sync-allowlists verify-metadata docs-dev; do
  copy_tool_pkg "${pkg}"
done

if git -C "${SOURCE}" ls-files --error-unmatch .github/docs-quality/generated/harper-dictionary.txt &>/dev/null; then
  copy_git_paths "${DEST}" .github/docs-quality/generated/harper-dictionary.txt
fi

echo "export-pwnpatterns-ci: ${SOURCE} -> ${DEST}"
