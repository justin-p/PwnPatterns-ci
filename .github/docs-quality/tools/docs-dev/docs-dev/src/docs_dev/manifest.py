from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Manifest:
    doc_lint_install_dir: str
    vale_version: str
    typos_version: str
    rumdl_version: str
    harper_version: str
    harper_user_dict: str
    harper_ignore_rules_file: str
    shellcheck_version: str
    shfmt_version: str
    reviewdog_version: str
    lychee_version: str
    actionlint_version: str
    raw: dict[str, str]

    def harper_ignore_rules_csv(self, repo_root: Path) -> str:
        path = repo_root / self.harper_ignore_rules_file
        if not path.is_file():
            return ""
        lines: list[str] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            lines.append(s)
        return ",".join(lines)


_ENV_LINE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$")


def load_manifest(path: Path) -> Manifest:
    raw: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        m = _ENV_LINE.match(s)
        if not m:
            continue
        raw[m.group(1)] = m.group(2)

    def req(key: str) -> str:
        if key not in raw:
            raise KeyError(f"Missing {key} in {path}")
        return raw[key]

    return Manifest(
        doc_lint_install_dir=raw.get("DOC_LINT_INSTALL_DIR", "/tmp"),
        vale_version=req("VALE_VERSION"),
        typos_version=req("TYPOS_VERSION"),
        rumdl_version=req("RUMDL_VERSION"),
        harper_version=req("HARPER_VERSION"),
        harper_user_dict=req("HARPER_USER_DICT"),
        harper_ignore_rules_file=req("HARPER_IGNORE_RULES_FILE"),
        shellcheck_version=req("SHELLCHECK_VERSION"),
        shfmt_version=req("SHFMT_VERSION"),
        reviewdog_version=req("REVIEWDOG_VERSION"),
        lychee_version=req("LYCHEE_VERSION"),
        actionlint_version=req("ACTIONLINT_VERSION"),
        raw=raw,
    )
