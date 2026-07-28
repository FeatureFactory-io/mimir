# Skill: Drift Detection and Classification

**Capability Domain**: DRIFT_DETECTION  
**Technology Stack**: GitHub CLI + YAML

## Overview

Patterns for detecting, classifying, and responding to execution deviations during MIT. Covers signal type definitions, severity thresholds, detection commands, and the absorbed/escalated response protocol.

Time-based signals are not used — Claude Code cannot reliably measure wall-clock time in autonomous mode. All drift detection is based on observable artifacts: git diffs, method signatures, and explicit SAO.md compliance review.

## Signal Type Reference

| Signal Type | Trigger Condition | Severity |
|---|---|---|
| `footprint_violation` | any file in `git diff {skeleton_commit} --name-only` is NOT in `codebase_footprint[]` | escalated |
| `method_explosion` | unplanned public method added since skeleton commit (not prefixed with `_`) | escalated |
| `sao_violation` | SAO compliance check finds implementation breaches an architectural constraint | escalated |
| `checkpoint_fail` | checkpoint command exits non-zero (first occurrence) | absorbed (retry once) |
| `checkpoint_fail_retry` | checkpoint fails after one retry | escalated |

## Reference Implementation

### Pattern 1: Detect Footprint Violation

```bash
# Get files changed since skeleton commit
git diff {skeleton_commit} --name-only > /tmp/actual_files.txt

# Compare against declared footprint
python3 - <<EOF
footprint = {codebase_footprint_list}  # from issue <!-- SCENARIO --> YAML

with open('/tmp/actual_files.txt') as f:
    actual = set(f.read().splitlines())

violations = actual - set(footprint)
if violations:
    for f in sorted(violations):
        print(f"SIGNAL: footprint_violation | severity: escalated | file: {f}")
else:
    print("footprint check: PASS — no unexpected files")
EOF
```

All footprint violations escalate. There is no absorbed path for this signal.

### Pattern 2: Detect Method Explosion

```bash
# Find new public methods added since skeleton commit (non-underscore def at class indent level)
NEW_PUBLIC=$(git diff {skeleton_commit} -- {file} \
  | grep "^+    def " \
  | grep -v "^+    def _")

if [ -n "$NEW_PUBLIC" ]; then
  echo "SIGNAL: method_explosion | severity: escalated"
  echo "Evidence: unplanned public methods:"
  echo "$NEW_PUBLIC"
else
  echo "method explosion check: PASS — no unplanned public methods"
fi
```

Run this check for each file in `codebase_footprint[]` separately so evidence is file-specific.

### Pattern 3: SAO Compliance Check

This is a reasoning step, not a script. For each section listed in `sao_sections[]` from the issue body:

1. Read that section of `docs/architecture/SAO.md`
2. For each constraint in the section, state explicitly:
   - `complies: {constraint summary}` — implementation respects it
   - `violation: {constraint summary} — {what was built that breaches it}`

```
Reviewing §Services Layer:
  - "Services are shared by MCP and Web UI, no MCP-specific logic" → complies
  - "Services call ORM directly, no intermediate layer" → violation: added WorkflowRepository between service and ORM

SIGNAL: sao_violation | severity: escalated
Evidence: WorkflowRepository class violates §Services Layer — services must call ORM directly
```

If all constraints pass: "SAO compliance check: PASS — no violations."

### Pattern 4: Classify Checkpoint Failure

```bash
# Run checkpoint and capture exit code
{checkpoint.command} > /tmp/checkpoint_out.txt 2>&1
CHECKPOINT_EXIT=$?

if [ $CHECKPOINT_EXIT -ne 0 ]; then
  # Check if a retry has already been attempted on this issue
  RETRY_COUNT=$(gh issue view {issue_number} --json comments \
    --jq '[.comments[].body | select(contains("DRIFT absorbed") and contains("checkpoint_fail"))] | length')

  if [ "$RETRY_COUNT" -eq 0 ]; then
    echo "SIGNAL: checkpoint_fail | severity: absorbed | action: retry once"
    # Apply targeted fix, then re-run checkpoint
  else
    echo "SIGNAL: checkpoint_fail_retry | severity: escalated"
    cat /tmp/checkpoint_out.txt | tail -20
  fi
fi
```

## Severity Decision Tree

```
Drift detected?
  ├─ footprint_violation:
  │     any file outside codebase_footprint[] → escalated (no absorbed path)
  │
  ├─ method_explosion:
  │     any unplanned public method → escalated (no absorbed path)
  │
  ├─ sao_violation:
  │     any architectural constraint breached → escalated (no absorbed path)
  │
  └─ checkpoint_fail:
        first occurrence → absorbed (retry once)
        retry fails      → checkpoint_fail_retry → escalated
```

## Post-Detection Actions

### Absorbed (checkpoint_fail first occurrence):
```bash
gh issue comment {issue_number} --body "<!-- DRIFT absorbed -->
type: checkpoint_fail
action: {targeted fix applied}
retry: PASS
<!-- /DRIFT -->"
gh issue edit {issue_number} --add-label "drift-absorbed"
```

### Escalated (any signal):
```bash
gh issue comment {issue_number} --body "<!-- ESCALATE -->
type: {footprint_violation|method_explosion|sao_violation|checkpoint_fail_retry}
evidence: {specific: file name / method name / SAO constraint / test output}
jedao_recommendation: {A: fix and retry | B: resequence | C: scope reduce}
await_human_decision: true
<!-- /ESCALATE -->"
gh issue edit {issue_number} --add-label "drift-escalated" --remove-label "status-in-progress"
```

## Quality Gates

- [ ] Every drift event has a signal type from the defined enum (footprint_violation, method_explosion, sao_violation, checkpoint_fail, checkpoint_fail_retry)
- [ ] Footprint check run against `skeleton_commit` hash (not HEAD~1)
- [ ] Method explosion check run per file, not across entire diff
- [ ] SAO compliance check explicitly states "complies" or "violation" per constraint — not a blanket statement
- [ ] Absorbed signals: action taken described in comment
- [ ] Escalated signals: `jedao_recommendation` and specific `evidence` present in comment
