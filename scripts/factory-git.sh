#!/usr/bin/env bash
# factory-git.sh — serialized commit/push for factory/ state on the mgmt branch.
#
# Usage: scripts/factory-git.sh <commit-message> [paths...]
# Defaults paths to factory/ when none given.

set -euo pipefail

# shellcheck source=lib/factory-common.sh
source "$(cd "$(dirname "$0")" && pwd)/lib/factory-common.sh"
REPO_ROOT="$(_factory_repo_root)"

MSG="${1:?usage: $0 <commit-message> [paths...]}"
shift

PATHS=("$@")
if (( ${#PATHS[@]} == 0 )); then
  PATHS=(factory/)
fi

export FACTORY_GIT_ROOT="$REPO_ROOT"
export FACTORY_GIT_MSG="$MSG"

factory_with_git_lock bash "${REPO_ROOT}/scripts/lib/factory-git-inner.sh" "${PATHS[@]}"
