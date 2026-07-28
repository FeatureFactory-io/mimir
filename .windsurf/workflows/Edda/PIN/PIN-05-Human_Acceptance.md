# Activity: Human Acceptance

**Activity ID**: 154
**Order**: 5
**Phase**: Construction
**Dependencies**: Predecessor: Activity 150 (Publish)

## Description

Human Acceptance

## Guidance

## Purpose
Verify CLAUDE.md iteration protocol is current, obtain explicit human approval, and deliver the single activation instruction for MIN. This is the final gate — do not proceed without explicit human go.

**STOP — mandatory human gate.**

## Prerequisites
- All skeleton commits on iteration branch
- Execution manifest finalized (`ITER-*.yaml`)
- GitHub/GitLab Milestone + Issues published (PIN-04 complete)

## Steps

### Step 1: Verify CLAUDE.md Iteration Protocol
Read the `## Iteration Protocol`, `## Drift Handling`, `## Session Resume Protocol`, and `## Authority Model (Jedao)` sections of CLAUDE.md. Verify they match `doctrine_version` in the manifest.

Required sections:
- **Iteration Protocol** — references `<!-- MANIFEST -->` block, `status-queued`, BPE-02 → BPE-05
- **Drift Handling** — matches manifest `drift_thresholds` (absorbed: checkpoint_fail retry once; escalated: footprint_violation, method_explosion, sao_violation, checkpoint_fail_after_retry)
- **Session Resume Protocol** — find `status-in-progress` → re-run checkpoint → PASS: close and continue / FAIL: retry

If any section missing or thresholds do not match: update CLAUDE.md and commit:
```bash
git commit -m "docs(claude): sync iteration protocol to doctrine v2.0"
```

### Step 2: Present Review Summary
```
=== PIN COMPLETE — REVIEW REQUIRED ===

Iteration: {iteration_goal}
Scenarios: {N} | Groups: {A,B,...}

{for each scenario:}
  S{N} [{group}] {title}
    Checkpoint: {command}
    Footprint:  {N} files
    Depends on: {deps or "none"}

Conflict map:
  {file} → [{S_N}, {S_M}] (serialized)
  {or "No conflicts — all scenarios parallel"}

Platform: {github|gitlab}
Milestone: #{N}

CLAUDE.md protocol: {current / updated at {timestamp}}

Activate MIN with: "Work on Milestone #{N}"
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
- Re-sequencing needed → return to PIN-03 Step 8–9 to revise conflict map
- Drop S{N} → close issue (won't-fix), remove from manifest, update Milestone description

## Success Criteria
- CLAUDE.md iteration protocol is current
- Explicit human go/no-go decision obtained
- If go: approval comment posted on GitHub/GitLab
- Human has the activation instruction: "Work on Milestone #{N}"

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
