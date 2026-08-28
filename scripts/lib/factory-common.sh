#!/usr/bin/env bash
# factory-common.sh — shared helpers for dark-factory scripts.
# Source from repo scripts: source "$(dirname "$0")/lib/factory-common.sh"

_factory_repo_root() {
  if [[ -n "${FACTORY_REPO_ROOT:-}" ]]; then
    printf '%s\n' "$FACTORY_REPO_ROOT"
    return 0
  fi
  local here
  here="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
  printf '%s\n' "$here"
}

_factory_flock_cmd() {
  if command -v flock >/dev/null 2>&1; then
    command -v flock
    return 0
  fi
  local brew_flock
  brew_flock="$(brew --prefix util-linux 2>/dev/null)/bin/flock"
  if [[ -x "$brew_flock" ]]; then
    printf '%s\n' "$brew_flock"
    return 0
  fi
  echo "error: flock not found — install util-linux" >&2
  return 1
}

# Run a command under factory/.git.lock (serialized factory-state git ops).
factory_with_git_lock() {
  local root lock flock_cmd
  root="$(_factory_repo_root)"
  lock="${root}/factory/.git.lock"
  flock_cmd="$(_factory_flock_cmd)" || return 1
  mkdir -p "${root}/factory"
  (
    "$flock_cmd" -x 9
    "$@"
  ) 9>"$lock"
}

# Extract frontmatter or result field from a task markdown file.
factory_task_field() {
  local file="$1" field="$2"
  rg -m1 "^${field}:[[:space:]]*" "$file" 2>/dev/null \
    | sed "s/^${field}:[[:space:]]*//" \
    | tr -d '"' \
    | tr -d "'"
}

factory_result_section() {
  local file="$1"
  awk '/^# Result/{found=1; next} found{print}' "$file"
}

factory_result_field() {
  local file="$1" field="$2"
  local section
  section="$(factory_result_section "$file")"
  printf '%s\n' "$section" \
    | rg -m1 "^${field}:[[:space:]]*" \
    | sed "s/^${field}:[[:space:]]*//" \
    | tr -d '"' \
    | tr -d "'"
}

# Classify task result kind: code | manual | monitoring
factory_result_kind() {
  local file="$1"
  local role status branch mr
  role="$(factory_task_field "$file" role)"
  status="$(factory_result_field "$file" status)"
  branch="$(factory_result_field "$file" branch)"
  mr="$(factory_result_field "$file" mr)"

  if [[ "$status" == "monitoring" && "$mr" == "0" ]]; then
    echo "monitoring"
    return 0
  fi
  if [[ "$role" == "manual-tester" ]]; then
    echo "manual"
    return 0
  fi
  if [[ "$branch" == "none" || "$branch" == '""' || -z "$branch" ]] \
    && [[ "$mr" == "0" ]]; then
    echo "manual"
    return 0
  fi
  echo "code"
}

# Terminal integrated/validated statuses for dependency eligibility.
factory_dep_terminal_status() {
  local done_file="$1"
  local status role
  status="$(factory_result_field "$done_file" status)"
  role="$(factory_task_field "$done_file" role)"

  case "$status" in
    integrated|validated|monitoring) return 0 ;;
  esac
  if [[ "$role" == "manual-tester" && "$status" == "passed" ]]; then
    return 0
  fi
  return 1
}
