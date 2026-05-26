# ocd-nl/pwnpatterns-ci (platform export)

Push this tree to the private **`ocd-nl/pwnpatterns-ci`** repository.

## Export from PwnPatterns (no rsync)

```bash
PWNPATTERNS_CI_USE_EXPORT=1 ./scripts/export-pwnpatterns-ci.sh
# Creates .github/pwnpatterns-ci/ for local CI; copy platform-templates/ + export into the platform repo root.
```

## Layout

- `.github/docs-quality/` — automation, tools (`pwnpatterns-ci`, `docs-dev`, …), `manifest.env`, `styles-base/`
- `.github/tests/` — component tests + fixtures
- `.github/workflows/` — reusable `workflow_call` entrypoints
- `renovate.json` — tool version bumps + `refresh-checksums`

Consumers pin `@<sha>` and keep only `.github/docs-quality/config/`, `.github/platform.ref`, and thin workflows.
