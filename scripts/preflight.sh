#!/usr/bin/env bash
# preflight.sh — Phase 0 dry gate for dark-factory.
#
# Usage: scripts/preflight.sh [options] <milestone-title>
#
# Options:
#   --allow-dirty
#   --allow-missing-featurefile-ref
#   --skip-staging-check

set -euo pipefail

ALLOW_DIRTY=false
ALLOW_MISSING_FEATUREFILE_REF=false
SKIP_STAGING_CHECK=false
ARGS=()
for arg in "$@"; do
  case "$arg" in
    --allow-dirty) ALLOW_DIRTY=true ;;
    --allow-missing-featurefile-ref) ALLOW_MISSING_FEATUREFILE_REF=true ;;
    --skip-staging-check) SKIP_STAGING_CHECK=true ;;
    *) ARGS+=("$arg") ;;
  esac
done

MILESTONE="${ARGS[0]:?usage: $0 [--allow-dirty] [--skip-staging-check] <milestone-title>}"

REPO_ROOT="${FACTORY_REPO_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
cd "$REPO_ROOT"

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "error: missing command: $1" >&2
    exit 1
  }
}

for c in git gh fswatch tmux rg python3 jq; do require_cmd "$c"; done

if ! command -v cursor-agent >/dev/null 2>&1 && ! command -v cursor >/dev/null 2>&1; then
  echo "error: need cursor-agent or cursor on PATH" >&2
  exit 1
fi

if ! gh auth status >/dev/null 2>&1; then
  echo "error: gh not authenticated — run: gh auth login" >&2
  exit 1
fi

command -v watch >/dev/null 2>&1 || echo "warn: watch not on PATH (factory.sh falls back to sleep loop)" >&2

if [[ "$ALLOW_DIRTY" != true ]] && [[ -n "$(git status --porcelain 2>/dev/null)" ]]; then
  echo "error: git working tree not clean (commit/stash or pass --allow-dirty)" >&2
  exit 1
fi

# Resolve milestone via gh api (open milestone required)
REPO_SLUG="$(gh repo view --json nameWithOwner -q .nameWithOwner)"
MILESTONE_JSON="$(gh api "repos/${REPO_SLUG}/milestones" --paginate -q \
  "[.[] | select(.state==\"open\" and .title==\"${MILESTONE}\")] | .[0]")"

if [[ "$MILESTONE_JSON" == "null" || -z "$MILESTONE_JSON" ]]; then
  echo "error: no open milestone titled '${MILESTONE}'" >&2
  exit 1
fi

MILESTONE_NUMBER="$(printf '%s' "$MILESTONE_JSON" | jq -r '.number')"
OPEN_ISSUES="$(printf '%s' "$MILESTONE_JSON" | jq -r '.open_issues')"
echo "milestone: #${MILESTONE_NUMBER} (${MILESTONE}) open_issues=${OPEN_ISSUES}"

ISSUES_JSON="$(gh issue list --milestone "$MILESTONE" --state open --json number,title,body --limit 500)" || {
  echo "error: gh issue list failed" >&2
  exit 1
}

ISSUE_COUNT="$(printf '%s' "$ISSUES_JSON" | jq 'length')"
if (( ISSUE_COUNT == 0 )); then
  echo "error: milestone has no open issues" >&2
  exit 1
fi

if [[ "$ALLOW_MISSING_FEATUREFILE_REF" == true ]]; then
  export PREFLIGHT_ALLOW_MISSING_FEATUREFILE_REF=1
fi

printf '%s' "$ISSUES_JSON" | python3 "${REPO_ROOT}/scripts/validate-feature-refs.py" \
  --repo-root "$REPO_ROOT" || {
  if [[ "$ALLOW_MISSING_FEATUREFILE_REF" != true ]]; then
    exit 1
  fi
  echo "warn: feature validation failed but waived by --allow-missing-featurefile-ref" >&2
}

unset PREFLIGHT_ALLOW_MISSING_FEATUREFILE_REF 2>/dev/null || true

# Optional staging reachability (STAGING_URL or make eb-status idle CNAME)
if [[ "$SKIP_STAGING_CHECK" != true ]]; then
  STAGING_URL="${STAGING_URL:-}"
  if [[ -z "$STAGING_URL" ]] && command -v make >/dev/null 2>&1; then
    STAGING_URL="$(make -s eb-status 2>/dev/null | rg -m1 'mimir-idle' | awk '{print $NF}' || true)"
    if [[ -n "$STAGING_URL" && "$STAGING_URL" != http* ]]; then
      STAGING_URL="http://${STAGING_URL}"
    fi
  fi
  if [[ -n "$STAGING_URL" ]]; then
    if curl -sf --max-time 10 "${STAGING_URL}/" >/dev/null 2>&1; then
      echo "staging: reachable (${STAGING_URL})"
    else
      echo "warn: staging URL not reachable: ${STAGING_URL} (pass --skip-staging-check to waive)" >&2
    fi
  else
    echo "note: no STAGING_URL configured — skipping reachability check"
  fi
fi

echo "preflight ok: milestone #${MILESTONE_NUMBER}, ${ISSUE_COUNT} open issue(s)"
