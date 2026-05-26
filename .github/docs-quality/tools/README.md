# docs-quality tools

Python packages used by documentation CI and `docs-dev`:

| Package | Role | CI |
|---------|------|-----|
| [docs-dev](docs-dev/) | Local TUI/CLI check orchestration | `pytest` (unit + TUI e2e) |
| [sync-allowlists](sync-allowlists/) | Regenerate Vale/typos/Harper allowlists from `terms.txt` | `pytest` + component E2E |
| [verify-metadata](verify-metadata/) | Pattern frontmatter validation → rdjsonl | `pytest` + component E2E |
| [grammar-routing](grammar-routing/) | Harper vs LanguageTool routing + LT batch runner | `pytest` + component E2E |
| [pwnpatterns-ci](pwnpatterns-ci/) | Python CI orchestration (`pwnpatterns-ci` CLI) | `pytest` + platform export |

Workflow: [`.github/workflows/docs-quality-tools.yml`](../../workflows/docs-quality-tools.yml) — matrix `pytest` on all three packages, then component E2E (`DOCS_QUALITY_TOOLS_E2E_ONLY=1`).

Full `.github/**` machinery (jq filters, `run-ci-e2e.sh`) still runs in [CI E2E](../../workflows/ci-e2e.yml).
