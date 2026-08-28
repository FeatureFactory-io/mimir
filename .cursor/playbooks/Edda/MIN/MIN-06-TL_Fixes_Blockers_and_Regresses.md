# Activity: TL Fixes Blockers and Regresses

**Activity ID**: 221
**Order**: 6
**Phase**: None
**Dependencies**: None

## Description

TL Fixes Blockers and Regresses

## Guidance

## Purpose
Team Lead triages the UAT blocker list, invokes BPE-09 (Fix Bug) once per blocker, then sends Saga back for a targeted regression run over the affected scenarios. Loop until the regression verdict is CLEAN. Non-blockers are filed as deferred issues and do not gate close.

**Entry condition:** MIN-05 Saga produced a UAT Report with `Blockers > 0`. If blockers = 0, skip this activity — proceed directly to MIN-07.

---

## Step 1: Triage Blockers
Read the UAT Report. For each blocker issue:
```bash
gh issue view {bug_number} --json number,title,body,labels
```
Extract: failing scenario, step ID, expected vs actual, affected feature. Group by affected file/feature. Prioritize: fix bugs that unblock the most downstream journey steps first.

## Step 2: Invoke BPE-09 Per Blocker
For each blocker, run **BPE-09 Fix Bug** (Activity 203) as a fresh dr-dobbs subagent (cheap-fast model).

The BPE-09 input is the Bug Report filed by Saga in MIN-05. Pass it directly:
```
dr-dobbs — run BPE-09 Fix Bug for bug #{bug_number}.

Bug Report: gh issue view {bug_number} --json number,title,body

Follow BPE-09 steps exactly:
1. Analyze why existing tests missed the bug.
2. Write a failing test that reproduces it (Red).
3. Implement the minimal correct fix (Green).
4. Full regression: pytest tests/
5. Commit: fix({scope}): {bug_title} — Fixes #{bug_number}
6. Post NODE_PASS on the bug issue.

Scope: do not touch files unrelated to this bug. Do not patch symptoms.
```
Launch as a fresh Task subagent. Never resume a prior worker.

**On NODE_PASS:**
```bash
gh issue comment {bug_number} --body "<!-- FIX_COMMITTED -->\nCommit: {sha}\nTest gap: {one-line analysis}\n<!-- /FIX_COMMITTED -->"
```

**On NODE_FAIL after worker’s internal BPE-09 retry:** dispatch one additional TL-guided fix subagent with a narrower prompt targeting only the failing assertion. If still failing: escalate with `drift-escalated` label and await human decision.

## Step 3: Defer Non-Blockers
For each Major and Minor defect from the UAT Report:
```bash
gh issue edit {issue_number} --add-label "deferred"
gh issue comment {issue_number} --body "Deferred. Non-blocker from iteration {slug}. Fix in next iteration."
```

## Step 4: Regression UAT (Saga in Regression Mode)
After all blocker fixes are committed, invoke Saga as a fresh Task subagent (medium model):
```
Saga — regression run for iteration {slug}.
Re-execute only the scenarios / journeys that had failures in the prior UAT report:
  {affected_scenario_list}
Follow the full MIN-05 protocol (survey → execute → classify → report).
Produce a verdict: CLEAN or NEW_BLOCKERS_FOUND.
```

**CLEAN → proceed to MIN-07 TL Closes Sprint with Lessons and Release.**

**NEW_BLOCKERS_FOUND → loop back to Step 1.** Each loop iteration must make net progress (at least one fewer blocker than the prior loop). If the same blocker persists across two fix cycles: escalate.

## Exit Condition
Saga regression verdict is CLEAN and no open `blocker`-labelled issues remain on the milestone.

## Success Criteria
- Every UAT blocker passed through BPE-09 Fix Bug (test-gap analysis + failing test + fix + regression)
- Every fix has a commit where the reproducing test was red before and green after
- Full regression suite green after all fixes
- Saga regression run returns CLEAN over affected scenarios
- Non-blockers labeled `deferred` and removed from milestone gate
- Zero open blockers before proceeding to MIN-07

## Agent
**Team Lead (Orchestrator) — advanced reasoning model.** Triages blockers, assembles BPE-09 prompts, monitors worker results, coordinates regression Saga invocation.

**dr-dobbs (Worker) — cheap-fast model.** Runs BPE-09 Fix Bug per blocker: one bug per invocation, test-first, full regression before NODE_PASS.

**Saga (Regression UAT) — medium model.** Re-runs only affected scenarios from tests/e2e or tests/uat.

## Rules
- `do-test-first` (via BPE-09)
- `do-not-mock-in-integration-tests` (via BPE-09)
- `do-follow-commit-convention`
- `do-small-increments`

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
