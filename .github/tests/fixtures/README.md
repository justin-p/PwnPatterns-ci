# CI and docs-quality fixtures

Test inputs for component tests and grammar-routing smoke checks. Not production pattern docs.

| File | Purpose |
| --- | --- |
| [`metadata-invalid.md`](metadata-invalid.md) | Invalid frontmatter for `verify-metadata` E2E |
| [`nl-languagetool-smoke.md`](nl-languagetool-smoke.md) | `language: nl` sample; always merged into prose lint via [`language-tools.yml`](../docs-quality/config/language-tools.yml) `grammar_smoke_paths` |
| [`harper/sample.json`](harper/sample.json) | Harper JSON for jq filter tests |
| [`rumdl/sample.json`](rumdl/sample.json) | rumdl JSON for jq filter tests |
| [`lychee/report-with-403.json`](lychee/report-with-403.json) | Lychee 403 filter tests |

**Manual LanguageTool error test:** change the Beschrijving line to `Dit is een fout tekst.`, then:

```bash
export PATH="${PWD}/.local/doc-linters:${PATH}"
languagetool-cli -l nl --json .github/tests/fixtures/nl-languagetool-smoke.md
```
