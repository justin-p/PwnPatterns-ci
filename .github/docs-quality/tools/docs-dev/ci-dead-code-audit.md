# CI dead-code audit (docs-quality automation)

Reference grep + plan decisions. Files listed for removal after Python parity is verified.

## Superseded by existing Python (delete)

| File | Replaced by |
|------|-------------|
| `automation/bin/doc-targets.sh` | `pwnpatterns_ci.targets` |
| `automation/bin/run-parallel-prose-lint.sh` | `pwnpatterns_ci.lint_prose` |
| `automation/bin/record-lint-exits.sh` | `pwnpatterns_ci.report.record_lint_exits` |
| `automation/bin/report-lint-failures.sh` | `pwnpatterns_ci.report.report_failures` |
| `automation/bin/refresh-checksums.sh` | `pwnpatterns_ci.checksums` |

## Migrate then delete

| File | Replaced by |
|------|-------------|
| `automation/bin/prose-to-rdjsonl.sh` | `pwnpatterns_ci.rdjsonl` |
| `automation/bin/build-path-index.sh` | `pwnpatterns_ci.paths_util` / `lint_prose.build_path_index` |
| `automation/filters/*.jq` | `pwnpatterns_ci.rdjsonl` |
| `automation/bin/report-docs-quality-reviewdog.sh` | `pwnpatterns_ci.reviewdog` |
| `automation/bin/report-prek-reviewdog.sh` | `pwnpatterns_ci.reviewdog` |
| `automation/lib/reviewdog-invoke.sh` | `pwnpatterns_ci.reviewdog.invoke` |
| `automation/lib/reviewdog-shellcheck.sh` | `pwnpatterns_ci.reviewdog.shellcheck` |
| `automation/lib/ci-steps.sh` | `pwnpatterns_ci.jobs` + `pwnpatterns_ci.e2e` |
| `automation/bin/run-ci-e2e.sh` | `pwnpatterns_ci.e2e` |
| `automation/install/*.sh` | `pwnpatterns_ci.install` |
| `automation/bin/sync-allowlists.sh` | `sync_allowlists` module via CLI |
| `automation/bin/vale-sync.sh` | CLI `vale-sync` |
| `automation/bin/route-grammar-paths.sh` | `grammar-routing/route_grammar_paths.py` via CLI |
| `automation/bin/load-doc-paths.sh` | `pwnpatterns_ci.paths_util` |

## docs-dev only (delete or fold into CLI)

| File | Action |
|------|--------|
| `automation/bin/lint-shell.sh` | Replaced by `actionlint-job` / docs-dev check path |
| `automation/bin/harper-lint-issues.sh` | Maintenance via docs-dev / delete if unused |

## Keep (exempt)

| Path | Reason |
|------|--------|
| `scripts/ensure-platform.sh`, `scripts/consumer-ensure-platform.sh` | Bootstrap |
| `scripts/docs-dev.sh` | Dev entrypoint |
| `.github/lychee/automation/**` | Lychee unchanged this PR |

## Remove

| File | Reason |
|------|--------|
| `scripts/run-with-platform.sh` | Obsolete; use `pwnpatterns-ci sync-allowlists` |
