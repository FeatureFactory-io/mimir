# Skill: GitLab Issue Operations

**Capability Domain**: GITLAB_ISSUE
**Technology Stack**: GitLab CLI (glab)

## Overview

Patterns for managing GitLab Milestones and Issues as iteration execution records using `glab`. Mirrors the GitHub Issue Operations skill. Covers `<!-- SCENARIO -->` YAML embedding, label management, and structured comment templates.

## Bootstrap Labels

```bash
for label in \
  "status-queued:#e4e669" \
  "status-in-progress:#0075ca" \
  "status-done:#0e8a16" \
  "drift-absorbed:#fef2c0" \
  "drift-escalated:#e11d48" \
  "parallel-group-A:#bfd4f2" \
  "parallel-group-B:#d4c5f9" \
  "parallel-group-C:#f9d0c4"; do
  name=$(echo $label | cut -d: -f1)
  color=$(echo $label | cut -d: -f2)
  glab label create "$name" --color "$color" 2>/dev/null || true
done
```

## Pattern 1 — Create Milestone

```bash
PROJECT=$(glab api projects/:fullpath --jq '.id')

glab api "projects/$PROJECT/milestones" \
  --method POST \
  --field title="ITER-YYYYMMDD | {iteration_goal}" \
  --field description="$(cat <<'EOF'
<!-- MANIFEST -->
{paste full ITER-*.yaml verbatim}
<!-- /MANIFEST -->

## Iteration Goal
{iteration_goal}

## Scenarios
- S1: {title}
EOF
)"
# Record returned milestone id
```

## Pattern 2 — Create Scenario Issue

```bash
glab issue create \
  --title "[S1][A] {scenario title}" \
  --label "status-queued,parallel-group-A" \
  --milestone "{milestone_title}" \
  --description "$(cat <<'EOF'
<!-- SCENARIO -->
id: S1
parallel_group: A
skeleton_commit: "{hash}"
codebase_footprint:
  - path/to/file.py
checkpoint:
  command: "pytest tests/integration/test_feature.py -x"
  expected_exit_code: 0
dependencies: []
sao_sections:
  - "§Services Layer"
do_not_do:
  - "Do NOT create a new Django app"
system_dependencies:
  - notification_service   # or empty list [] if none; append [STUBBED] if stubbed in skeleton
rollback_point: "git stash"
<!-- /SCENARIO -->

## Context Map
| File | Lines | Note |
|------|-------|------|
| path/to/service.py | 45–80 | Follow this pattern |

## Do Not Do
- Do NOT create a new Django app

## SAO.md Sections That Apply
- §Services Layer

## Implementation Plan
{BPE-01 plan content — full text}

## Acceptance Criteria
- [ ] `pytest tests/integration/test_feature.py -x` passes
- [ ] No regressions: `pytest tests/ -x --ignore=tests/e2e` passes
- [ ] Changes committed with Angular convention message
EOF
)"
```

## Pattern 3 — Label State Transitions

```bash
# queued → in-progress
glab issue update {N} --add-label "status-in-progress" --remove-label "status-queued"

# in-progress → done
glab issue close {N}
glab issue update {N} --add-label "status-done" --remove-label "status-in-progress"

# drift escalation
glab issue update {N} --add-label "drift-escalated" --remove-label "status-in-progress"
```

## Pattern 4 — Checkpoint Pass Comment

```bash
glab issue note {N} --message "<!-- CHECKPOINT_PASS -->
Checkpoint passed at: $(date -u +%Y-%m-%dT%H:%M:%SZ)
Command: {command}
<!-- /CHECKPOINT_PASS -->"
```

## Pattern 5 — Absorbed Drift Comment

```bash
glab issue note {N} --message "<!-- DRIFT absorbed -->
type: checkpoint_fail
detected_at: $(date -u +%Y-%m-%dT%H:%M:%SZ)
action: {fix applied}
retry: PASS
<!-- /DRIFT -->"
glab issue update {N} --add-label "drift-absorbed"
```

## Pattern 6 — Escalate Comment

```bash
glab issue note {N} --message "<!-- ESCALATE -->
type: {footprint_violation|method_explosion|sao_violation|checkpoint_fail_retry|system_dependency_missing}
evidence: {specific — file / method / constraint / test output / missing dependency name}
jedao_recommendation: {A: fix and retry | B: resequence | C: scope reduce}
await_human_decision: true
<!-- /ESCALATE -->"
glab issue update {N} --add-label "drift-escalated" --remove-label "status-in-progress"
```

## Pattern 7 — Next Eligible Scenario

```bash
glab issue list \
  --milestone "{milestone_title}" \
  --label "status-queued" \
  --output json | python3 -c "
import sys, json, re, yaml
issues = json.load(sys.stdin)
for issue in issues:
    match = re.search(r'<!-- SCENARIO -->(.+?)<!-- /SCENARIO -->', issue.get('description',''), re.DOTALL)
    if not match: continue
    s = yaml.safe_load(match.group(1))
    print(f\"#{issue['iid']} {issue['title']} deps:{s.get('dependencies',[])}\")"
```
