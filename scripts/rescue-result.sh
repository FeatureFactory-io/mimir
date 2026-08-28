#!/usr/bin/env bash
# rescue-result.sh — auto-fill an empty # Result block from git state (code tasks only).
#
# Usage: scripts/rescue-result.sh <task-id>
#
# Never overwrites valid manual-validation sentinels (branch none, mr 0).

set -euo pipefail

# shellcheck source=lib/factory-common.sh
source "$(cd "$(dirname "$0")" && pwd)/lib/factory-common.sh"
REPO_ROOT="$(_factory_repo_root)"
cd "$REPO_ROOT"

TASK_ID="${1:?usage: $0 <task-id>}"
CLAIMED="factory/tasks/claimed/${TASK_ID}.md"
BLOCKED="factory/tasks/blocked/${TASK_ID}.md"

if [[ -f "$CLAIMED" ]]; then
  TARGET="$CLAIMED"
elif [[ -f "$BLOCKED" ]]; then
  TARGET="$BLOCKED"
else
  echo "rescue-result: task not in claimed/ or blocked/: ${TASK_ID}" >&2
  exit 1
fi

ROLE="$(factory_task_field "$TARGET" role)"
if [[ "$ROLE" == "manual-tester" ]]; then
  echo "rescue-result: skipping manual-tester task ${TASK_ID}"
  exit 0
fi

if rg -q '^# Result' "$TARGET" 2>/dev/null; then
  kind="$(factory_result_kind "$TARGET")"
  if [[ "$kind" == "manual" ]]; then
    echo "rescue-result: ${TASK_ID} has manual validation result — skipping"
    exit 0
  fi
  _status="$(factory_result_field "$TARGET" status)"
  _branch="$(factory_result_field "$TARGET" branch)"
  _mr="$(factory_result_field "$TARGET" mr)"
  _sha="$(factory_result_field "$TARGET" commit_sha)"
  if [[ -n "$_status" && -n "$_branch" && -n "$_mr" && -n "$_sha" ]]; then
    echo "rescue-result: ${TASK_ID} already has complete # Result block — skipping"
    exit 0
  fi
  tmpfile="$(mktemp)"
  awk '/^# Result/{exit} {print}' "$TARGET" > "$tmpfile"
  mv "$tmpfile" "$TARGET"
fi

BRANCH="$(factory_task_field "$TARGET" branch)"
if [[ -z "$BRANCH" || "$BRANCH" == "none" ]]; then
  echo "rescue-result: no branch: field in ${TARGET}" >&2
  exit 1
fi

COMMIT_SHA="$(git ls-remote origin "$BRANCH" 2>/dev/null | awk '{print $1}' | cut -c1-8 || true)"

MR="0"
if command -v gh >/dev/null 2>&1 && command -v jq >/dev/null 2>&1; then
  MR="$(gh pr list --head "$BRANCH" --json number -q '.[0].number // 0' 2>/dev/null || echo 0)"
fi

STATUS="rescued"
[[ -n "$COMMIT_SHA" ]] || COMMIT_SHA="unknown"

printf '\n# Result\n\nstatus: %s\nbranch: %s\nmr: %s\ncommit_sha: %s\n\nAuto-filled by rescue-result.sh.\n' \
  "$STATUS" "$BRANCH" "$MR" "$COMMIT_SHA" >> "$TARGET"

echo "rescue-result: ${TASK_ID} → branch=${BRANCH} pr=#${MR} sha=${COMMIT_SHA}"

"$REPO_ROOT/scripts/factory-git.sh" "factory: rescue ${TASK_ID} (auto-filled Result block)" "$TARGET" 2>/dev/null || true
