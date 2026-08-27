# Activity: Activate Iteration

**Activity ID**: 178
**Order**: 1
**Phase**: None
**Dependencies**: Successor: Activity 179 (Load Context & Sequence)

## Description

Activate the iteration from a single human trigger. Verify PIN artifacts exist, find and uniquely identify the requested milestone, confirm every issue is open and queued, and assert a clean execution slate before any work begins.

## Guidance

**Trigger:** user says "Work on milestone `<name or #N>`"

## Step 0: Verify PIN Artifacts Exist — do this FIRST

```bash
ls docs/plans/iterations/ITER-*.yaml 2>/dev/null | head -1
```

If no file found:
> **STOP.** No execution manifest found. The Plan Iteration (PIN) workflow must run first to produce the manifest, skeletons, and milestone. Tell the user: "Run PIN on this feature first, then invoke MIN."

If found: proceed.

## Step 1: Find the Milestone

```bash
gh milestone list --json number,title,state | jq '.[] | select(.state == "open")'
```

Match the user's input (name substring or `#N`) to exactly one open milestone. Multiple matches or no match → stop and ask the user to clarify.

## Step 2: Confirm Issues and Sprint-Size Guard

Fetch each issue individually — never use list-all:

```bash
gh issue view {github_issue} --json number,title,labels,state
```

Confirm each is `open` with label `status-queued`. Report any discrepancy before proceeding.

**Sprint-size guard:**

```bash
gh api repos/{owner}/{repo}/milestones/{N} --jq '.open_issues'
```

If `open_issues > 15`:
> "This milestone has {N} open issues. Sprints above ~10 issues carry high drift risk. Consider splitting before running MIN. Proceed? (yes / no)"

Wait for explicit user confirmation before continuing.

## Step 3: Assert Clean Slate

```bash
gh issue list --milestone {N} --label "status-in-progress" --json number,title
```

If any issue has `status-in-progress` — prior session was interrupted. Resume from MIN-03 Build for that scenario:
- Re-run its last `gate.command` first
- PASS → close issue (`status-done`), continue queue
- FAIL → treat as first `test_failure`, apply one targeted retry before escalating

Only proceed to MIN-02 if no `status-in-progress` issue exists.

## Step 4: Output Activation Summary

```
=== MIN ACTIVATION ===
Manifest: ITER-{slug}.yaml ✓
Milestone: #{N} | {goal}
Issues:    {N} open, all status-queued
Size:      {ok | WARNING: {N} issues — user confirmed}
Slate:     clean
Next:      MIN-02 Load Context & Sequence
======================
```

## Success Criteria

- PIN manifest confirmed present before any GitHub call
- Milestone found and uniquely identified
- All issues confirmed `open` with `status-queued` (fetched one by one)
- Sprint-size warning shown if > 15 issues; user confirmed to proceed
- No dangling `status-in-progress` issue — or resume path taken
- Ready to proceed to MIN-02

## Inputs

- **Execution Manifest** (`docs/plans/iterations/ITER-*.yaml`) — produced by PIN-03
- **GitHub Milestone** — produced by PIN-03
- **GitHub Issues** — produced by PIN-03

## Agent

None — Team Lead (TL) runs this activity inline.

## Skill

None

## Rules

- **Follow Commit Convention** (`do-follow-commit-convention`)
- **Github Issues** (`do-github-issues`)

## Artifacts Produced

None

## Artifacts Consumed

None

## Notes

No additional notes.
