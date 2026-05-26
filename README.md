# ocd-nl/pwnpatterns-ci (platform export)

Push this tree to the private **`ocd-nl/pwnpatterns-ci`** repository.

## Scripts (platform)

| Script | Purpose |
|--------|---------|
| [`scripts/ensure-platform.sh`](scripts/ensure-platform.sh) | Clone/checkout this repo into a consumer’s `.github/pwnpatterns-ci/` (set `REPO_ROOT` to the pattern repo) |
| [`scripts/run-with-platform.sh`](scripts/run-with-platform.sh) | Run automation under `.github/docs-quality/automation/bin/` |
| [`scripts/docs-dev.sh`](scripts/docs-dev.sh) | docs-dev TUI / CLI |
| [`scripts/consumer-ensure-platform.sh`](scripts/consumer-ensure-platform.sh) | **Vendored** into pattern repos as `scripts/ensure-platform.sh` |

Pattern repos keep only `scripts/ensure-platform.sh` (copy of `consumer-ensure-platform.sh`), then run:

```bash
./scripts/ensure-platform.sh
./.github/pwnpatterns-ci/scripts/docs-dev.sh
```

## Layout

- `.github/docs-quality/` — automation, tools (`pwnpatterns-ci`, `docs-dev`, …), `manifest.env`, `styles-base/`
- `.github/actions/checkout-platform/` — composite action: `actions/checkout` of this repo at `platform_ref`
- `.github/tests/` — component tests + fixtures
- `.github/workflows/` — reusable `workflow_call` entrypoints (use `checkout-platform`, not export)
- `renovate.json` — tool version bumps + `refresh-checksums`

Consumers pin `@<sha>` in workflow `uses:` lines and `.github/platform.ref`, and keep only `.github/docs-quality/config/`, thin workflows, and content (`docs/`, `styles/`).

## GitHub org setup (required for CI)

1. **`ocd-nl/pwnpatterns-ci`** → Settings → Actions → General → **Access**: allow reusable workflows and actions from repositories in the **ocd-nl** organization.
2. **Organization** → Settings → Actions → General: allow workflows to **access repositories in the organization** (so `GITHUB_TOKEN` can run `actions/checkout` on the private platform repo).
3. If checkout still fails with “repository not found”, add an org or repo secret **`PWNPATTERNS_CI_CHECKOUT_TOKEN`** (fine-scoped PAT with `contents:read` on `pwnpatterns-ci`). Reusable workflows accept it via `secrets: inherit`.
