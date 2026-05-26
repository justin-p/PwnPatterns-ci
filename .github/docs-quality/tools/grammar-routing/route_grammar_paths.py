#!/usr/bin/env python3
"""Route documentation paths to grammar tools from language-tools.yml and frontmatter."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from lt_preprocess import FRONTMATTER_RE

DEFAULT_CONFIG: dict[str, Any] = {
    "default_language": "en",
    "fallback_tool": "languagetool",
    "grammar_tools": {"en": "harper", "nl": "languagetool"},
    "spelling_tools": {"en": "typos", "nl": "textlint"},
    "spelling_fallback_tool": "typos",
    "languagetool_codes": {"nl": "nl", "fr": "fr", "de": "de-DE", "en": "en-US"},
    "languagetool_enabled": True,
    "grammar_from_frontmatter": True,
    "grammar_smoke_paths": [".github/tests/fixtures/nl-languagetool-smoke.md"],
}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def load_language_tools_config(path: Path) -> dict[str, Any]:
    cfg = {k: (v.copy() if isinstance(v, dict) else v) for k, v in DEFAULT_CONFIG.items()}
    if isinstance(cfg.get("grammar_smoke_paths"), list):
        cfg["grammar_smoke_paths"] = list(cfg["grammar_smoke_paths"])
    if not path.is_file():
        return cfg

    section: str | None = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        if line.endswith(":") and not line.startswith(" "):
            key = line[:-1].strip()
            if key in ("grammar_tools", "spelling_tools", "languagetool_codes"):
                section = key
                cfg.setdefault(key, {})
            elif key == "grammar_smoke_paths":
                section = key
                cfg["grammar_smoke_paths"] = []
            else:
                section = None
            continue
        if section == "grammar_smoke_paths" and line.startswith("  - "):
            cfg["grammar_smoke_paths"].append(line[4:].strip().strip("\"'"))
            continue
        # Top-level scalars (column 0); ends an open grammar_tools / languagetool_codes section.
        if ":" in line and not line.startswith(" "):
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip().strip("\"'")
            section = None
            if key in ("languagetool_enabled", "grammar_from_frontmatter"):
                cfg[key] = value.lower() in ("true", "yes", "1")
            elif key in ("default_language", "fallback_tool", "spelling_fallback_tool"):
                cfg[key] = value
            continue
        if section and line.startswith("  ") and ":" in line:
            key, value = line.split(":", 1)
            cfg[section][key.strip()] = value.strip().strip("\"'")
    return cfg


def _platform_grammar_smoke_rel(repo: Path) -> str | None:
    for rel in (
        ".github/pwnpatterns-ci/.github/tests/fixtures/nl-languagetool-smoke.md",
        ".github/tests/fixtures/nl-languagetool-smoke.md",
    ):
        if (repo / rel).is_file():
            return rel
    return None


def merge_lint_paths(paths: list[str], cfg: dict[str, Any], repo: Path) -> list[str]:
    """Union explicit lint targets with configured grammar smoke fixtures."""
    merged: list[str] = []
    seen: set[str] = set()
    smoke_paths: list[str] = []
    smoke_extra: str | None = None
    if cfg.get("languagetool_enabled", True):
        smoke_extra = _platform_grammar_smoke_rel(repo)
        smoke_paths = list(cfg.get("grammar_smoke_paths") or [])
        if smoke_extra and smoke_extra not in smoke_paths:
            smoke_paths.append(smoke_extra)
    for rel in [*paths, *smoke_paths]:
        rel = rel.strip()
        if not rel or rel in seen:
            continue
        if not (repo / rel).is_file():
            continue
        seen.add(rel)
        merged.append(rel)
    return merged


def _read_frontmatter_field(file_path: Path, repo: Path, field: str) -> str | None:
    full = repo / file_path if not file_path.is_absolute() else file_path
    if not full.is_file():
        return None
    text = full.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(text)
    if not match:
        return None
    prefix = f"{field}:"
    for line in match.group(1).split("\n"):
        stripped = line.strip()
        if stripped.startswith(prefix):
            return stripped.split(":", 1)[1].strip().strip("\"'")
    return None


def read_frontmatter_language(file_path: Path, repo: Path) -> str | None:
    return _read_frontmatter_field(file_path, repo, "language")


def read_grammar_language(file_path: Path, repo: Path, cfg: dict[str, Any]) -> str | None:
    """Language used for grammar-tool routing (may differ from catalog ``language``)."""
    if cfg.get("grammar_from_frontmatter", True):
        return read_frontmatter_language(file_path, repo)
    return _read_frontmatter_field(file_path, repo, "grammar_language")


def grammar_tool_for_language(lang: str | None, cfg: dict[str, Any]) -> str:
    tools: dict[str, str] = cfg.get("grammar_tools") or {}
    default_lang = str(cfg.get("default_language") or "en")
    fallback = str(cfg.get("fallback_tool") or "languagetool")
    code = (lang or default_lang).strip().lower()
    if code in tools:
        return str(tools[code])
    return fallback


def spelling_tool_for_language(lang: str | None, cfg: dict[str, Any]) -> str:
    tools: dict[str, str] = cfg.get("spelling_tools") or {}
    default_lang = str(cfg.get("default_language") or "en")
    fallback = str(cfg.get("spelling_fallback_tool") or "typos")
    code = (lang or default_lang).strip().lower()
    if code in tools:
        return str(tools[code])
    return fallback


def languagetool_code(lang: str, cfg: dict[str, Any]) -> str:
    codes: dict[str, str] = cfg.get("languagetool_codes") or {}
    return str(codes.get(lang, lang))


def route_paths(
    paths: list[str],
    cfg: dict[str, Any],
    repo: Path,
) -> dict[str, Any]:
    typos: list[str] = []
    textlint: list[str] = []
    harper: list[str] = []
    languagetool: list[dict[str, str]] = []
    none_paths: list[str] = []
    lt_enabled = bool(cfg.get("languagetool_enabled", True))

    for rel in paths:
        rel = rel.strip()
        if not rel:
            continue
        lang = read_grammar_language(Path(rel), repo, cfg)
        spelling_tool = spelling_tool_for_language(lang, cfg)
        if spelling_tool == "textlint":
            textlint.append(rel)
        else:
            typos.append(rel)
        tool = grammar_tool_for_language(lang, cfg)
        if tool == "harper":
            harper.append(rel)
        elif tool == "languagetool":
            if lt_enabled:
                languagetool.append(
                    {
                        "path": rel,
                        "language": lang or str(cfg.get("default_language") or "en"),
                        "lt_code": languagetool_code(
                            (lang or str(cfg.get("default_language") or "en")).lower(),
                            cfg,
                        ),
                    }
                )
            else:
                none_paths.append(rel)
        else:
            none_paths.append(rel)

    return {
        "typos": typos,
        "textlint": textlint,
        "harper": harper,
        "languagetool": languagetool,
        "none": none_paths,
    }


def write_route_outputs(log_dir: Path, routed: dict[str, Any]) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    typos = routed.get("typos") or []
    textlint = routed.get("textlint") or []
    (log_dir / "spelling-typos-paths.lst").write_text(
        "\n".join(typos) + ("\n" if typos else ""),
        encoding="utf-8",
    )
    (log_dir / "spelling-textlint-paths.lst").write_text(
        "\n".join(textlint) + ("\n" if textlint else ""),
        encoding="utf-8",
    )
    harper = routed.get("harper") or []
    lt_rows = routed.get("languagetool") or []
    (log_dir / "grammar-harper-paths.lst").write_text(
        "\n".join(harper) + ("\n" if harper else ""),
        encoding="utf-8",
    )
    lines = [f"{row['path']}\t{row['lt_code']}" for row in lt_rows]
    (log_dir / "grammar-languagetool.tsv").write_text(
        "\n".join(lines) + ("\n" if lines else ""),
        encoding="utf-8",
    )
    (log_dir / "grammar-route.json").write_text(
        json.dumps(routed, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Route docs to grammar tools by language")
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="language-tools.yml (default: .github/docs-quality/config/language-tools.yml)",
    )
    parser.add_argument(
        "--log-dir",
        type=Path,
        required=True,
        help="Directory for grammar-harper-paths.lst and grammar-languagetool.tsv",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="Repository root (default: auto-detect)",
    )
    parser.add_argument("paths", nargs="*", help="Documentation paths relative to repo root")
    args = parser.parse_args()

    root = args.repo_root or repo_root()
    config_path = args.config or (
        root / ".github/docs-quality/config/language-tools.yml"
    )
    cfg = load_language_tools_config(config_path)
    paths = args.paths
    if not paths and not sys.stdin.isatty():
        paths = [ln.strip() for ln in sys.stdin if ln.strip()]

    paths = merge_lint_paths(paths, cfg, root)
    if not paths:
        print("route_grammar_paths: no lint targets", file=sys.stderr)
        return 1

    log_dir = args.log_dir
    if not log_dir.is_absolute():
        log_dir = (root / log_dir).resolve()

    routed = route_paths(paths, cfg, root)
    write_route_outputs(log_dir, routed)

    print(
        f"grammar route: harper={len(routed['harper'])} "
        f"spelling_typos={len(routed['typos'])} "
        f"spelling_textlint={len(routed['textlint'])} "
        f"languagetool={len(routed['languagetool'])} "
        f"none={len(routed['none'])}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
