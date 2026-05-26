#!/usr/bin/env bash
# Refresh *_LINUX_AMD64_SHA256 values in manifest.env from release checksums.
set -euo pipefail

# shellcheck source=../lib/env.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/lib/env.sh"
manifest="${DOCS_QUALITY_DIR}/config/manifest.env"

get_var() {
  grep -E "^${1}=" "${manifest}" | head -1 | cut -d= -f2-
}

set_var() {
  local name="$1"
  local value="$2"
  sed -i "s|^${name}=.*|${name}=${value}|" "${manifest}"
}

fetch_sha256() {
  local url="$1"
  if curl -fsSL "${url}.sha256" 2>/dev/null | awk '{print $1; exit}'; then
    return 0
  fi
  local tmp
  tmp="$(mktemp)"
  curl -fsSL -o "${tmp}" "${url}"
  sha256sum "${tmp}" | awk '{print $1}'
  rm -f "${tmp}"
}

vale_version="$(get_var VALE_VERSION)"
vale_asset="vale_${vale_version}_Linux_64-bit.tar.gz"
vale_sha="$(fetch_sha256 "https://github.com/errata-ai/vale/releases/download/v${vale_version}/${vale_asset}")"
set_var VALE_LINUX_AMD64_SHA256 "${vale_sha}"
echo "VALE ${vale_version} -> ${vale_sha}"

typos_version="$(get_var TYPOS_VERSION)"
typos_asset="typos-v${typos_version}-x86_64-unknown-linux-musl.tar.gz"
typos_sha="$(fetch_sha256 "https://github.com/crate-ci/typos/releases/download/v${typos_version}/${typos_asset}")"
set_var TYPOS_LINUX_AMD64_SHA256 "${typos_sha}"
echo "TYPOS ${typos_version} -> ${typos_sha}"

rumdl_version="$(get_var RUMDL_VERSION)"
rumdl_asset="rumdl-v${rumdl_version}-x86_64-unknown-linux-gnu.tar.gz"
rumdl_sha="$(fetch_sha256 "https://github.com/rvben/rumdl/releases/download/v${rumdl_version}/${rumdl_asset}")"
set_var RUMDL_LINUX_AMD64_SHA256 "${rumdl_sha}"
echo "RUMDL ${rumdl_version} -> ${rumdl_sha}"

harper_version="$(get_var HARPER_VERSION)"
harper_asset="harper-cli-x86_64-unknown-linux-gnu.tar.gz"
harper_sha="$(fetch_sha256 "https://github.com/Automattic/harper/releases/download/v${harper_version}/${harper_asset}")"
set_var HARPER_LINUX_AMD64_SHA256 "${harper_sha}"
echo "HARPER ${harper_version} -> ${harper_sha}"

lt_version="$(get_var LANGUAGETOOL_VERSION)"
lt_asset="LanguageTool-${lt_version}.zip"
lt_tmp="$(mktemp)"
curl -fsSL -o "${lt_tmp}" "https://languagetool.org/download/${lt_asset}"
lt_sha="$(sha256sum "${lt_tmp}" | awk '{print $1}')"
rm -f "${lt_tmp}"
set_var LANGUAGETOOL_ZIP_SHA256 "${lt_sha}"
echo "LANGUAGETOOL ${lt_version} -> ${lt_sha}"

shellcheck_version="$(get_var SHELLCHECK_VERSION)"
shellcheck_asset="shellcheck-v${shellcheck_version}.linux.x86_64.tar.xz"
shellcheck_sha="$(fetch_sha256 "https://github.com/koalaman/shellcheck/releases/download/v${shellcheck_version}/${shellcheck_asset}")"
set_var SHELLCHECK_LINUX_AMD64_SHA256 "${shellcheck_sha}"
echo "SHELLCHECK ${shellcheck_version} -> ${shellcheck_sha}"

shfmt_version="$(get_var SHFMT_VERSION)"
shfmt_asset="shfmt_v${shfmt_version}_linux_amd64"
shfmt_sha="$(fetch_sha256 "https://github.com/mvdan/sh/releases/download/v${shfmt_version}/${shfmt_asset}")"
set_var SHFMT_LINUX_AMD64_SHA256 "${shfmt_sha}"
echo "SHFMT ${shfmt_version} -> ${shfmt_sha}"

reviewdog_version="$(get_var REVIEWDOG_VERSION)"
reviewdog_asset="reviewdog_${reviewdog_version}_Linux_x86_64.tar.gz"
reviewdog_sha="$(fetch_sha256 "https://github.com/reviewdog/reviewdog/releases/download/v${reviewdog_version}/${reviewdog_asset}")"
set_var REVIEWDOG_LINUX_AMD64_SHA256 "${reviewdog_sha}"
echo "REVIEWDOG ${reviewdog_version} -> ${reviewdog_sha}"

lychee_version="$(get_var LYCHEE_VERSION)"
lychee_asset="lychee-x86_64-unknown-linux-gnu.tar.gz"
lychee_sha="$(fetch_sha256 "https://github.com/lycheeverse/lychee/releases/download/lychee-v${lychee_version}/${lychee_asset}")"
set_var LYCHEE_LINUX_AMD64_SHA256 "${lychee_sha}"
echo "LYCHEE ${lychee_version} -> ${lychee_sha}"

actionlint_version="$(get_var ACTIONLINT_VERSION)"
actionlint_asset="actionlint_${actionlint_version}_linux_amd64.tar.gz"
actionlint_sha="$(fetch_sha256 "https://github.com/rhysd/actionlint/releases/download/v${actionlint_version}/${actionlint_asset}")"
set_var ACTIONLINT_LINUX_AMD64_SHA256 "${actionlint_sha}"
echo "ACTIONLINT ${actionlint_version} -> ${actionlint_sha}"
