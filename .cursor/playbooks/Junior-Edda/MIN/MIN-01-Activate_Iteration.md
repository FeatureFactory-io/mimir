# Activity: Activate Iteration

**Activity ID**: 178
**Order**: 1
**Phase**: None
**Dependencies**: Successor: Activity 179 (Load Context from PIN Artifacts)

## Description

Activate Iteration

## Guidance

## Purpose
Activate the iteration from a single human trigger. Confirm the correct PIN manifest exists for the requested milestone, validate PIN readiness (no contradictory or non-executable scenarios), assert every issue is open and queued, and declare a clean execution slate.

**Trigger:** user says "Work on Milestone #N" or "Work on Milestone <name>"

## Step 0 — Locate Milestone-Bound Manifest (do this FIRST)

Find the manifest using the `milestone_number` or `milestone_title` fields written by the Publish activity in Plan Iteration. Do NOT use "newest file" or `ls -t | head -1`.

```bash
# When user provides a milestone number (#N):
grep -l "milestone_number: {N}" docs/plans/iterations/ITER-*.yaml 2>/dev/null

# When user provides a milestone name or fragment:
grep -rl "milestone_title:.*{title_fragment}" docs/plans/iterations/ITER-*.yaml 2>/dev/null
```

If no matching manifest:
> **STOP.** No manifest bound to this milestone. Tell user: "Run Plan Iteration for milestone '{name}' first, then invoke Manage Iteration."

If `milestone_number: null` (or field absent) in the matched file: the Publish activity did not complete its manifest update. Tell user: "Plan Iteration Publish step did not write the milestone number back to the manifest. Re-run Publish Step 5, then invoke Manage Iteration."

If multiple matches: confirm with user which manifest to use.

Record the selected manifest path. All subsequent steps use this file only.

## Step 1 — Find and Lock the Milestone
```bash
gh milestone list --json number,title,state | jq '.[] | select(.state == "open")'
```
Match to exactly one open milestone. Store `{milestone_number}` and `{milestone_title}`. Multiple matches or no match → stop and ask user to clarify.

Cross-check: confirm the manifest's `milestone_number` matches `{milestone_number}` AND `milestone_title` matches `{milestone_title}`. Any mismatch → stop and report.

## Step 2 — PIN Readiness Validation

Before touching any issue, validate that the manifest scenarios are executable:

```bash
cat {selected_manifest} | grep -A1 'feature_file_paths' | grep '\.feature'
```

For each `feature_file_paths[]` entry, verify:
- [ ] The `.feature` file exists on disk
- [ ] Each `Scenario:` title is unique within that file
- [ ] URLs referenced in steps are consistent (flag alternating paths as a spec conflict)
- [ ] No scenario step is irreducibly vague — flag and ask user before proceeding

If any conflict or ambiguity is found:
> **STOP.** List each conflict with file + line reference. Tell user: "Plan Iteration produced contradictory or non-executable scenarios. Reconcile these before Manage Iteration can run."

Do not proceed past this step with unresolved spec conflicts.

## Step 3 — Confirm Issues + Sprint-Size Guard
Fetch each issue one at a time:
```bash
gh issue view {github_issue} --json number,title,labels,state
```
Confirm each is `open` with `status-queued`. Report discrepancies.

Sprint-size guard:
```bash
gh api repos/{owner}/{repo}/milestones/{N} --jq '.open_issues'
```
If `open_issues > 15`: warn and require explicit user confirmation before continuing.

## Step 4 — Assert Clean Slate
```bash
gh issue list --milestone {N} --label "status-in-progress" --json number,title
```
If any `status-in-progress` exists: prior session interrupted. Re-run its last `gate.command`. PASS → close issue, continue. FAIL → one retry → escalate.

## Step 5 — Verify Iteration Branch
```bash
git branch -a | grep "iteration/{milestone-slug}"
```
If absent:
> **STOP.** Tell user: "Plan Iteration Contract step did not create an iteration branch. Re-run Contract Step 1 or create the branch manually before invoking Manage Iteration."

Check out the iteration branch:
```bash
git checkout iteration/{milestone-slug}
```

## Step 6 — Output Activation Summary
```
=== ACTIVATION ===
Manifest:  {selected_manifest} (milestone_number: {N}, milestone_title: {title})
Milestone: #{N} | {goal}
Branch:    iteration/{slug}
Issues:    {N} open, all status-queued
Size:      {ok | WARNING: {N} issues — user confirmed}
Spec:      {N} feature files checked, {conflicts} conflicts, {vague} vague steps
Slate:     clean
Next:      Load Context from PIN Artifacts
==================
```

## Success Criteria
- Manifest located by `milestone_number` or `milestone_title` field (not by file order)
- `milestone_number` is a concrete integer in the matched manifest (not null or absent)
- Manifest `milestone_number` + `milestone_title` cross-checked against the live milestone
- PIN readiness validation passed (no unresolved spec conflicts or vague steps)
- Iteration branch confirmed and checked out
- All issues confirmed open with `status-queued` (fetched individually)
- Sprint-size warning shown if > 15 issues; user confirmed
- No dangling `status-in-progress`, or resume path taken

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
