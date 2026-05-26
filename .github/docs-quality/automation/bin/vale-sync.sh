#!/usr/bin/env bash
# Sync Vale packages from .vale.ini into styles/ (committed + CI cache).
set -euo pipefail

# shellcheck source=../lib/env.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/lib/env.sh"
cd "${REPO_ROOT}"
mkdir -p styles
# Plain output for TUI/CI logs (vale sync uses Rich progress bars by default).
export NO_COLOR=1
export CLICOLOR=0
export TERM="${TERM:-dumb}"
vale sync
