"""Download and install pinned doc/shell/reviewdog tools."""

from __future__ import annotations

import hashlib
import os
import sys
import shutil
import subprocess
import tarfile
import tempfile
import urllib.request
import zipfile
from pathlib import Path

from pwnpatterns_ci.paths import Layout


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def download_verify(url: str, expected_sha256: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    # Some hosts (e.g. languagetool.org) reject urllib's default user agent with 403.
    req = urllib.request.Request(url, headers={"User-Agent": "PwnPatterns-ci/1.0"})
    with urllib.request.urlopen(req, timeout=300) as resp:
        data = resp.read()
    dest.write_bytes(data)
    actual = _sha256_file(dest)
    if actual != expected_sha256.lower():
        dest.unlink(missing_ok=True)
        raise RuntimeError(f"SHA256 mismatch for {url}: expected {expected_sha256}, got {actual}")


def install_dir() -> Path:
    raw = os.environ.get("DOC_LINT_INSTALL_DIR", "/tmp")
    p = Path(raw)
    p.mkdir(parents=True, exist_ok=True)
    return p.resolve()


def _prepend_path(install: Path) -> None:
    os.environ["PATH"] = f"{install}{os.pathsep}{os.environ.get('PATH', '')}"
    gh_path = os.environ.get("GITHUB_PATH")
    if gh_path:
        with open(gh_path, "a", encoding="utf-8") as fh:
            fh.write(f"{install}\n")


def _install_tar_binary(
    install: Path,
    name: str,
    url: str,
    sha256: str,
    binary_name: str,
) -> None:
    dest = install / binary_name
    if dest.is_file():
        return
    with tempfile.TemporaryDirectory() as tmp:
        archive = Path(tmp) / Path(url).name
        download_verify(url, sha256, archive)
        extract = Path(tmp) / "extract"
        extract.mkdir()
        with tarfile.open(archive, "r:gz") as tf:
            tf.extractall(extract, filter="data")
        binary = extract / binary_name
        if not binary.is_file():
            raise RuntimeError(f"Expected {binary_name} in {url}")
        shutil.copy2(binary, dest)
        dest.chmod(0o755)
    if binary_name == "harper-cli" and not (install / "harper").exists():
        (install / "harper").symlink_to("harper-cli")


def install_doc_linters(layout: Layout) -> None:
    install = install_dir()
    v = os.environ
    required = (
        "VALE_VERSION",
        "VALE_LINUX_AMD64_SHA256",
        "TYPOS_VERSION",
        "TYPOS_LINUX_AMD64_SHA256",
        "RUMDL_VERSION",
        "RUMDL_LINUX_AMD64_SHA256",
        "HARPER_VERSION",
        "HARPER_LINUX_AMD64_SHA256",
    )
    for key in required:
        if not v.get(key):
            raise RuntimeError(f"{key} is required")

    vale_v = v["VALE_VERSION"]
    _install_tar_binary(
        install,
        "vale",
        f"https://github.com/errata-ai/vale/releases/download/v{vale_v}/vale_{vale_v}_Linux_64-bit.tar.gz",
        v["VALE_LINUX_AMD64_SHA256"],
        "vale",
    )
    typos_v = v["TYPOS_VERSION"]
    _install_tar_binary(
        install,
        "typos",
        f"https://github.com/crate-ci/typos/releases/download/v{typos_v}/typos-v{typos_v}-x86_64-unknown-linux-musl.tar.gz",
        v["TYPOS_LINUX_AMD64_SHA256"],
        "typos",
    )
    rumdl_v = v["RUMDL_VERSION"]
    _install_tar_binary(
        install,
        "rumdl",
        f"https://github.com/rvben/rumdl/releases/download/v{rumdl_v}/rumdl-v{rumdl_v}-x86_64-unknown-linux-gnu.tar.gz",
        v["RUMDL_LINUX_AMD64_SHA256"],
        "rumdl",
    )
    harper_v = v["HARPER_VERSION"]
    _install_tar_binary(
        install,
        "harper",
        f"https://github.com/Automattic/harper/releases/download/v{harper_v}/harper-cli-x86_64-unknown-linux-gnu.tar.gz",
        v["HARPER_LINUX_AMD64_SHA256"],
        "harper-cli",
    )
    try:
        _install_languagetool(install)
    except Exception as exc:
        print(f"LanguageTool install skipped: {exc}", file=sys.stderr)
    try:
        _install_textlint(layout)
    except Exception as exc:
        print(f"textlint install skipped: {exc}", file=sys.stderr)
    _prepend_path(install)


def _install_languagetool(install: Path) -> None:
    v = os.environ
    lt_v = v.get("LANGUAGETOOL_VERSION")
    lt_sha = v.get("LANGUAGETOOL_ZIP_SHA256")
    if not lt_v or not lt_sha:
        return
    lt_home = install / f"LanguageTool-{lt_v}"
    jar = lt_home / "languagetool-commandline.jar"
    wrapper = install / "languagetool-cli"
    if jar.is_file() and wrapper.is_file():
        os.environ["LANGUAGETOOL_HOME"] = str(lt_home)
        return
    if shutil.which("java") is None:
        raise RuntimeError("Java is required for LanguageTool")
    asset = f"LanguageTool-{lt_v}.zip"
    url = f"https://languagetool.org/download/{asset}"
    with tempfile.TemporaryDirectory() as tmp:
        zpath = Path(tmp) / asset
        download_verify(url, lt_sha, zpath)
        with zipfile.ZipFile(zpath) as zf:
            zf.extractall(Path(tmp))
        extracted = next(
            (
                p
                for p in Path(tmp).glob("LanguageTool-*")
                if p.is_dir() and (p / "languagetool-commandline.jar").is_file()
            ),
            None,
        )
        if not extracted:
            raise RuntimeError("Invalid LanguageTool archive")
        if lt_home.exists():
            shutil.rmtree(lt_home)
        shutil.move(str(extracted), str(lt_home))
    wrapper.write_text(
        f'#!/usr/bin/env bash\nexec java -jar "{jar}" "$@"\n',
        encoding="utf-8",
    )
    wrapper.chmod(0o755)
    os.environ["LANGUAGETOOL_HOME"] = str(lt_home)
    gh_env = os.environ.get("GITHUB_ENV")
    if gh_env:
        with open(gh_env, "a", encoding="utf-8") as fh:
            fh.write(f"LANGUAGETOOL_HOME={lt_home}\n")


def _install_textlint(layout: Layout) -> None:
    cfg = layout.docs_quality_dir / "config" / "textlint"
    pkg = cfg / "package.json"
    if not pkg.is_file():
        return
    if shutil.which("bun") is None:
        raise RuntimeError("bun is required for textlint")
    subprocess.run(
        ["bun", "install", "--frozen-lockfile"],
        cwd=cfg,
        check=True,
    )


def install_shell_linters() -> None:
    install = install_dir()
    v = os.environ
    if (install / "shellcheck").is_file() and (install / "shfmt").is_file():
        _prepend_path(install)
        return
    sc_v = v["SHELLCHECK_VERSION"]
    sc_sha = v["SHELLCHECK_LINUX_AMD64_SHA256"]
    sh_v = v["SHFMT_VERSION"]
    sh_sha = v["SHFMT_LINUX_AMD64_SHA256"]
    with tempfile.TemporaryDirectory() as tmp:
        sc_asset = f"shellcheck-v{sc_v}.linux.x86_64.tar.xz"
        sc_url = f"https://github.com/koalaman/shellcheck/releases/download/v{sc_v}/{sc_asset}"
        sc_archive = Path(tmp) / sc_asset
        download_verify(sc_url, sc_sha, sc_archive)
        with tarfile.open(sc_archive, "r:xz") as tf:
            tf.extractall(install, filter="data")
        sc_bin = install / f"shellcheck-v{sc_v}" / "shellcheck"
        shutil.move(str(sc_bin), str(install / "shellcheck"))
        shutil.rmtree(install / f"shellcheck-v{sc_v}", ignore_errors=True)
        sh_asset = f"shfmt_v{sh_v}_linux_amd64"
        sh_url = f"https://github.com/mvdan/sh/releases/download/v{sh_v}/{sh_asset}"
        sh_dest = install / "shfmt"
        download_verify(sh_url, sh_sha, sh_dest)
        sh_dest.chmod(0o755)
    _prepend_path(install)


def install_actionlint() -> None:
    install = install_dir()
    if (install / "actionlint").is_file():
        _prepend_path(install)
        return
    v = os.environ["ACTIONLINT_VERSION"]
    sha = os.environ["ACTIONLINT_LINUX_AMD64_SHA256"]
    asset = f"actionlint_{v}_linux_amd64.tar.gz"
    url = f"https://github.com/rhysd/actionlint/releases/download/v{v}/{asset}"
    with tempfile.TemporaryDirectory() as tmp:
        archive = Path(tmp) / asset
        download_verify(url, sha, archive)
        with tarfile.open(archive, "r:gz") as tf:
            tf.extractall(Path(tmp), filter="data")
        shutil.copy2(Path(tmp) / "actionlint", install / "actionlint")
        (install / "actionlint").chmod(0o755)
    _prepend_path(install)


def install_reviewdog() -> None:
    install = install_dir()
    dest = install / "reviewdog"
    if dest.is_file() and subprocess.run(
        [str(dest), "-version"], capture_output=True, check=False
    ).returncode == 0:
        _prepend_path(install)
        return
    v = os.environ["REVIEWDOG_VERSION"]
    sha = os.environ["REVIEWDOG_LINUX_AMD64_SHA256"]
    asset = f"reviewdog_{v}_Linux_x86_64.tar.gz"
    url = f"https://github.com/reviewdog/reviewdog/releases/download/v{v}/{asset}"
    with tempfile.TemporaryDirectory() as tmp:
        archive = Path(tmp) / asset
        download_verify(url, sha, archive)
        with tarfile.open(archive, "r:gz") as tf:
            tf.extractall(Path(tmp), filter="data")
        shutil.copy2(Path(tmp) / "reviewdog", dest)
        dest.chmod(0o755)
    _prepend_path(install)
