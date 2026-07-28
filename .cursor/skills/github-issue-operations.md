# Skill: GitHub Issue Operations

**Capability Domain**: GITHUB_ISSUE
**Technology Stack**: GitHub CLI

## Overview

Patterns for managing GitHub Milestones and Issues as iteration execution records. Covers the `<!-- SCENARIO -->` YAML embedding convention, label management for iteration state, and structured comment templates for checkpoints and drift signals.

## Bootstrap Labels

```bash
for label in \
  "status-queued:#e4e669:Scenario waiting to start" \
  "status-in-progress:#0075ca:Scenario being executed" \
  "status-done:#0e8a16:Scenario complete" \
  "drift-absorbed:#fef2c0:Drift absorbed within threshold" \
  "drift-escalated:#e11d48:Drift escalated to human" \
  "parallel-group-A:#bfd4f2:" \
  "parallel-group-B:#d4c5f9:" \
  "parallel-group-C:#f9d0c4:" \
  "backlog:#ededed:"; do
  name=$(echo $label | cut -d: -f1)
  color=$(echo $label | cut -d: -f2)
  desc=$(echo $label | cut -d: -f3)
  gh label create "$name" --color "$color" --description "$desc" 2>/dev/null || true
done
```

## Pattern 1 — Create Milestone

```bash
gh api repos/{owner}/{repo}/milestones \
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
# Record returned milestone number
```

## Pattern 2 — Create Scenario Issue

```bash
gh issue create \
  --title "[S1][A] {scenario title}" \
  --label "status-queued,parallel-group-A" \
  --milestone "{milestone_number}" \
  --body "$(cat <<'EOF'
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

## Pattern 2b — Parse SCENARIO Block from Issue Body

```bash
# Get issue body
ISSUE_BODY=$(gh issue view {issue_number} --json body --jq '.body')

# Extract and parse SCENARIO block
python3 - <<EOF
import re, yaml

body = """$ISSUE_BODY"""
match = re.search(r'<!-- SCENARIO -->(.+?)<!-- /SCENARIO -->', body, re.DOTALL)
if match:
    scenario = yaml.safe_load(match.group(1))
    print('ID:', scenario['id'])
    print('Group:', scenario['parallel_group'])
    print('Skeleton commit:', scenario['skeleton_commit'])
    print('Checkpoint:', scenario['checkpoint']['command'])
    print('Footprint:', scenario['codebase_footprint'])
    print('SAO sections:', scenario['sao_sections'])
    print('Do not do:', scenario['do_not_do'])
    print('Dependencies:', scenario['dependencies'])
    print('System deps:', scenario.get('system_dependencies', []))
EOF
```

## Pattern 3 — Label State Transitions

```bash
# queued → in-progress
gh issue edit {N} --add-label "status-in-progress" --remove-label "status-queued"

# in-progress → done
gh issue close {N}
gh issue edit {N} --add-label "status-done" --remove-label "status-in-progress"

# drift escalation
gh issue edit {N} --add-label "drift-escalated" --remove-label "status-in-progress"
```

## Pattern 4 — Checkpoint Pass Comment

```bash
gh issue comment {N} --body "<!-- CHECKPOINT_PASS -->
Checkpoint passed at: $(date -u +%Y-%m-%dT%H:%M:%SZ)
Command: {command}
<!-- /CHECKPOINT_PASS -->"
```

## Pattern 5 — Absorbed Drift Comment

```bash
gh issue comment {N} --body "<!-- DRIFT absorbed -->
type: checkpoint_fail
detected_at: $(date -u +%Y-%m-%dT%H:%M:%SZ)
action: {fix applied}
retry: PASS
<!-- /DRIFT -->"
gh issue edit {N} --add-label "drift-absorbed"
```

## Pattern 6 — Escalate Comment

```bash
gh issue comment {N} --body "<!-- ESCALATE -->
type: {footprint_violation|method_explosion|sao_violation|checkpoint_fail_retry|system_dependency_missing}
evidence: {specific — file / method / constraint / test output / missing dependency name}
jedao_recommendation: {A: fix and retry | B: resequence | C: scope reduce}
await_human_decision: true
<!-- /ESCALATE -->"
gh issue edit {N} --add-label "drift-escalated" --remove-label "status-in-progress"
```

## Pattern 7 — Next Eligible Scenario

```bash
# Get all queued issues for milestone
gh issue list \
  --milestone {N} \
  --label "status-queued" \
  --json number,title,body \
  --jq '.[] | {number, title}'

# Filter for scenarios with all dependencies met
python3 - <<EOF
import subprocess, json, re, yaml

issues = json.loads(subprocess.check_output([
    'gh', 'issue', 'list', '--milestone', '{N}',
    '--label', 'status-queued', '--json', 'number,title,body'
]))

for issue in issues:
    body = issue['body']
    match = re.search(r'<!-- SCENARIO -->(.+?)<!-- /SCENARIO -->', body, re.DOTALL)
    if not match:
        continue
    scenario = yaml.safe_load(match.group(1))
    deps = scenario.get('dependencies', [])
    # For each dependency issue number, verify it is closed with status-done
    all_done = all(
        'status-done' in subprocess.check_output(
            ['gh', 'issue', 'view', str(dep), '--json', 'labels', '--jq', '[.labels[].name]']
        ).decode()
        for dep in deps
    ) if deps else True
    if all_done:
        print(f"ELIGIBLE: #{issue['number']} {issue['title']}")
        break
EOF
```

## Quality Gates

- [ ] Every scenario issue has `<!-- SCENARIO -->` block parseable as YAML
- [ ] `skeleton_commit` field present and is a valid git hash
- [ ] `sao_sections[]` and `do_not_do[]` fields present and non-empty
- [ ] `system_dependencies[]` field present (empty list `[]` is valid)
- [ ] Context Map, Do Not Do, SAO Sections, and Implementation Plan all present inline (not linked)
- [ ] Every scenario issue linked to correct milestone
- [ ] Labels transition correctly through state machine
- [ ] Drift comments include `type`, `detected_at`, `evidence`
- [ ] Escalate comments include `jedao_recommendation` and specific `evidence`
