#!/usr/bin/env bash
# integrate.sh — LE tool for reviewing and merging worker task branches.
#
# Usage:
#   scripts/integrate.sh <id>              # diff review (read-only)
#   scripts/integrate.sh validate <id>     # mark manual task validated (no PR)
#   scripts/integrate.sh merge <id>        # merge PR + regression gate (code tasks)
#
# Requires: git, gh, jq, rg

set -euo pipefail

# shellcheck source=lib/factory-common.sh
source "$(cd "$(dirname "$0")" && pwd)/lib/factory-common.sh"
REPO_ROOT="$(_factory_repo_root)"
_script_dir="$(cd "$(dirname "$0")" && pwd)"
cd "$REPO_ROOT"

MODE="review"
if [[ "${1:-}" == "merge" || "${1:-}" == "validate" ]]; then
  MODE="$1"
  TASK_ID="${2:?usage: $0 ${MODE} <task-id>}"
else
  TASK_ID="${1:?usage: $0 <task-id> | $0 merge <task-id> | $0 validate <task-id>}"
fi

DONE_FILE="factory/tasks/done/${TASK_ID}.md"

[[ -f "$DONE_FILE" ]] || {
  echo "error: task not in done/: ${TASK_ID}" >&2
  exit 1
}

ROLE="$(factory_task_field "$DONE_FILE" role)"
KIND="$(factory_result_kind "$DONE_FILE")"
BRANCH="$(factory_result_field "$DONE_FILE" branch)"
MR="$(factory_result_field "$DONE_FILE" mr)"
STATUS="$(factory_result_field "$DONE_FILE" status)"

WORKTREE="$REPO_ROOT/.worktrees/${ROLE}"

_check_dependency_integration() {
  local dep id done_file st
  while IFS= read -r dep; do
    [[ -n "$dep" ]] || continue
    done_file="factory/tasks/done/${dep}.md"
    [[ -f "$done_file" ]] || {
      echo "error: dependency ${dep} not in done/" >&2
      return 1
    }
    st="$(factory_result_field "$done_file" status)"
    if ! factory_dep_terminal_status "$done_file"; then
      echo "error: dependency ${dep} not integrated (status: ${st:-missing})" >&2
      return 1
    fi
  done < <(awk '
BEGIN { mode=0; fm=0 }
/^---$/ { if (fm) exit; fm=1; next }
!fm { next }
/^depends_on:[[:space:]]*\[\][[:space:]]*$/ { exit }
/^depends_on:[[:space:]]*\[[[:space:]]*[^]]*[[:space:]]*\][[:space:]]*$/ {
  line=$0
  sub(/^depends_on:[[:space:]]*\[/,"",line)
  sub(/\][[:space:]]*$/,"",line)
  n=split(line,a,",")
  for (i=1;i<=n;i++) {
    gsub(/^[[:space:]]+|[[:space:]]+$/,"",a[i])
    gsub(/^["'\'']+|["'\'']+$/,"",a[i])
    if (a[i] != "") print a[i]
  }
  exit
}
/^depends_on:[[:space:]]*$/ { mode=1; next }
mode==1 && /^[[:space:]]*-[[:space:]]/ {
  id=$0
  sub(/^[[:space:]]*-[[:space:]]*/,"",id)
  gsub(/^["'\'']+|["'\'']+$/,"",id)
  print id
  next
}
mode==1 { mode=0 }
' "$DONE_FILE")
}

_mark_status() {
  local new_status="$1"
  local tmp
  tmp="$(mktemp)"
  awk -v ns="$new_status" '
    /^# Result/{in_result=1}
    in_result && /^status:/ && !done { print "status: " ns; done=1; next }
    { print }
  ' "$DONE_FILE" > "$tmp"
  mv "$tmp" "$DONE_FILE"
}

if [[ "$MODE" == "review" ]]; then
  echo "=== integrate: ${TASK_ID} (review, kind=${KIND}) ==="
  echo "Worktree : ${WORKTREE}"
  echo "Branch   : ${BRANCH}"
  echo "PR       : #${MR}"
  echo "Status   : ${STATUS}"
  echo ""

  if [[ "$KIND" == "manual" ]]; then
    echo "--- manual validation task — use 'integrate.sh validate ${TASK_ID}' ---"
    exit 0
  fi

  if [[ -d "$WORKTREE" && -n "$BRANCH" && "$BRANCH" != "none" ]]; then
    echo "--- git log (${BRANCH} vs main) ---"
    git -C "$WORKTREE" log --oneline "main..${BRANCH}" 2>/dev/null || \
      echo "(worktree not on branch ${BRANCH})"
    echo ""
    echo "--- git diff --stat (main...${BRANCH}) ---"
    git -C "$WORKTREE" diff --stat "main...${BRANCH}" 2>/dev/null || true
  else
    echo "(worktree ${WORKTREE} not present or no branch)"
  fi
  exit 0
fi

if [[ "$MODE" == "validate" ]]; then
  if [[ "$KIND" != "manual" ]]; then
    echo "error: validate mode only for manual tasks (kind=${KIND})" >&2
    exit 1
  fi
  _check_dependency_integration
  if [[ "$STATUS" != "passed" && "$STATUS" != "failed" ]]; then
    echo "error: manual task status must be passed or failed before validate (got '${STATUS}')" >&2
    exit 1
  fi
  if ! rg -q '^## Evidence' "$DONE_FILE" 2>/dev/null; then
    echo "error: manual task missing ## Evidence section" >&2
    exit 1
  fi
  _mark_status "validated"
  "$_script_dir/bb-append.sh" "$(printf -- '- **%s %s** ✅ (LE) validated **%s** (manual)' \
    "$(date +%Y-%m-%d)" "$(date +%H:%M:%S)" "$TASK_ID")"
  echo "Task ${TASK_ID} marked status: validated."
  exit 0
fi

# merge mode (code tasks)
if [[ "$KIND" == "manual" ]]; then
  echo "error: manual task — use 'integrate.sh validate ${TASK_ID}' instead of merge" >&2
  exit 1
fi
if [[ "$KIND" == "monitoring" ]]; then
  _mark_status "integrated"
  echo "Task ${TASK_ID} marked status: integrated (monitoring)."
  exit 0
fi

[[ -n "$BRANCH" && "$BRANCH" != "none" ]] || {
  echo "error: code task missing branch in ${DONE_FILE}" >&2
  exit 1
}
[[ -n "$MR" && "$MR" != "0" ]] || {
  echo "error: code task missing mr in ${DONE_FILE}" >&2
  exit 1
}

_check_dependency_integration

if ! command -v jq >/dev/null 2>&1; then
  echo "error: jq required for merge mode" >&2
  exit 1
fi

echo "=== integrate merge: ${TASK_ID} ==="
echo "PR #${MR}  branch ${BRANCH}"

pr_json="$(gh pr view "$MR" --json state,mergeable,mergeStateStatus,statusCheckRollup 2>/dev/null)"
pr_state="$(printf '%s\n' "$pr_json" | jq -r '.state // empty')"
mergeable="$(printf '%s\n' "$pr_json" | jq -r '.mergeable // empty')"
merge_state="$(printf '%s\n' "$pr_json" | jq -r '.mergeStateStatus // empty')"

if [[ "$pr_state" == "MERGED" ]]; then
  echo "PR #${MR} is already merged — updating task status only."
else
  if [[ "$pr_state" != "OPEN" ]]; then
    echo "error: PR #${MR} state is '${pr_state}', expected OPEN or MERGED" >&2
    exit 1
  fi
  if [[ "$mergeable" != "MERGEABLE" && "$merge_state" != "CLEAN" ]]; then
    echo "error: PR #${MR} not mergeable (mergeable='${mergeable}', mergeStateStatus='${merge_state}')" >&2
    exit 1
  fi

  failing_checks="$(printf '%s\n' "$pr_json" | jq -r '
    [.statusCheckRollup[]? | select(.state != "SUCCESS" and .conclusion != "SUCCESS" and .state != null)]
    | length
  ' 2>/dev/null || echo 0)"
  if [[ "${failing_checks:-0}" != "0" ]]; then
    echo "error: PR #${MR} has non-success required checks" >&2
    exit 1
  fi

  # Optional files_in_scope guard
  scope_files=()
  while IFS= read -r line; do
    [[ -n "$line" ]] && scope_files+=("$line")
  done < <(awk '
    /^files_in_scope:/ { mode=1; next }
    mode==1 && /^[[:space:]]*-[[:space:]]/ {
      p=$0; sub(/^[[:space:]]*-[[:space:]]*/,"",p); gsub(/^["'\'' ]+|["'\'' ]+$/,"",p); print p; next
    }
    mode==1 && /^[^[:space:]#-]/ { mode=0 }
  ' "$DONE_FILE")

  if (( ${#scope_files[@]} > 0 )); then
    pr_files="$(gh pr diff "$MR" --name-only 2>/dev/null || true)"
    while IFS= read -r pf; do
      [[ -n "$pf" ]] || continue
      allowed=0
      for sf in "${scope_files[@]}"; do
        if [[ "$pf" == "$sf" || "$pf" == factory/* || "$pf" == docs/* ]]; then
          allowed=1
          break
        fi
      done
      if (( allowed == 0 )); then
        echo "error: PR file out of scope: ${pf}" >&2
        exit 1
      fi
    done <<< "$pr_files"
  fi

  echo "Merging PR #${MR} (squash, delete branch) …"
  gh pr merge "$MR" --squash --delete-branch --yes
  echo "Merged."
fi

if [[ "${FACTORY_SKIP_POST_MERGE:-}" != "1" ]]; then
  git fetch origin main 2>/dev/null || true
  INTEGRATION_WT="$REPO_ROOT/.worktrees/integration-verify"
  if [[ ! -d "$INTEGRATION_WT" ]]; then
    git worktree add "$INTEGRATION_WT" origin/main --detach 2>/dev/null || \
      git worktree add "$INTEGRATION_WT" main --detach 2>/dev/null || true
  fi
  if [[ -d "$INTEGRATION_WT" ]]; then
    git -C "$INTEGRATION_WT" fetch origin main 2>/dev/null || true
    git -C "$INTEGRATION_WT" checkout -f origin/main 2>/dev/null || \
      git -C "$INTEGRATION_WT" checkout -f main 2>/dev/null || true
    if command -v make >/dev/null 2>&1; then
      make -C "$INTEGRATION_WT" lint test 2>/dev/null || {
        echo "error: post-merge regression failed (make lint test)" >&2
        exit 1
      }
    fi
  fi
fi

_mark_status "integrated"

"$_script_dir/bb-append.sh" "$(printf -- '- **%s %s** 🔀 (LE) merged **%s** via #%s → integrated' \
  "$(date +%Y-%m-%d)" "$(date +%H:%M:%S)" "$TASK_ID" "$MR")"

echo "Task ${TASK_ID} marked status: integrated."
