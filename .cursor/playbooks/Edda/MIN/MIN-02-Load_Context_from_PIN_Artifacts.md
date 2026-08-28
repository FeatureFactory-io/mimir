# Activity: Load Context from PIN Artifacts

**Activity ID**: 179
**Order**: 2
**Phase**: None
**Dependencies**: Predecessor: Activity 178 (Activate Iteration)

## Description

Load Context from PIN Artifacts

## Guidance

## Purpose
Restore the distilled context that Plan Iteration already built, then derive and present the full execution queue. Pure pre-flight — no implementation, no GitHub mutations. This activity absorbs the sequencing responsibilities of the dropped 'Sequence from Manifest' activity: loading context and building the execution queue share the same actor (TL), the same input (the iteration manifest), and the same exit condition (execution queue ready to dispatch).

Do NOT re-read SAO.md, BDD specs, or mockups from scratch.

## Part A — Load Context

### Step 1: Load the Milestone-Bound Manifest

Use the manifest path identified and locked in Activate Iteration. Do not re-select. Do not use `ls -t | head -1`.

```bash
cat {manifest_path_from_activate_iteration}   # already on disk; read it directly
```

Extract per scenario: `id`, `title`, `github_issue`, `parallel_group`, `codebase_footprint[]`, `context_map[]`, `do_not_do[]`, `checkpoint.command`, `checkpoint.log_story_command`, `feature_execution_graph` (nodes: `id`, `bpe`, `depends_on`, `footprint[]`, `gate`), `dependencies[]`, `feature_file_paths[]`, `system_dependencies[]`.

Verify that each scenario's `github_issue` is on the current milestone (cross-check with Activate Iteration's confirmed issue list). Any issue not in the milestone list → flag before proceeding.

### Step 2: Load Orient Summary
```bash
ls -t docs/plans/iterations/pin-orient-*.md 2>/dev/null | head -1
```
If none: first-iteration defaults (`velocity_trend: unknown`, `scope_risks: none`). Continue.
If found: read it. Extract velocity trend, scope risks, watch-fors.

### Step 3: Spot-Check Context Map
For 1-3 `context_map` entries per scenario:
```bash
wc -l {file}   # confirm file exists and has sufficient lines
```
Missing file → flag as potential sao_violation.

### Step 4: Check System Dependencies
For each `system_dependencies[]` item, verify it exists in the codebase. If absent: **STOP** and escalate before any implementation.

## Part B — Sequence

### Step 5: Parse Parallel Groups + Conflict Map
From the manifest: extract `parallel_groups` and `conflict_map`. Do not recompute — Plan Iteration Contract derived these from actual skeleton commits.

### Step 6: Check Dependency State Per Scenario
For each scenario, fetch each `dependencies[]` issue individually:
```bash
gh issue view {N} --json number,state,labels
```
Mark each **READY** (no deps, or all deps closed with status-done) or **BLOCKED**.

### Step 7: Build Execution Queue
Order: Group A → Group B → Group C. Within each group: READY before BLOCKED.

### Step 8: Output Execution Plan (Plan Mode)
Switch to Plan Mode. Present:

**Outer** — scenario dependency graph (Mermaid flowchart)

**Inner** — for each READY scenario, feature_execution_graph node dependencies

```
=== CONTEXT LOADED ===
Manifest:  {path} — bound to milestone #{milestone_number}
Orient:    {filename or "first iteration"} | velocity_trend: {value}
Scenarios: {N} total
System deps: {list or "none"}
Spot-check: {N}/{N} context_map refs confirmed

=== EXECUTION QUEUE ===
Groups: {N} | Ready: {N} | Blocked: {N}
{queue with nodes per scenario}
First ready nodes: {list}
Conflicts: {file shared by SN, SM — serialized}
Next: Execute (TL Dispatches Workers)
=======================
```

## Success Criteria
- Manifest loaded from the path locked in Activate Iteration (not re-selected)
- Every scenario's `github_issue` confirmed on the milestone
- All per-scenario fields extracted
- System dependencies verified; escalation if absent
- Parallel groups + conflict map parsed (not recomputed)
- Execution queue ordered; Mermaid diagrams presented

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
