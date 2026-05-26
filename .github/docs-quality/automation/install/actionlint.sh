#!/usr/bin/env bash
# Install actionlint with SHA256 verification (manifest pin).
set -euo pipefail

# shellcheck source=../lib/env.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/lib/env.sh"

install_dir="${DOC_LINT_INSTALL_DIR:-/tmp}"
mkdir -p "${install_dir}"
install_dir="$(cd "${install_dir}" && pwd)"

if [ -x "${install_dir}/actionlint" ]; then
  echo "actionlint already installed in ${install_dir}"
  "${install_dir}/actionlint" -version
  exit 0
fi

: "${ACTIONLINT_VERSION:?ACTIONLINT_VERSION is required}"
: "${ACTIONLINT_LINUX_AMD64_SHA256:?ACTIONLINT_LINUX_AMD64_SHA256 is required}"

asset="actionlint_${ACTIONLINT_VERSION}_linux_amd64.tar.gz"
url="https://github.com/rhysd/actionlint/releases/download/v${ACTIONLINT_VERSION}/${asset}"
tmp="$(mktemp -d)"
archive="${tmp}/${asset}"

curl -fsSL -o "${archive}" "${url}"
echo "${ACTIONLINT_LINUX_AMD64_SHA256}  ${archive}" | sha256sum -c -
tar -xzf "${archive}" -C "${tmp}"
install -m 0755 "${tmp}/actionlint" "${install_dir}/actionlint"
rm -rf "${tmp}"

export PATH="${install_dir}:${PATH}"
actionlint -version
