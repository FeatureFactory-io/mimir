#!/usr/bin/env bash
# claim.sh — atomically move a pending task to claimed if role and deps match.
#
# Dependencies must be in done/ with terminal status (integrated, validated, passed, monitoring).

set -euo pipefail

# shellcheck source=lib/factory-common.sh
source "$(cd "$(dirname "$0")" && pwd)/lib/factory-common.sh"
REPO_ROOT="$(_factory_repo_root)"
cd "$REPO_ROOT"

TASK_ID="${1:?usage: $0 <task-id> <role>}"
ROLE="${2:?usage: $0 <task-id> <role>}"

PENDING="factory/tasks/pending/${TASK_ID}.md"
CLAIMED="factory/tasks/claimed/${TASK_ID}.md"

[[ -f "$PENDING" ]] || exit 1

file_role="$(factory_task_field "$PENDING" role)"
[[ -n "$file_role" ]] || exit 1
[[ "$file_role" == "$ROLE" ]] || exit 1

deps=()
while IFS= read -r line; do
  [[ -n "$line" ]] && deps+=("$line")
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
' "$PENDING")

for ((i = 0; i < ${#deps[@]}; i++)); do
  d="${deps[i]}"
  done_file="factory/tasks/done/${d}.md"
  [[ -f "$done_file" ]] || exit 1
  if ! factory_dep_terminal_status "$done_file"; then
    exit 1
  fi
done

mv "$PENDING" "$CLAIMED"
PENDING_REMEDIATION="factory/tasks/pending/${TASK_ID}.remediation.md"
CLAIMED_REMEDIATION="factory/tasks/claimed/${TASK_ID}.remediation.md"
[[ -f "$PENDING_REMEDIATION" ]] && mv "$PENDING_REMEDIATION" "$CLAIMED_REMEDIATION" || true
echo "$(pwd)/${CLAIMED}"
