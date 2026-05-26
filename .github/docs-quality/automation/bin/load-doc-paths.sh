#!/usr/bin/env bash
# Read multiline doc paths (e.g. from $GITHUB_OUTPUT paths<<EOF) onto stdout, one per line.
# Usage: mapfile -t paths < <(bash load-doc-paths.sh)   # with DOC_PATHS in env
#    or: mapfile -t paths < <(bash load-doc-paths.sh "$paths_blob")
set -euo pipefail

_text="${1:-${DOC_PATHS:-}}"
if [ -z "${_text}" ]; then
  exit 0
fi
while IFS= read -r _line || [ -n "${_line}" ]; do
  [ -n "${_line}" ] && printf '%s\n' "${_line}"
done <<<"${_text}"
