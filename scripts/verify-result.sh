#!/usr/bin/env bash
# verify-result.sh — verify a claimed task's # Result block before moving to done/.
#
# Result kinds:
#   code       — branch + mr + commit_sha; remote branch + PR required
#   manual     — manual-tester: branch none, mr 0, commit_sha none, evidence required
#   monitoring — release-engineer pipeline watch: mr 0, status monitoring
#
# Exit 0 on success. Exit 2 on failure (reason:<field>: <detail> on stderr).

set -euo pipefail

# shellcheck source=lib/factory-common.sh
source "$(cd "$(dirname "$0")" && pwd)/lib/factory-common.sh"
REPO_ROOT="$(_factory_repo_root)"
cd "$REPO_ROOT"

TASK_ID="${1:?usage: $0 <task-id>}"
CLAIMED="factory/tasks/claimed/${TASK_ID}.md"

[[ -f "$CLAIMED" ]] || {
  echo "error: task not in claimed/: ${TASK_ID}" >&2
  exit 1
}

if ! rg -q '^# Result' "$CLAIMED" 2>/dev/null; then
  echo "reason:result_block: no '# Result' section in ${CLAIMED}" >&2
  exit 2
fi

STATUS="$(factory_result_field "$CLAIMED" status)"
BRANCH="$(factory_result_field "$CLAIMED" branch)"
MR="$(factory_result_field "$CLAIMED" mr)"
COMMIT_SHA="$(factory_result_field "$CLAIMED" commit_sha)"
KIND="$(factory_result_kind "$CLAIMED")"

[[ -n "$STATUS" ]] || { echo "reason:status: field 'status' is empty" >&2; exit 2; }

if [[ "$KIND" == "monitoring" ]]; then
  echo "verify-result: ${TASK_ID} OK (monitoring task, mr=0)"
  exit 0
fi

if [[ "$KIND" == "manual" ]]; then
  if [[ "$STATUS" != "passed" && "$STATUS" != "failed" ]]; then
    echo "reason:status: manual task status must be passed or failed, got '${STATUS}'" >&2
    exit 2
  fi
  if ! rg -q '^## Evidence' "$CLAIMED" 2>/dev/null; then
    echo "reason:evidence: manual task missing '## Evidence' section" >&2
    exit 2
  fi
  echo "verify-result: ${TASK_ID} OK (manual validation, status=${STATUS})"
  exit 0
fi

# code task
[[ -n "$BRANCH" ]] || { echo "reason:branch: field 'branch' is empty" >&2; exit 2; }
[[ -n "$MR" ]]     || { echo "reason:mr: field 'mr' is empty" >&2; exit 2; }
[[ -n "$COMMIT_SHA" ]] || { echo "reason:commit_sha: field 'commit_sha' is empty" >&2; exit 2; }

if ! git ls-remote --exit-code origin "$BRANCH" >/dev/null 2>&1; then
  echo "reason:branch: branch '${BRANCH}' not found on origin" >&2
  exit 2
fi

if ! command -v jq >/dev/null 2>&1; then
  echo "reason:mr: jq not found — install via: brew install jq" >&2
  exit 2
fi

pr_state="$(gh pr view "$MR" --json state -q .state 2>/dev/null || true)"
if [[ -z "$pr_state" ]]; then
  echo "reason:mr: could not fetch PR #${MR} state (gh pr view failed)" >&2
  exit 2
fi
if [[ "$pr_state" != "OPEN" && "$pr_state" != "MERGED" ]]; then
  echo "reason:mr: PR #${MR} state is '${pr_state}', expected OPEN or MERGED" >&2
  exit 2
fi

echo "verify-result: ${TASK_ID} OK (branch=${BRANCH} pr=#${MR} status=${STATUS})"
exit 0
