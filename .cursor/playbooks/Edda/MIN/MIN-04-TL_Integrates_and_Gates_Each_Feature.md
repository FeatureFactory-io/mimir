# Activity: TL Integrates and Gates Each Feature

**Activity ID**: 222
**Order**: 4
**Phase**: None
**Dependencies**: None

## Description

TL Integrates and Gates Each Feature

## Guidance

## Purpose
For each issue that posts BUILD_COMPLETE: verify the DoD node already ran (do not re-run it), run BPE-07 Finalize Feature (Activity 102 in the Build Feature workflow), and close the issue. When all issues are closed, open the iteration PR for human review. TL may fix trivial presentation issues inline only — no logic, no new tests.

**Runs interleaved with Execute:** as soon as an issue posts BUILD_COMPLETE, start its gate cycle.

---

## TL Code Authority

TL **may** fix inline (without dispatching a worker):
- Adding a missing `data-testid` attribute to an existing static HTML element
- Correcting an import order violation
- Fixing a commit message format

TL **must** dispatch a dr-dobbs worker for:
- Any fix that touches logic, queries, or view code
- Any missing or broken test
- Any method that needs to be created or modified

This authority is consistent with Execute (Activity 181). dr-dobbs workers dispatched from this activity operate under the same isolation rules as in Activity 181.

---

## Per-Issue Cycle

### Step 1: Verify All Nodes Committed and NODE_PASS

```bash
# Count NODE_PASS comments — must equal total node count in the graph
gh issue view {N} --json comments | jq '[.comments[] | select(.body | contains("NODE_PASS"))] | length'

# Verify each NODE_PASS contains a commit SHA
gh issue view {N} --json comments | jq '[.comments[] | select(.body | contains("NODE_PASS")) | select(.body | contains("commit:"))] | length'
```

Both counts must equal `total_nodes`. If any NODE_PASS is missing a commit SHA: return to Execute (Activity 181) to dispatch a cleanup worker.

### Step 2: Verify the BPE-06 DoD Node Ran

BPE-06 (Check Definition of Done, Activity 101 in Build Feature workflow) was dispatched as a terminal node by Execute (Activity 181). Do **not** re-run the full checklist. Instead, verify it passed:

```bash
gh issue view {N} --json comments | jq '[.comments[] | select(.body | contains("NODE_PASS")) | select(.body | contains("BPE-06"))] | length'
```

If the BPE-06 node did not post NODE_PASS: return to Execute (Activity 181) to dispatch it.

If BPE-06 NODE_PASS is present, run a lightweight regression:
```bash
pytest tests/ -x --ignore=tests/e2e -q 2>&1 | tail -5
```
Green → proceed. Red → dispatch targeted dr-dobbs fix worker, rerun.

### Step 3: Run BPE-07 — Finalize Feature

Apply BPE-07 (Finalize Feature, Activity 102 in Build Feature workflow):

**3a. Full test suite:**
```bash
pytest tests/ -x --ignore=tests/e2e
```
100% pass rate required. Any failure: dispatch targeted dr-dobbs fix worker, rerun.

**3b. Dependencies:** no new packages missing from `requirements.txt`.

**3c. Scenario terminal checkpoint:**
```bash
{checkpoint.command}   # from manifest
```
Must exit 0. One fix attempt → retry → escalate.

**3d. Finalize commit (if anything changed during gate):**
```bash
git add -A
git commit -m "chore({scope}): BPE-07 finalize for #{N} — {feature_title}"
```

### Step 4: Close Issue
```bash
gh issue close {N} --comment "<!-- GATE_PASS -->\nBPE-06 node: NODE_PASS (worker-run)\nBPE-07: PASS\nCheckpoint: PASS\nBranch: iteration/{slug}\nReady for: Acceptance\n<!-- /GATE_PASS -->"
gh issue edit {N} --remove-label "status-in-progress" --add-label "status-done"
```

### Step 5: Advance the Queue
Check Execute (Activity 181) for newly unblocked BLOCKED scenarios.

---

## Exit Gate — All Issues Integrated

When all issues on the milestone are closed:
```bash
gh issue list --milestone {N} --state open --json number | jq 'length'
# must return 0
```

Then open the iteration PR:
```bash
gh pr create \
  --base main \
  --head iteration/{slug} \
  --title "Iteration {slug}: {goal}" \
  --body "## Delivered\n{scenario list with issue links}\n\n## Gate\nAll issues: NODE_PASS + BPE-06 node + BPE-07 PASS\n\n## Next\nAcceptance testing runs on this branch before merge."
```

Record the PR number. Proceed to Acceptance (Activity 183 — Saga UAT on the iteration branch, do not merge yet).

## Success Criteria
- Every NODE_PASS comment contains a commit SHA
- BPE-06 node verified (worker-run via Execute, not re-executed by TL)
- Regression suite green before each issue closes
- BPE-07 Finalize applied per issue
- All issues status-done with GATE_PASS
- Iteration PR opened against main

## Agent
None — TL inline. May dispatch targeted dr-dobbs workers for regression failures or missing BPE-06 node.

## Rules
`do-test-first`, `do-not-mock-in-integration-tests`, `do-informative-logging`, `do-assert-log-story`, `do-follow-commit-convention`

## Agent

None

## Skill

None

## Rules

None

## Artifacts Produced

None

## Artifacts Consumed

None

## Notes

No additional notes.
