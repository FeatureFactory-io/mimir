#!/usr/bin/env bash
# check-factory-prereqs.sh — verify CLI tools for dark-factory.
#
# Usage:
#   scripts/check-factory-prereqs.sh           # fail on missing binaries; warn on auth/cursor
#   scripts/check-factory-prereqs.sh --strict  # also fail on gh auth / cursor-agent warnings

set -euo pipefail

STRICT=0
[[ "${1:-}" == "--strict" ]] && STRICT=1

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

missing=()
warn=()

check_cmd() {
  local name="$1"
  if command -v "$name" >/dev/null 2>&1; then
    printf '  ok  %s (%s)\n' "$name" "$(command -v "$name")"
    return 0
  fi
  missing+=("$name")
  printf '  MISSING  %s\n' "$name"
  return 1
}

echo "Dark-factory prerequisites:"

for c in git gh fswatch tmux rg python3 jq; do
  check_cmd "$c" || true
done

if command -v flock >/dev/null 2>&1; then
  printf '  ok  flock (%s)\n' "$(command -v flock)"
elif [[ -x "$(brew --prefix util-linux 2>/dev/null)/bin/flock" ]]; then
  flock_path="$(brew --prefix util-linux)/bin/flock"
  printf '  ok  flock (%s)\n' "$flock_path"
  printf '  note add util-linux to PATH for interactive shell use: export PATH="$(brew --prefix util-linux)/bin:$PATH"\n'
else
  missing+=("flock (util-linux)")
  printf '  MISSING  flock — run make provision or install util-linux\n'
fi

if command -v cursor-agent >/dev/null 2>&1; then
  printf '  ok  cursor-agent (%s)\n' "$(command -v cursor-agent)"
  if (( STRICT == 1 )); then
    if cursor-agent --list-models >/dev/null 2>&1; then
      printf '  ok  cursor-agent --list-models\n'
      for role_var in FACTORY_LE_MODEL FACTORY_MODEL_FEATURE_BUILDER; do
        model="${!role_var:-}"
        [[ -z "$model" ]] && continue
        if ! cursor-agent --list-models 2>/dev/null | rg -qF "$model"; then
          warn+=("${role_var}=${model} not in cursor-agent --list-models")
          printf '  WARN  %s=%s not listed by cursor-agent --list-models\n' "$role_var" "$model"
        fi
      done
    else
      warn+=("cursor-agent --list-models unavailable — skip model validation")
      printf '  WARN  cursor-agent --list-models unavailable\n'
    fi
  fi
elif command -v cursor >/dev/null 2>&1; then
  printf '  ok  cursor (%s — factory.sh accepts cursor CLI)\n' "$(command -v cursor)"
else
  warn+=("cursor-agent or cursor not on PATH (install via Cursor IDE CLI)")
  printf '  WARN  cursor-agent / cursor not found\n'
fi

if command -v gh >/dev/null 2>&1; then
  if gh auth status >/dev/null 2>&1; then
    printf '  ok  gh auth\n'
  else
    warn+=("gh not authenticated — run: gh auth login")
    printf '  WARN  gh auth — run: gh auth login\n'
  fi
fi

if command -v watch >/dev/null 2>&1; then
  printf '  ok  watch (optional status pane)\n'
else
  printf '  note watch not installed (factory.sh uses sleep loop fallback)\n'
fi

echo ""
if (( ${#missing[@]} > 0 )); then
  echo "Missing required tools: ${missing[*]}"
  echo "Re-run: make provision"
  exit 1
fi

if (( ${#warn[@]} > 0 )); then
  echo "Manual steps (not installed by make provision):"
  for w in "${warn[@]}"; do
    echo "  - $w"
  done
  if (( STRICT == 1 )); then
    exit 1
  fi
fi

if (( ${#missing[@]} == 0 && ${#warn[@]} == 0 )); then
  echo "All dark-factory prerequisites satisfied."
fi

exit 0
