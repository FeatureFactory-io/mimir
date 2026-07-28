# Activity: Activate Iteration

**Activity ID**: 178
**Order**: 1
**Phase**: None
**Dependencies**: None

## Description

Activate Iteration

## Guidance

## Purpose
Activate the iteration from a single human trigger. Find the requested milestone, verify it is ready, and confirm a clean execution slate.

**Trigger:** user says "Work on milestone `<name or #N>`"

## Step 0: Verify PIN Artifacts Exist (do this FIRST)
Before touching GitHub, confirm PIN completed its work:
```bash
ls docs/plans/iterations/ITER-*.yaml 2>/dev/null | head -1
```
If no file found:
> **STOP.** No execution manifest found. The Plan Iteration (PIN) workflow must be run first to produce the manifest, skeletons, and milestone. Tell the user: "Run PIN on this feature first, then invoke MIN."

If found: proceed.

## Step 1: Find the Milestone
```bash
gh milestone list --json number,title,state | jq '.[] | select(.state == "open")'
```
Match the user's input (name substring or #N) to one open milestone. If no match or multiple matches: stop and ask the user to clarify.

## Step 2: Confirm Issues and Sprint-Size Guard
Get each issue one at a time — do not list all:
```bash
gh issue view {github_issue} --json number,title,labels,state
```
Confirm each is open with `status-queued`. Report any discrepancy before proceeding.

**Sprint-size guard:** check total open issues on the milestone:
```bash
gh api repos/{owner}/{repo}/milestones/{N} --jq '.open_issues'
```
If `open_issues > 15`: warn before proceeding:
> "This milestone has {N} open issues. Sprints above ~10 issues carry high drift risk. Consider splitting before running MIN. Proceed? (yes / no)"

Do not proceed until explicit user confirmation.

## Step 3: Verify Clean Slate
```bash
gh issue list --milestone {N} --label "status-in-progress" --json number,title
```
If any issue has `status-in-progress`: do not re-activate. Resume from MIN-04 for that scenario — re-run its checkpoint first:
- PASS → close issue (`status-done`), continue queue
- FAIL → treat as first checkpoint_fail, apply one retry before escalating

Only proceed if no `status-in-progress` issue exists.

## Step 4: Output Confirmation
```
=== MIN ACTIVATION ===
Manifest: ITER-{slug}.yaml ✓
Milestone: #{N} | {goal}
Issues:    {N} open, all status-queued
Size:      {ok | WARNING: {N} issues — user confirmed}
Slate:     clean — no in-progress work
Next:      MIN-02 Load Context
======================
```

## Success Criteria
- PIN manifest confirmed present before any GitHub call
- Milestone found and uniquely identified
- All issues confirmed open with `status-queued` (fetched one by one)
- Sprint-size warning shown if > 15 issues; user confirmed to proceed
- No dangling `status-in-progress` issue from prior session
- Ready to proceed to MIN-02

## Inputs
- **Execution Manifest** (`docs/plans/iterations/ITER-*.yaml`) — produced by PIN-02
- **GitHub Milestone** — produced by PIN-03
- **GitHub Issues** — produced by PIN-03

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
