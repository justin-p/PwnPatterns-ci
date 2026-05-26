#!/usr/bin/env python3
"""Regenerate Vale accept, Harper dictionary, and typos blocks from canonical allowlists."""

from __future__ import annotations

import sys
from pathlib import Path

DOCS_QUALITY_DIR = Path(__file__).resolve().parents[2]
_DOCS_DEV_SRC = DOCS_QUALITY_DIR / "tools" / "docs-dev" / "src"
if str(_DOCS_DEV_SRC) not in sys.path:
    sys.path.insert(0, str(_DOCS_DEV_SRC))

from docs_dev.allowlist import (  # noqa: E402
    canonical_casing_path,
    dictionary_entries,
    merge_patterns,
    vale_token_ignores,
    normalize_terms,
    parse_patterns_file,
    parse_canonical_casing_file,
    parse_terms_file,
    read_canonical_casing,
    read_terms,
    vale_accept_entries,
    write_patterns_file,
    write_terms_file,
)

_VALE_INI_BEGIN = "# BEGIN GENERATED TokenIgnores"
_VALE_INI_END = "# END GENERATED TokenIgnores"


def repo_root() -> Path:
    import os

    if os.environ.get("REPO_ROOT"):
        return Path(os.environ["REPO_ROOT"]).resolve()
    return DOCS_QUALITY_DIR.parents[1]


def consumer_config_dir(root: Path) -> Path:
    import os

    env = os.environ.get("CONSUMER_CONFIG_DIR")
    if env:
        return Path(env).resolve()
    p = root / ".github/docs-quality/config"
    if p.is_dir():
        return p
    return DOCS_QUALITY_DIR / "config"


def replace_block(content: str, begin: str, end: str, lines: list[str]) -> str:
    start = content.index(begin) + len(begin)
    stop = content.index(end)
    body = "\n".join(lines) + ("\n" if lines else "")
    return content[:start] + "\n" + body + content[stop:]


def sync(root: Path) -> tuple[Path, Path, Path]:
    cfg = consumer_config_dir(root)
    terms_path = cfg / "allowlists/terms.txt"
    patterns_path = cfg / "allowlists/patterns.txt"
    accept_path = root / "styles/config/vocabularies/PwnPatterns/accept.txt"
    harper_dict_path = root / ".github/docs-quality/generated/harper-dictionary.txt"
    typos_path = root / "_typos.toml"

    casing_path = canonical_casing_path(cfg)
    casing = read_canonical_casing(casing_path)
    _, casing_pairs = parse_canonical_casing_file(casing_path)
    header, raw_terms = parse_terms_file(terms_path)
    terms = normalize_terms(raw_terms, casing=casing)
    terms_changed = write_terms_file(terms_path, header, raw_terms, casing=casing)
    pat_header, raw_patterns = parse_patterns_file(patterns_path)
    patterns = merge_patterns(raw_patterns, casing=casing)
    patterns_changed = write_patterns_file(
        patterns_path, pat_header, raw_patterns, casing=casing
    )

    accept_path.parent.mkdir(parents=True, exist_ok=True)
    harper_dict_path.parent.mkdir(parents=True, exist_ok=True)

    accept_lines = vale_accept_entries(
        terms, casing=casing, casing_pairs=casing_pairs
    )
    accept_path.write_text(
        "\n".join(accept_lines) + ("\n" if accept_lines else ""),
        encoding="utf-8",
    )
    harper_lines = dictionary_entries(terms, casing_pairs=casing_pairs)
    harper_dict_path.write_text(
        "\n".join(harper_lines) + ("\n" if harper_lines else ""),
        encoding="utf-8",
    )

    typos = typos_path.read_text(encoding="utf-8")
    typos = replace_block(
        typos,
        "# BEGIN GENERATED extend-ignore-re\n",
        "# END GENERATED extend-ignore-re",
        [f'    "{p}",' for p in patterns],
    )
    typos = replace_block(
        typos,
        "# BEGIN GENERATED extend-words\n",
        "# END GENERATED extend-words",
        [f'{w} = "{w}"' for w in terms],
    )
    typos_path.write_text(typos, encoding="utf-8")

    vale_ini_path = root / ".vale.ini"
    vale_ini = vale_ini_path.read_text(encoding="utf-8")
    token_lines = vale_token_ignores(terms, casing=casing)
    token_block_lines = (
        [f"TokenIgnores = {', '.join(token_lines)}"]
        if token_lines
        else []
    )
    if _VALE_INI_BEGIN in vale_ini:
        vale_ini = replace_block(
            vale_ini, _VALE_INI_BEGIN, _VALE_INI_END, token_block_lines
        )
    elif token_block_lines:
        marker = "[*.md]\n"
        if marker in vale_ini:
            body = "\n".join(token_block_lines) + "\n"
            vale_ini = vale_ini.replace(
                marker,
                f"{marker}{_VALE_INI_BEGIN}\n{body}{_VALE_INI_END}\n",
                1,
            )
    vale_ini_path.write_text(vale_ini, encoding="utf-8")

    return (
        accept_path,
        harper_dict_path,
        typos_path,
        terms_path,
        patterns_path,
        terms_changed,
        patterns_changed,
    )


def main() -> int:
    root = repo_root()
    (
        accept_path,
        harper_dict_path,
        typos_path,
        terms_path,
        patterns_path,
        terms_changed,
        patterns_changed,
    ) = sync(root)
    print("Synced:")
    if terms_changed:
        print(f"  {terms_path} (deduped)")
    if patterns_changed:
        print(f"  {patterns_path} (updated)")
    print(f"  {accept_path}")
    print(f"  {harper_dict_path}")
    print(f"  {typos_path}")
    print(f"  {root / '.vale.ini'} (TokenIgnores)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
