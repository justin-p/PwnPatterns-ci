#!/usr/bin/env bash
# Emit GITHUB_OUTPUT: scan_mode (changed|all), paths (multiline), skip (true|false)
set -euo pipefail

CONFIG_PATTERN='^(\.vale\.ini|_typos\.toml|rumdl\.toml|\.markdownlint\.json|styles/|\.github/docs-quality/|\.github/lychee/)'

emit_paths() {
  local -n _arr=$1
  if [ "${#_arr[@]}" -eq 0 ]; then
    echo "skip=true" >>"${GITHUB_OUTPUT:?}"
    echo "No documentation targets for this event."
    return
  fi
  echo "skip=false" >>"${GITHUB_OUTPUT}"
  {
    echo 'paths<<EOF'
    printf '%s\n' "${_arr[@]}"
    echo 'EOF'
  } >>"${GITHUB_OUTPUT}"
}

if [ "${GITHUB_EVENT_NAME}" = "pull_request" ]; then
  pr_range="${GITHUB_EVENT_PULL_REQUEST_BASE_SHA}...${GITHUB_EVENT_PULL_REQUEST_HEAD_SHA}"
  mapfile -t md_files < <(
    git diff --name-only --diff-filter=ACMR "${pr_range}" -- docs/ | grep -E '\.md$' || true
  )
  mapfile -t other_files < <(
    git diff --name-only --diff-filter=ACMR "${pr_range}" || true
  )

  if [ "${#md_files[@]}" -gt 0 ]; then
    echo "scan_mode=changed" >>"${GITHUB_OUTPUT}"
    emit_paths md_files
    exit 0
  fi

  config_only=true
  for f in "${other_files[@]}"; do
    [ -z "${f}" ] && continue
    if [[ "${f}" =~ ${CONFIG_PATTERN} ]]; then
      continue
    fi
    config_only=false
    break
  done

  if [ "${config_only}" = true ] && [ "${#other_files[@]}" -gt 0 ]; then
    echo "scan_mode=all" >>"${GITHUB_OUTPUT}"
    mapfile -t md_files < <(find docs -type f -name '*.md' | sort)
    emit_paths md_files
    exit 0
  fi

  echo "skip=true" >>"${GITHUB_OUTPUT}"
  exit 0
fi

# push to main or other events
echo "scan_mode=all" >>"${GITHUB_OUTPUT}"
mapfile -t md_files < <(find docs -type f -name '*.md' | sort)
emit_paths md_files
