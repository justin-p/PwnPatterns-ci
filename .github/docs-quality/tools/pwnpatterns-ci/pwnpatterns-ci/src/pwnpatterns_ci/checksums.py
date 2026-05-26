"""Refresh manifest.env SHA256 checksums from upstream releases."""

from __future__ import annotations

import hashlib
import re
import tempfile
import urllib.request
from pathlib import Path

from pwnpatterns_ci.paths import Layout

_LINE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$")


def _get_var(lines: list[str], name: str) -> str:
    for line in lines:
        m = _LINE.match(line.strip())
        if m and m.group(1) == name:
            return m.group(2)
    raise KeyError(name)


def _set_var(lines: list[str], name: str, value: str) -> None:
    for i, line in enumerate(lines):
        m = _LINE.match(line.strip())
        if m and m.group(1) == name:
            lines[i] = f"{name}={value}"
            return
    lines.append(f"{name}={value}")


def _fetch_sha256(url: str) -> str:
    try:
        with urllib.request.urlopen(f"{url}.sha256", timeout=120) as resp:
            return resp.read().decode().split()[0]
    except OSError:
        pass
    with tempfile.NamedTemporaryFile(delete=True) as tmp:
        urllib.request.urlretrieve(url, tmp.name)
        h = hashlib.sha256()
        with open(tmp.name, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()


def refresh_checksums(layout: Layout) -> None:
    manifest = layout.manifest_path()
    lines = manifest.read_text(encoding="utf-8").splitlines()

    vale_v = _get_var(lines, "VALE_VERSION")
    _set_var(
        lines,
        "VALE_LINUX_AMD64_SHA256",
        _fetch_sha256(
            f"https://github.com/errata-ai/vale/releases/download/v{vale_v}/"
            f"vale_{vale_v}_Linux_64-bit.tar.gz"
        ),
    )

    typos_v = _get_var(lines, "TYPOS_VERSION")
    _set_var(
        lines,
        "TYPOS_LINUX_AMD64_SHA256",
        _fetch_sha256(
            f"https://github.com/crate-ci/typos/releases/download/v{typos_v}/"
            f"typos-v{typos_v}-x86_64-unknown-linux-musl.tar.gz"
        ),
    )

    rumdl_v = _get_var(lines, "RUMDL_VERSION")
    _set_var(
        lines,
        "RUMDL_LINUX_AMD64_SHA256",
        _fetch_sha256(
            f"https://github.com/rvben/rumdl/releases/download/v{rumdl_v}/"
            f"rumdl-v{rumdl_v}-x86_64-unknown-linux-gnu.tar.gz"
        ),
    )

    harper_v = _get_var(lines, "HARPER_VERSION")
    _set_var(
        lines,
        "HARPER_LINUX_AMD64_SHA256",
        _fetch_sha256(
            f"https://github.com/Automattic/harper/releases/download/v{harper_v}/"
            "harper-cli-x86_64-unknown-linux-gnu.tar.gz"
        ),
    )

    lt_v = _get_var(lines, "LANGUAGETOOL_VERSION")
    lt_url = f"https://languagetool.org/download/LanguageTool-{lt_v}.zip"
    with tempfile.NamedTemporaryFile(delete=True) as tmp:
        urllib.request.urlretrieve(lt_url, tmp.name)
        h = hashlib.sha256()
        with open(tmp.name, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        _set_var(lines, "LANGUAGETOOL_ZIP_SHA256", h.hexdigest())

    for tool, asset_tpl in (
        ("SHELLCHECK", "shellcheck-v{v}.linux.x86_64.tar.xz"),
        ("SHFMT", "shfmt_v{v}_linux_amd64"),
        ("REVIEWDOG", "reviewdog_{v}_Linux_x86_64.tar.gz"),
        ("LYCHEE", "lychee-x86_64-unknown-linux-gnu.tar.gz"),
        ("ACTIONLINT", "actionlint_{v}_linux_amd64.tar.gz"),
    ):
        v = _get_var(lines, f"{tool}_VERSION")
        base = {
            "SHELLCHECK": f"https://github.com/koalaman/shellcheck/releases/download/v{v}/",
            "SHFMT": f"https://github.com/mvdan/sh/releases/download/v{v}/",
            "REVIEWDOG": f"https://github.com/reviewdog/reviewdog/releases/download/v{v}/",
            "LYCHEE": f"https://github.com/lycheeverse/lychee/releases/download/lychee-v{v}/",
            "ACTIONLINT": f"https://github.com/rhysd/actionlint/releases/download/v{v}/",
        }[tool]
        asset = asset_tpl.format(v=v)
        _set_var(lines, f"{tool}_LINUX_AMD64_SHA256", _fetch_sha256(base + asset))

    manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")
