# Activity: Human Acceptance

**Activity ID**: 154
**Order**: 5
**Phase**: Construction
**Dependencies**: Predecessor: Activity 150 (Publish)

## Description

Human Acceptance

## Guidance

## Purpose
Verify CLAUDE.md iteration protocol sections are current, obtain explicit human approval, and deliver the single activation instruction for MIN. This is the final gate — do not proceed without explicit human go.

**STOP — mandatory human gate.**

## Prerequisites
- All skeleton commits on iteration branch
- Execution manifest finalized (`ITER-*.yaml`) with `milestone_number` populated
- GitHub/GitLab Milestone + Issues published (PIN-04 complete)

## Steps

### Step 1: Verify CLAUDE.md Iteration Protocol Sections

Read the `## Iteration Protocol`, `## Drift Handling`, `## Session Resume Protocol`, and `## Authority Model` sections of CLAUDE.md.

Required sections must exist and contain:
- **Iteration Protocol** — references `<!-- MANIFEST -->` block, `status-queued`, fresh subagent per `feature_execution_graph` node with pytest gates
- **Drift Handling** — absorbed and escalated thresholds (checkpoint_fail retry once; escalate on footprint_violation, method_explosion, sao_violation)
- **Session Resume Protocol** — find `status-in-progress` → re-run checkpoint → PASS: close and continue / FAIL: retry
- **Authority Model** — can-decide / must-escalate / cannot-do bounds for the iteration runner

If any section is missing or substantially absent: update CLAUDE.md and commit:
```bash
git commit -m "docs(claude): sync iteration protocol to current MIN workflow"
```

Do NOT compare against a `doctrine_version` field in the manifest — protocol version is managed by the Edda playbook release, not the manifest.

### Step 2: Present Review Summary
```
=== PIN COMPLETE — REVIEW REQUIRED ===

Iteration: {iteration_goal}
Milestone: #{milestone_number} — {milestone_title}
Scenarios: {N} | Groups: {A,B,...}

{for each scenario:}
  S{N} [{group}] {title}
    Checkpoint: {command}
    Graph nodes: {N} (BPE-02...06)
    Footprint:  {N} files
    Depends on: {deps or "none"}

Sample: review one scenario's feature_execution_graph in Plan mode

Conflict map:
  {file} -> [{S_N}, {S_M}] (serialized)
  {or "No conflicts — all scenarios parallel"}

Platform: {github|gitlab}
Milestone: #{milestone_number}
CLAUDE.md protocol: {current / updated at {timestamp}}

Activate MIN with: "Work on Milestone #{milestone_number}"
======================================
```

### Step 3: Await Human Decision

**GO** — "Approved" or "Work on Milestone #{N}"
```bash
# GitHub:
gh issue comment {first_issue} --body "PIN approved at {timestamp}. MIN authorized."
# GitLab:
glab issue note {first_issue} --message "PIN approved at {timestamp}. MIN authorized."
```

**NO-GO options:**
- Skeleton issue on S{N} → return to PIN-03 for that scenario only
- Re-sequencing needed → return to PIN-03 Step 8-9 to revise conflict map
- Drop S{N} → close issue (won't-fix), remove from manifest, update Milestone description

## Success Criteria
- CLAUDE.md iteration protocol sections are current (no doctrine_version comparison)
- Explicit human go/no-go decision obtained
- If go: approval comment posted on GitHub/GitLab
- Human has the activation instruction with the concrete milestone number

## Rules
- Never skip this gate regardless of time pressure
- If human is unavailable: pause PIN, do not proceed to MIN
- A no-go with a fix takes minutes; a bad MIN run wastes an hour

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
