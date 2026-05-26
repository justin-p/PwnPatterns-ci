#!/usr/bin/env bash
# Install reviewdog with SHA256 verification (manifest pin).
set -euo pipefail

# shellcheck source=../lib/env.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/lib/env.sh"

install_dir="${DOC_LINT_INSTALL_DIR:-/tmp}"
mkdir -p "${install_dir}"

if command -v reviewdog >/dev/null 2>&1 && reviewdog -version >/dev/null 2>&1; then
  if [ -x "${install_dir}/reviewdog" ]; then
    echo "reviewdog already installed in ${install_dir}"
    reviewdog -version
    exit 0
  fi
fi

: "${REVIEWDOG_VERSION:?REVIEWDOG_VERSION is required}"
: "${REVIEWDOG_LINUX_AMD64_SHA256:?REVIEWDOG_LINUX_AMD64_SHA256 is required}"

asset="reviewdog_${REVIEWDOG_VERSION}_Linux_x86_64.tar.gz"
url="https://github.com/reviewdog/reviewdog/releases/download/v${REVIEWDOG_VERSION}/${asset}"
tmp="$(mktemp -d)"
archive="${tmp}/${asset}"

curl -fsSL -o "${archive}" "${url}"
echo "${REVIEWDOG_LINUX_AMD64_SHA256}  ${archive}" | sha256sum -c -
tar -xzf "${archive}" -C "${tmp}"
install -m 0755 "${tmp}/reviewdog" "${install_dir}/reviewdog"
rm -rf "${tmp}"

export PATH="${install_dir}:${PATH}"
reviewdog -version
