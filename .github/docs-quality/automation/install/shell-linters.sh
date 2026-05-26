#!/usr/bin/env bash
# Install shellcheck and shfmt with SHA256 verification (see manifest.env).
set -euo pipefail

# shellcheck source=../lib/env.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/lib/env.sh"

install_dir="${DOC_LINT_INSTALL_DIR:-/tmp}"
mkdir -p "${install_dir}"

if [ -x "${install_dir}/shellcheck" ] && [ -x "${install_dir}/shfmt" ]; then
  echo "Shell linters already installed in ${install_dir}"
  "${install_dir}/shellcheck" --version
  "${install_dir}/shfmt" --version
  exit 0
fi

: "${SHELLCHECK_VERSION:?SHELLCHECK_VERSION is required}"
: "${SHELLCHECK_LINUX_AMD64_SHA256:?SHELLCHECK_LINUX_AMD64_SHA256 is required}"
: "${SHFMT_VERSION:?SHFMT_VERSION is required}"
: "${SHFMT_LINUX_AMD64_SHA256:?SHFMT_LINUX_AMD64_SHA256 is required}"

download_and_verify() {
  local url="$1"
  local sha256="$2"
  local dest="$3"
  local filename
  filename="$(basename "${url}")"
  (
    cd "${install_dir}"
    curl -fsSLO "${url}"
    echo "${sha256}  ${filename}" | sha256sum -c -
    mv "${filename}" "${dest}"
  )
}

shellcheck_asset="shellcheck-v${SHELLCHECK_VERSION}.linux.x86_64.tar.xz"
shellcheck_archive="$(mktemp "${install_dir}/shellcheck.XXXXXX.tar.xz")"
download_and_verify \
  "https://github.com/koalaman/shellcheck/releases/download/v${SHELLCHECK_VERSION}/${shellcheck_asset}" \
  "${SHELLCHECK_LINUX_AMD64_SHA256}" \
  "${shellcheck_archive}"
tar xJf "${shellcheck_archive}" -C "${install_dir}"
rm -f "${shellcheck_archive}"
mv "${install_dir}/shellcheck-v${SHELLCHECK_VERSION}/shellcheck" "${install_dir}/shellcheck"
rm -rf "${install_dir}/shellcheck-v${SHELLCHECK_VERSION}"
chmod +x "${install_dir}/shellcheck"

shfmt_asset="shfmt_v${SHFMT_VERSION}_linux_amd64"
shfmt_archive="$(mktemp "${install_dir}/shfmt.XXXXXX")"
download_and_verify \
  "https://github.com/mvdan/sh/releases/download/v${SHFMT_VERSION}/${shfmt_asset}" \
  "${SHFMT_LINUX_AMD64_SHA256}" \
  "${shfmt_archive}"
mv "${shfmt_archive}" "${install_dir}/shfmt"
chmod +x "${install_dir}/shfmt"

if [ -n "${GITHUB_PATH:-}" ]; then
  echo "${install_dir}" >>"${GITHUB_PATH}"
fi

"${install_dir}/shellcheck" --version
"${install_dir}/shfmt" --version
