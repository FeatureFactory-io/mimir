#!/usr/bin/env bash
# release.sh — cut a semver GitHub release after all tasks are integrated.
#
# Usage: scripts/release.sh <semver> [--dry-run] [--target-sha <sha>]
#
# Guards:
#   1. semver matches x.y.z (no v prefix in argument)
#   2. pending/ and claimed/ empty
#   3. Every done/*.md has terminal status for its result kind
#   4. main clean, up to date with origin/main
#   5. make lint + make test green (skipped in --dry-run)
#   6. tag v<semver> does not exist
#
# Production promote remains manual: make swap

set -euo pipefail

# shellcheck source=lib/factory-common.sh
source "$(cd "$(dirname "$0")" && pwd)/lib/factory-common.sh"
REPO_ROOT="$(_factory_repo_root)"
cd "$REPO_ROOT"

SEMVER="${1:?usage: $0 <semver> [--dry-run] [--target-sha <sha>]}"
DRY_RUN=0
TARGET_SHA=""
shift || true
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY_RUN=1 ;;
    --target-sha)
      TARGET_SHA="${2:?--target-sha requires a value}"
      shift
      ;;
    *)
      echo "error: unknown argument: $1" >&2
      exit 1
      ;;
  esac
  shift
done

TAG="v${SEMVER}"

if ! [[ "$SEMVER" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "error: semver '${SEMVER}' must match x.y.z (pass without 'v' prefix)" >&2
  exit 1
fi

pending_count="$(find factory/tasks/pending -name '*.md' 2>/dev/null | wc -l | tr -d ' ')"
claimed_count="$(find factory/tasks/claimed -name '*.md' 2>/dev/null | wc -l | tr -d ' ')"

if (( pending_count > 0 )); then
  echo "error: factory/tasks/pending/ is not empty (${pending_count} task(s))" >&2
  exit 1
fi
if (( claimed_count > 0 )); then
  echo "error: factory/tasks/claimed/ is not empty (${claimed_count} task(s))" >&2
  exit 1
fi

not_terminal=()
for f in factory/tasks/done/*.md; do
  [[ -f "$f" ]] || continue
  kind="$(factory_result_kind "$f")"
  status_val="$(factory_result_field "$f" status)"
  ok=0
  case "$kind" in
    code) [[ "$status_val" == "integrated" ]] && ok=1 ;;
    manual) [[ "$status_val" == "validated" || "$status_val" == "passed" ]] && ok=1 ;;
    monitoring) [[ "$status_val" == "integrated" || "$status_val" == "monitoring" ]] && ok=1 ;;
  esac
  if (( ok == 0 )); then
    not_terminal+=("$(basename "$f") (kind=${kind}, status: ${status_val:-missing})")
  fi
done

if (( ${#not_terminal[@]} > 0 )); then
  echo "error: done/ tasks not in terminal status:" >&2
  printf '  %s\n' "${not_terminal[@]}" >&2
  exit 1
fi

if git rev-parse "$TAG" >/dev/null 2>&1; then
  echo "error: git tag '${TAG}' already exists" >&2
  exit 1
fi

current_branch="$(git symbolic-ref --short HEAD 2>/dev/null || echo 'DETACHED')"
if [[ "$current_branch" != "main" ]]; then
  echo "error: must be on 'main' (currently on '${current_branch}')" >&2
  exit 1
fi

if [[ -n "$(git status --porcelain 2>/dev/null)" ]]; then
  echo "error: working tree not clean on main" >&2
  exit 1
fi

git fetch origin main 2>/dev/null || true
local_sha="$(git rev-parse HEAD)"
if git remote get-url origin >/dev/null 2>&1 && git rev-parse origin/main >/dev/null 2>&1; then
  remote_sha="$(git rev-parse origin/main)"
  if [[ "$local_sha" != "$remote_sha" ]]; then
    echo "error: main is not up to date with origin/main" >&2
    echo "  local:  ${local_sha}" >&2
    echo "  remote: ${remote_sha}" >&2
    exit 1
  fi
fi

if [[ -n "$TARGET_SHA" ]]; then
  if [[ "$local_sha" != "$TARGET_SHA" && "${local_sha:0:8}" != "$TARGET_SHA" ]]; then
    echo "error: --target-sha ${TARGET_SHA} does not match HEAD ${local_sha}" >&2
    exit 1
  fi
fi

if [[ $DRY_RUN -eq 0 ]]; then
  if command -v make >/dev/null 2>&1; then
    make lint test || {
      echo "error: release gate failed (make lint test)" >&2
      exit 1
    }
  fi
fi

echo "release.sh: all guards passed for ${SEMVER} (tag ${TAG})"

if [[ $DRY_RUN -eq 1 ]]; then
  echo "DRY RUN — would execute:"
  echo "  git tag ${TAG}"
  echo "  git push origin ${TAG}"
  echo "  gh release create ${TAG} --generate-notes"
  exit 0
fi

echo "Tagging and pushing …"
git tag "$TAG"
git push origin "$TAG"
gh release create "$TAG" --generate-notes

"$REPO_ROOT/scripts/bb-append.sh" "$(printf -- '- **%s %s** 🚀 (LE) cut release **%s** — CI deploy to idle EB starting' \
  "$(date +%Y-%m-%d)" "$(date +%H:%M:%S)" "$TAG")"

echo ""
echo "Release ${TAG} published. GitHub Actions will test, build, and deploy to idle EB."
echo "After staging review: make swap"
