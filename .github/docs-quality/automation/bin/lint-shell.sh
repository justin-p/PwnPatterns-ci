#!/usr/bin/env bash
# Run shellcheck and shfmt on repository shell scripts under .github/.
set -euo pipefail

# shellcheck source=../lib/env.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/lib/env.sh"
cd "${REPO_ROOT}"

export PATH="${DOC_LINT_INSTALL_DIR:-/tmp}:${PATH}"
bash "${AUTOMATION_DIR}/install/shell-linters.sh" >/dev/null

mapfile -t scripts < <(find .github -type f -name '*.sh' | sort)

if [ "${#scripts[@]}" -eq 0 ]; then
  echo "No shell scripts under .github/"
  exit 0
fi

shellcheck_rc="${DOCS_QUALITY_DIR}/config/shellcheckrc"
shellcheck_args=(-x)
if [ -f "${shellcheck_rc}" ]; then
  shellcheck_args+=(--rcfile="${shellcheck_rc}")
fi

echo "==> shellcheck (${#scripts[@]} scripts)"
shellcheck "${shellcheck_args[@]}" "${scripts[@]}"

if [ "${CI_LINT_AUTOFIX:-}" = true ]; then
  echo "==> shfmt (write)"
  shfmt -w -ln bash -i 2 -ci "${scripts[@]}"
else
  echo "==> shfmt"
  shfmt -d -ln bash -i 2 -ci "${scripts[@]}"
fi
