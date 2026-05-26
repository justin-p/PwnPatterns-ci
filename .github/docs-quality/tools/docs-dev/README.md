# docs-dev (Python)

Local documentation quality CLI for PwnPatterns.

## Run

From the repository root:

```bash
./scripts/ensure-platform.sh             # pattern repo bootstrap (vendored script)
./.github/pwnpatterns-ci/scripts/docs-dev.sh                    # Textual TUI (setup, check, tools submenu)
./.github/pwnpatterns-ci/scripts/docs-dev.sh --changed          # TUI opens “lint changed docs” directly
./.github/pwnpatterns-ci/scripts/docs-dev.sh --no-ui            # CLI check (all docs)
./.github/pwnpatterns-ci/scripts/docs-dev.sh --no-ui --changed --format json
./.github/pwnpatterns-ci/scripts/docs-dev.sh web                # same TUI in a browser (textual-serve)
./.github/pwnpatterns-ci/scripts/docs-dev.sh check              # CLI: lint changed docs vs origin/main
./.github/pwnpatterns-ci/scripts/docs-dev.sh setup              # CLI: install pinned tools + prek hooks
```

**Web UI:** run `./scripts/docs-dev.sh web`, open http://127.0.0.1:8765/, click the **docs-dev** tile to start the session. Override bind address with `--host` / `--port` or `DOCS_DEV_WEB_HOST` / `DOCS_DEV_WEB_PORT`.

On **Check Changed** / **Check All**, use the **file filter** (or press **/**) for fuzzy search over paths (e.g. `prometheus`, `prom exp`). Select a file, then a finding, and press **Open file [e]** (or the button under the findings list) to open the markdown editor on the right at that line. The editor uses **Bearded Theme Feat-gold-d-raynh** syntax colors (YAML frontmatter, headings, fenced blocks, strings, and inline code) aligned with the VS Code/Cursor Bearded Bear theme. When you close the editor (**Close** / **esc** / **q**), switch files, run a new check, or go Home, you are prompted to **Save**, **Don't save**, or **Cancel**. **Ctrl+S** saves without closing. Findings that can be allowlisted are marked with `★`. Press **Allowlist [a]** to append a term and sync. **Recheck file [c]** re-lints the selected file; **Run check [r]** re-checks all.

Allowlists, dual-valid casing (e.g. `certipy` vs `Certipy`), and sync behavior are documented in the repository [README.md](../../../../README.md#dual-valid-casing-cli-tools-and-product-names) (Documentation quality section).

The shell wrapper accepts commands (`check`, `fix`, `setup`, `web`) and global flags (`--no-ui`, `--format`, `--changed`, `--fix`, `--skip-lychee`, `--skip-actionlint`). **Doctor**, **sync**, **e2e**, and other maintenance commands live in the TUI menu (Setup on the home screen; checksums, doctor, e2e, sync, vale-sync under **Tools**).

## Flags

| Flag | Purpose |
|------|---------|
| `--no-ui` | Force CLI (no Textual) |
| `--format json` | Machine-readable report (`schema_version: 1`) |
| `--format plain` | One finding per line |
| `--fix` | typos, rumdl, prek fixers, shfmt; then re-check |
| `--changed` | Only `docs/**/*.md` changed vs `origin/main` |
| `--skip-lychee` | Skip offline lychee |
| `--skip-actionlint` | Skip workflow lint |

## JSON schema

```json
{
  "schema_version": 1,
  "command": "check",
  "options": {},
  "summary": { "passed": false, "steps": [] },
  "files": [{ "path": "docs/....md", "findings": [] }]
}
```

## Tests (uv + TDD)

From this directory, use **uv** for the environment (do not activate `.venv` manually):

```bash
cd .github/docs-quality/tools/docs-dev
uv sync --group dev          # install runtime + dev deps from uv.lock
uv run pytest --co           # list collected tests
uv run pytest                # all tests
uv run pytest -x             # stop on first failure
uv run pytest -k "vale"      # by name pattern
uv run pytest --cov=docs_dev # coverage (src package)
```

**TUI e2e** — Textual Pilot; runners mocked in `conftest.py` (offline, no real linters):

```bash
uv run pytest tests/test_tui_e2e.py -v
```

**TDD cycle** for new behavior: one failing test → minimal implementation → refactor → `uv run pytest`. Keep mocks at boundaries (linters, subprocess, network); unit tests use fixtures under `tests/fixtures/`.

Commit `pyproject.toml` and `uv.lock` together when dependencies change.

## CI

[`.github/workflows/docs-quality-tools.yml`](../../../../workflows/docs-quality-tools.yml) runs `pytest` for **docs-dev**, **sync-allowlists**, and **verify-metadata**, plus component E2E smoke (invalid metadata → rdjsonl, allowlist sync import). Triggers on `.github/docs-quality/tools/**` changes.

Documentation linting in PRs still uses bash ([`ci-steps.sh`](../../automation/lib/ci-steps.sh)) via [Documentation quality](../../../../workflows/docs-quality.yml); `docs-dev` is the local/TUI wrapper around that stack.
