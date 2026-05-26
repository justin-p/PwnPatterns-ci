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
- `.github/actions/checkout-platform/` — optional legacy composite; reusable workflows inline `actions/checkout` instead (one fewer SHA pin)
- `.github/tests/` — component tests + fixtures
- `.github/workflows/` — reusable `workflow_call` entrypoints (clone platform via `actions/checkout` + `platform_ref`, not export)
- `renovate.json` — tool version bumps + `refresh-checksums`

Consumers pin `@<sha>` in workflow `uses:` lines and `.github/platform.ref`, and keep only `.github/docs-quality/config/`, thin workflows, and content (`docs/`, `styles/`).

## GitHub org setup (required for CI)

1. **`ocd-nl/pwnpatterns-ci`** → Settings → Actions → General → **Access**: allow reusable workflows and actions from repositories in the **ocd-nl** organization.
2. **Organization** → Settings → Actions → General: allow workflows to **access repositories in the organization** (so `GITHUB_TOKEN` can run `actions/checkout` on the private platform repo).
3. If checkout still fails with “repository not found”, add an org or repo secret **`PWNPATTERNS_CI_CHECKOUT_TOKEN`** (fine-scoped PAT with `contents:read` on `pwnpatterns-ci`). Reusable workflows accept it via `secrets: inherit`.

## Public mirror (`justin-p/PwnPatterns-ci`)

Forking is disabled on the org repo. A public mirror at [justin-p/PwnPatterns-ci](https://github.com/justin-p/PwnPatterns-ci) lets consumer CI use reusable workflows without org checkout access. **`main` on the org repo is canonical**; the mirror is `ocd-nl/main` plus a single commit that rewrites CI checkout/pin slugs to `justin-p/PwnPatterns-ci`.

After merging to `ocd-nl/main`, refresh the mirror:

```bash
# From the personal clone (_git/github/PwnPatterns-ci):
git remote add ocd-nl https://github.com/ocd-nl/PwnPatterns-ci.git   # once
./scripts/sync-justin-p-mirror.sh
```

Or from this org clone (add `justin-p` remote once):

```bash
git remote add justin-p https://github.com/justin-p/PwnPatterns-ci.git
PERSONAL_REMOTE=justin-p ./scripts/sync-justin-p-mirror.sh
```

The script prints the mirror commit SHA to pin in consumer `.github/platform.ref`. Scheduled sync on the personal repo uses `OCNDNL_PWNPATTERNS_CI_READ_TOKEN` (PAT with `contents:read` on this repo).
