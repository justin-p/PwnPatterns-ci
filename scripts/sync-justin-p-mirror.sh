#!/usr/bin/env bash
# Sync ocd-nl/PwnPatterns-ci -> justin-p/PwnPatterns-ci (public mirror).
#
# ocd-nl/main is canonical. This script fast-forwards the personal mirror to the
# same tree, then applies CI slug rewrites so consumers can checkout the public repo.
#
# Run from either clone:
#   - Org:  /path/to/github_ocdnl/PwnPatterns-ci  (needs remote "justin-p")
#   - Personal: /path/to/github/PwnPatterns-ci   (needs remote "ocd-nl")
#
# Environment:
#   ORG_REMOTE=ocd-nl          upstream remote name
#   PERSONAL_REMOTE=justin-p   mirror push remote (or "origin" on personal clone)
#   SYNC_BRANCH=main           branch to sync
#   ORG_SLUG=ocd-nl/PwnPatterns-ci
#   MIRROR_SLUG=justin-p/PwnPatterns-ci
#   PUSH=1                     set to 0 for dry-run (no push)
#   FORCE_PUSH=0               set to 1 for git push --force-with-lease (required when upstream
#                              main was rebased and mirror main is not a strict ancestor).
set -euo pipefail

ORG_REMOTE="${ORG_REMOTE:-ocd-nl}"
PERSONAL_REMOTE="${PERSONAL_REMOTE:-justin-p}"
SYNC_BRANCH="${SYNC_BRANCH:-main}"
ORG_SLUG="${ORG_SLUG:-ocd-nl/PwnPatterns-ci}"
MIRROR_SLUG="${MIRROR_SLUG:-justin-p/PwnPatterns-ci}"
PUSH="${PUSH:-1}"
FORCE_PUSH="${FORCE_PUSH:-0}"

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "${REPO_ROOT}"

MIRROR_PATHS=(
  .github/actions/checkout-platform/action.yml
  .github/docs-quality/tools/pwnpatterns-ci/src/pwnpatterns_ci/pin.py
  .github/docs-quality/tools/pwnpatterns-ci/tests/test_pin.py
  .github/workflows/ci-e2e.yml
  .github/workflows/docs-quality-actionlint.yml
  .github/workflows/docs-quality-lychee.yml
  .github/workflows/docs-quality.yml
  .github/workflows/link-check-dashboard.yml
)

resolve_remotes() {
  if git remote get-url "${ORG_REMOTE}" >/dev/null 2>&1; then
    UPSTREAM="${ORG_REMOTE}"
  elif git remote get-url origin 2>/dev/null | grep -q 'ocd-nl/PwnPatterns-ci'; then
    ORG_REMOTE=origin
    UPSTREAM=origin
  else
    echo "sync-justin-p-mirror: add remote ${ORG_REMOTE} -> https://github.com/ocd-nl/PwnPatterns-ci.git" >&2
    exit 1
  fi

  if git remote get-url "${PERSONAL_REMOTE}" >/dev/null 2>&1; then
    :
  elif git remote get-url origin 2>/dev/null | grep -q 'justin-p/PwnPatterns-ci'; then
    PERSONAL_REMOTE=origin
  else
    echo "sync-justin-p-mirror: add remote ${PERSONAL_REMOTE} -> https://github.com/justin-p/PwnPatterns-ci.git" >&2
    exit 1
  fi
}

apply_mirror_slug() {
  local f
  for f in "${MIRROR_PATHS[@]}"; do
    if [ ! -f "${f}" ]; then
      echo "sync-justin-p-mirror: missing ${f}" >&2
      exit 1
    fi
    sed -i "s|${ORG_SLUG}|${MIRROR_SLUG}|g" "${f}"
  done
}

resolve_remotes
git fetch "${UPSTREAM}" "${SYNC_BRANCH}"
git fetch "${PERSONAL_REMOTE}" "${SYNC_BRANCH}" 2>/dev/null || true

git checkout -B "${SYNC_BRANCH}" "${UPSTREAM}/${SYNC_BRANCH}"

apply_mirror_slug

# Only compare mirror-managed paths; unrelated changes (e.g. editing this script) must not
# trip the slug commit branch or leak into "nothing to commit" failures from set -e.
if git diff --quiet HEAD -- "${MIRROR_PATHS[@]}"; then
  MIRROR_COMMIT="$(git rev-parse HEAD)"
  echo "Mirror tree matches ${UPSTREAM}/${SYNC_BRANCH} (slug already applied)."
else
  git add "${MIRROR_PATHS[@]}"
  git commit -m "$(cat <<EOF
chore(mirror): sync from ${ORG_SLUG} with public CI checkout slug

Automated mirror commit on top of ${UPSTREAM}/${SYNC_BRANCH}.
Consumers pin this SHA on ${MIRROR_SLUG}.
EOF
)"
  MIRROR_COMMIT="$(git rev-parse HEAD)"
  echo "Created mirror commit ${MIRROR_COMMIT}"
fi

if [ "${PUSH}" = "1" ]; then
  push_args=("${PERSONAL_REMOTE}" "HEAD:${SYNC_BRANCH}")
  if [ "${FORCE_PUSH}" = "1" ]; then
    push_args+=(--force-with-lease)
  fi
  if git push "${push_args[@]}"; then
    echo "Pushed ${MIRROR_COMMIT} to ${PERSONAL_REMOTE}/${SYNC_BRANCH}"
  else
    echo "sync-justin-p-mirror: push failed (mirror may have diverged). Retry with FORCE_PUSH=1." >&2
    exit 1
  fi
else
  echo "Dry-run: not pushing (set PUSH=1 to push)."
fi

echo "platform.ref pin for consumers: ${MIRROR_COMMIT}"
