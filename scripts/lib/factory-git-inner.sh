#!/usr/bin/env bash
# factory-git-inner.sh — run under factory_with_git_lock from factory-git.sh
set -euo pipefail

root="${FACTORY_GIT_ROOT:?FACTORY_GIT_ROOT required}"
msg="${FACTORY_GIT_MSG:?FACTORY_GIT_MSG required}"
shift_paths=("$@")

cd "$root"
branch="$(git symbolic-ref --short HEAD 2>/dev/null || echo main)"
git pull --rebase origin "$branch" 2>/dev/null || true

if git diff --name-only --diff-filter=U 2>/dev/null | grep -q .; then
  git diff --name-only --diff-filter=U | xargs -r git checkout --theirs -- 2>/dev/null || true
fi

if (( ${#shift_paths[@]} == 0 )); then
  shift_paths=(factory/)
fi

git add "${shift_paths[@]}"
if git diff --cached --quiet; then
  echo "factory-git: nothing to commit"
  exit 0
fi

git commit -m "$msg"
if [[ "${FACTORY_SKIP_PUSH:-}" != "1" ]]; then
  git push origin HEAD
fi
