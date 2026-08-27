# Activity: Fix & Reintegrate

**Activity ID**: 184
**Order**: 6
**Phase**: None
**Dependencies**: Predecessor: Activity 183 (UAT Agent)
Successor: Activity 185 (Close Iteration)

## Description

Team Lead triages the UAT blocker list, dispatches targeted dr-dobbs fix workers, runs DoD on each fix, then invokes Saga (UAT Agent) in regression mode over the affected journeys. Loop until no blockers remain. Non-blockers are filed as deferred issues and do not gate close.

## Guidance

**Entry condition:** MIN-05 UAT Agent produced a UAT Report with `Blockers > 0`. If blockers = 0, skip this activity and proceed directly to MIN-07.

---

## Step 1: Triage Blockers

Read the UAT Report. For each blocker issue:

```bash
gh issue view {bug_issue_number} --json number,title,body,labels
```

Extract:
- Failing scenario ID and step ID
- Expected vs actual observed
- Affected feature (which MIN-04 closed issue caused this regression or gap)

Group blockers by affected feature. Prioritize: fix bugs that unblock the most dependent journey steps first.

---

## Step 2: Dispatch Fix Workers

For each blocker (or batch of blockers in the same file/feature):

**2a. Create a fix task:**

```bash
gh issue comment {bug_issue_number} --body "<!-- FIX_START -->
Dispatching dr-dobbs fix worker.
Started: {ISO8601}
<!-- /FIX_START -->"
```

**2b. Assemble fix prompt for dr-dobbs:**

```
You are dr-dobbs — cheap-fast fix worker. Fix bug #{bug_issue_number}: {title}

Context:
- UAT scenario: {scenario_id} STEP {step_id}
- Expected: {see_assertion}
- Actual: {what_was_observed}
- Affected code: {affected_feature_issue_closed_in_MIN-04}

Instructions:
1. Read the bug issue: gh issue view {bug_issue_number} --json number,title,body
2. Write a failing test that reproduces the bug (test-first).
3. Fix the root cause — do not patch symptoms.
4. Run the failing test to confirm it now passes.
5. Run full regression: pytest tests/ -x --ignore=tests/e2e
6. If regression clean: post NODE_PASS on the bug issue.
7. If regression red from your change: revert and post NODE_FAIL.

Do NOT:
- Change method signatures or create new public methods not in skeleton
- Touch files unrelated to this bug
- Skip the failing test step
```

**2c. Launch as fresh Task subagent** (cheap-fast model, never resume).

**2d. Monitor NODE_PASS / NODE_FAIL:**

On NODE_PASS:
```bash
git add -A
git commit -m "fix({scope}): {bug_title}

Fixes #{bug_issue_number}
UAT scenario: {scenario_id} STEP {step_id}"

gh issue comment {bug_issue_number} --body "<!-- FIX_COMMITTED -->
Commit: {sha}
Test: passing
Regression: clean
<!-- /FIX_COMMITTED -->"
```

On NODE_FAIL (after worker's internal retry):
- Dispatch one additional targeted TL-guided fix subagent with a narrower prompt
- If still failing after second worker: escalate, apply `drift-escalated` label, pause

---

## Step 3: DoD Spot-Check on Each Fix

After each fix is committed, run a targeted BPE-06 check scoped to the fix:

```bash
pytest tests/ -x --ignore=tests/e2e 2>&1 | tail -10
```

Verify:
- Fix has a test (the failing-then-passing test from Step 2)
- No new methods without tests
- Commit follows Angular convention

If any DoD item fails: fix it inline or dispatch a micro dr-dobbs worker for it.

---

## Step 4: Regression UAT — Re-run Affected Journeys

After all blocker fixes are committed, invoke **Saga in regression mode**:

```
Saga — regression run. Re-execute only the following journeys from tests/uat/:

Affected journeys: {list from UAT Report — only journeys that had IF DIFFER blockers}

Follow the same UAT Agent protocol (MIN-05). File any new IF DIFFER as bugs.
Produce a regression UAT report: CLEAN or NEW_BLOCKERS_FOUND.
```

Launch Saga as a fresh Task subagent (medium model).

**On `CLEAN`:** no open blockers remain — proceed to MIN-07.

**On `NEW_BLOCKERS_FOUND`:** loop back to Step 1 with the new blocker list. Each loop iteration must make net progress (at least one blocker resolved). If a blocker persists across two fix cycles: escalate.

---

## Step 5: Deferred Non-Blockers

Major and Minor issues from the UAT Report are **not** fixed in this iteration:

```bash
for issue in {major_and_minor_list}; do
  gh issue edit {issue} --milestone {next_milestone_number_or_backlog} --add-label "deferred"
  gh issue comment {issue} --body "Deferred from iteration {slug}. Non-blocker. Fix in next iteration."
done
```

---

## Exit Condition

```bash
gh issue list --milestone {N} --label "blocker" --state open | jq 'length'
# must return 0
```

And regression Saga report is `CLEAN`. Then proceed to MIN-07 Close Iteration.

---

## Rules

- `do-test-first` — every fix ships with a test that was red before the fix
- `do-not-mock-in-integration-tests`
- `do-follow-commit-convention`
- `do-small-increments` — one fix per commit; no bundled patches

## Success Criteria

- All blocker issues from UAT Report have NODE_PASS from a fix worker
- Each fix has a corresponding test (was red before fix, green after)
- Full regression suite green after all fixes
- Saga regression run returns CLEAN over affected journeys
- Non-blocker issues labeled `deferred` and moved out of milestone gate
- Zero open blocker issues on milestone

## Agent

**Team Lead (Orchestrator):** advanced reasoning model — triages bugs, assembles fix prompts, monitors workers, coordinates regression UAT

**dr-dobbs (Worker):** cheap-fast model — implements one bug fix per invocation, writes failing test first, posts NODE_PASS or NODE_FAIL

**Saga (Regression UAT):** medium reasoning model — re-runs only affected journeys from `tests/uat/`

## Skill

None

## Artifacts Produced

- Fix commits (one per bug)
- Regression UAT report

## Artifacts Consumed

- UAT Report (from MIN-05)
- Bug issues (from MIN-05)

## Notes

No additional notes.
