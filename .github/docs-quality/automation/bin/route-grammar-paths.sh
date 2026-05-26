#!/usr/bin/env bash
# Split lint targets by frontmatter language and grammar tool (see config/language-tools.yml).
# Writes grammar-harper-paths.lst, grammar-languagetool.tsv, and grammar-route.json under LOG_DIR.
set -euo pipefail

# shellcheck source=../lib/env.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/lib/env.sh"

LOG_DIR="${1:-lint-logs}"

mapfile -t paths < <(bash "${AUTOMATION_DIR}/bin/load-doc-paths.sh")
mkdir -p "${LOG_DIR}"

if [ "${#paths[@]}" -eq 0 ]; then
  : >"${LOG_DIR}/grammar-harper-paths.lst"
  : >"${LOG_DIR}/grammar-languagetool.tsv"
  echo '{"harper":[],"languagetool":[],"none":[]}' >"${LOG_DIR}/grammar-route.json"
  exit 0
fi

uv_run_tool "${DOCS_QUALITY_DIR}/tools/grammar-routing" \
  python route_grammar_paths.py \
  --log-dir "${LOG_DIR}" \
  --repo-root "${REPO_ROOT}" \
  "${paths[@]}"
