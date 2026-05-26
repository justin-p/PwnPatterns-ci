#!/usr/bin/env bash
# Run shellcheck and shfmt on repository shell scripts under .github/.
# By default skips .github/pwnpatterns-ci/ (vendored platform); set
# LINT_SHELL_INCLUDE_PLATFORM=1 to lint the full tree (CI E2E uses ci-steps.sh).
set -euo pipefail

# shellcheck source=../lib/env.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/lib/env.sh"
cd "${REPO_ROOT}"

export PATH="${DOC_LINT_INSTALL_DIR:-/tmp}:${PATH}"
bash "${AUTOMATION_DIR}/install/shell-linters.sh" >/dev/null

if [ "${LINT_SHELL_INCLUDE_PLATFORM:-}" = "1" ]; then
  mapfile -t scripts < <(find .github -type f -name '*.sh' | sort)
else
  mapfile -t scripts < <(
    find .github -type f -name '*.sh' ! -path '*/pwnpatterns-ci/*' | sort
  )
fi

if [ "${#scripts[@]}" -eq 0 ]; then
  echo "No shell scripts to lint under .github/ (skipped vendored platform tree)."
  exit 0
fi

shellcheck_rc="${DOCS_QUALITY_DIR}/config/shellcheckrc"
shellcheck_args=(-x)
if [ -f "${shellcheck_rc}" ]; then
  shellcheck_args+=(--rcfile="${shellcheck_rc}")
fi

echo "==> shellcheck (${#scripts[@]} scripts)"
shellcheck "${shellcheck_args[@]}" "${scripts[@]}"

shfmt_mode="-d"
shfmt_label="check"
if [ "${CI_LINT_AUTOFIX:-}" = "true" ]; then
  shfmt_mode="-w"
  shfmt_label="write"
fi

echo "==> shfmt (${shfmt_label}, ${#scripts[@]} scripts)"
shfmt_fail=0
idx=0
for script in "${scripts[@]}"; do
  idx=$((idx + 1))
  echo "shfmt ${idx}/${#scripts[@]}: ${script}"
  if ! shfmt "${shfmt_mode}" -ln bash -i 2 -ci "${script}"; then
    shfmt_fail=1
  fi
done
echo "==> shfmt done"
exit "${shfmt_fail}"
