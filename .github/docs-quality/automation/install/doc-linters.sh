#!/usr/bin/env bash
# Install Vale, typos, rumdl, harper-cli, and LanguageTool with SHA256 verification.
set -euo pipefail

# shellcheck source=../lib/env.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/lib/env.sh"

install_dir="${DOC_LINT_INSTALL_DIR:-/tmp}"
mkdir -p "${install_dir}"
install_dir="$(cd "${install_dir}" && pwd)"

install_languagetool() {
  : "${LANGUAGETOOL_VERSION:?LANGUAGETOOL_VERSION is required}"
  : "${LANGUAGETOOL_ZIP_SHA256:?LANGUAGETOOL_ZIP_SHA256 is required}"

  lt_home="${install_dir}/LanguageTool-${LANGUAGETOOL_VERSION}"
  lt_jar="${lt_home}/languagetool-commandline.jar"
  lt_wrapper="${install_dir}/languagetool-cli"

  if [ -f "${lt_jar}" ] && [ -x "${lt_wrapper}" ]; then
    echo "LanguageTool already installed in ${lt_home}"
    "${lt_wrapper}" --version 2>/dev/null || true
    export LANGUAGETOOL_HOME="${lt_home}"
    return 0
  fi

  if ! command -v java >/dev/null 2>&1; then
    echo "Java is required to run LanguageTool (install OpenJDK 17+)" >&2
    return 1
  fi

  local asset url tmp_zip tmp_extract extracted
  asset="LanguageTool-${LANGUAGETOOL_VERSION}.zip"
  url="https://languagetool.org/download/${asset}"
  tmp_zip="$(mktemp "${install_dir}/languagetool.XXXXXX.zip")"
  tmp_extract="$(mktemp -d)"

  (
    cd "${install_dir}"
    curl -fsSLO "${url}"
    echo "${LANGUAGETOOL_ZIP_SHA256}  ${asset}" | sha256sum -c -
    mv "${asset}" "${tmp_zip}"
  )

  unzip -q "${tmp_zip}" -d "${tmp_extract}"
  rm -f "${tmp_zip}"

  extracted="$(find "${tmp_extract}" -maxdepth 1 -type d -name 'LanguageTool-*' | head -1)"
  if [ -z "${extracted}" ] || [ ! -f "${extracted}/languagetool-commandline.jar" ]; then
    echo "Expected LanguageTool-*/languagetool-commandline.jar in archive" >&2
    rm -rf "${tmp_extract}"
    return 1
  fi

  rm -rf "${lt_home}"
  mv "${extracted}" "${lt_home}"
  rm -rf "${tmp_extract}"

  cat >"${lt_wrapper}" <<EOF
#!/usr/bin/env bash
exec java -jar "${lt_jar}" "\$@"
EOF
  chmod +x "${lt_wrapper}"

  export LANGUAGETOOL_HOME="${lt_home}"
  if [ -n "${GITHUB_ENV:-}" ]; then
    echo "LANGUAGETOOL_HOME=${lt_home}" >>"${GITHUB_ENV}"
  fi

  echo "LanguageTool ${LANGUAGETOOL_VERSION} installed at ${lt_home}"
  java -jar "${lt_jar}" --version 2>/dev/null | head -1 || true
}

if [ -x "${install_dir}/vale" ] && [ -x "${install_dir}/typos" ] &&
  [ -x "${install_dir}/rumdl" ] && [ -x "${install_dir}/harper-cli" ]; then
  echo "Doc linters already installed in ${install_dir}"
  "${install_dir}/vale" -v
  "${install_dir}/typos" --version
  "${install_dir}/rumdl" --version
  "${install_dir}/harper-cli" --version
  install_languagetool || true
  exit 0
fi

: "${VALE_VERSION:?VALE_VERSION is required}"
: "${VALE_LINUX_AMD64_SHA256:?VALE_LINUX_AMD64_SHA256 is required}"
: "${TYPOS_VERSION:?TYPOS_VERSION is required}"
: "${TYPOS_LINUX_AMD64_SHA256:?TYPOS_LINUX_AMD64_SHA256 is required}"
: "${RUMDL_VERSION:?RUMDL_VERSION is required}"
: "${RUMDL_LINUX_AMD64_SHA256:?RUMDL_LINUX_AMD64_SHA256 is required}"
: "${HARPER_VERSION:?HARPER_VERSION is required}"
: "${HARPER_LINUX_AMD64_SHA256:?HARPER_LINUX_AMD64_SHA256 is required}"

download_and_verify() {
  local url="$1"
  local sha256="$2"
  local archive="$3"
  local filename
  filename="$(basename "${url}")"
  (
    cd "${install_dir}"
    curl -fsSLO "${url}"
    echo "${sha256}  ${filename}" | sha256sum -c -
    mv "${filename}" "${archive}"
  )
}

install_tar_binary() {
  local name="$1"
  local url="$2"
  local sha256="$3"
  local binary_name="$4"
  local archive extract_dir binary_path
  archive="$(mktemp "${install_dir}/${name}.XXXXXX.tar.gz")"
  download_and_verify "${url}" "${sha256}" "${archive}"
  extract_dir="$(mktemp -d)"
  # Extract to a temp dir: typos archives include "./" and would otherwise
  # try to chmod/utime the install directory (fails in sandboxes / tight perms).
  tar xzf "${archive}" -C "${extract_dir}" --no-same-permissions --touch
  binary_path="${extract_dir}/${binary_name}"
  if [ ! -f "${binary_path}" ]; then
    echo "Expected ${binary_name} in ${archive}" >&2
    rm -rf "${extract_dir}" "${archive}"
    exit 1
  fi
  install -m 0755 "${binary_path}" "${install_dir}/${binary_name}"
  rm -rf "${extract_dir}" "${archive}"
  if [ "${binary_name}" = "harper-cli" ] && [ ! -e "${install_dir}/harper" ]; then
    ln -sf harper-cli "${install_dir}/harper"
  fi
}

vale_asset="vale_${VALE_VERSION}_Linux_64-bit.tar.gz"
install_tar_binary vale \
  "https://github.com/errata-ai/vale/releases/download/v${VALE_VERSION}/${vale_asset}" \
  "${VALE_LINUX_AMD64_SHA256}" \
  vale

typos_asset="typos-v${TYPOS_VERSION}-x86_64-unknown-linux-musl.tar.gz"
install_tar_binary typos \
  "https://github.com/crate-ci/typos/releases/download/v${TYPOS_VERSION}/${typos_asset}" \
  "${TYPOS_LINUX_AMD64_SHA256}" \
  typos

rumdl_asset="rumdl-v${RUMDL_VERSION}-x86_64-unknown-linux-gnu.tar.gz"
install_tar_binary rumdl \
  "https://github.com/rvben/rumdl/releases/download/v${RUMDL_VERSION}/${rumdl_asset}" \
  "${RUMDL_LINUX_AMD64_SHA256}" \
  rumdl

harper_asset="harper-cli-x86_64-unknown-linux-gnu.tar.gz"
install_tar_binary harper \
  "https://github.com/Automattic/harper/releases/download/v${HARPER_VERSION}/${harper_asset}" \
  "${HARPER_LINUX_AMD64_SHA256}" \
  harper-cli

install_languagetool || true

if [ -n "${GITHUB_PATH:-}" ]; then
  echo "${install_dir}" >>"${GITHUB_PATH}"
fi

"${install_dir}/vale" -v
"${install_dir}/typos" --version
"${install_dir}/rumdl" --version
"${install_dir}/harper-cli" --version
