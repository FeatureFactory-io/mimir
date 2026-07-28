# Activity: Load Context from PIN Artifacts

**Activity ID**: 179
**Order**: 2
**Phase**: None
**Dependencies**: None

## Description

Load Context from PIN Artifacts

## Guidance

## Purpose
Restore the distilled context that PIN already built. Do NOT re-read SAO.md, user_journey.md, mockups, or BDD specs from scratch — PIN-02 and PIN-03 already did that work.

## Steps

### Step 1: Load Orient Summary (from PIN-02)
```bash
ls -t docs/plans/iterations/pin-orient-*.md 2>/dev/null | head -1
```

**If no file found (first iteration of this feature):**
> No orient summary exists — this is the first iteration for this feature. Apply first-iteration defaults:
> - `velocity_trend`: unknown
> - `scope_risks`: none computed
> - `watch_fors`: none — no prior drift patterns
>
> Continue to Step 2. Do not stop.

**If file found:** read it. Extract: velocity trend, scope risks, watch-fors.

### Step 2: Load Execution Manifest (from PIN-03)
```bash
ls -t docs/plans/iterations/ITER-*.yaml 2>/dev/null | head -1
```

**If no file found:**
> **STOP.** No execution manifest found. PIN-03 (Contract) must be run before MIN can proceed. Return to PIN.

**If found:** load the most recent manifest matching this milestone. Extract per scenario:
- `id`, `title`, `github_issue`, `parallel_group`
- `codebase_footprint[]`
- `sao_sections[]`
- `context_map[]` (file + lines + note)
- `do_not_do[]`
- `checkpoint.command`
- `dependencies[]`
- `feature_file_paths[]` — paths to the `.feature` files for this scenario (used by MIN-06 to build the demo path)
- `system_dependencies[]` — infrastructure capabilities required (e.g. `notification_service`, `email_backend`); empty list = none

### Step 3: Spot-Check Context Map References
For each scenario, verify 1–3 `context_map` entries still exist:
```bash
wc -l {file}  # confirm file exists and has enough lines
```
If a file is missing or significantly shorter than expected: flag as potential `sao_violation` before executing that scenario.

> For new features, context_map entries point to reference patterns in existing code, not the new feature's own files. The spot-check is still valid — those reference files must exist.

### Step 4: Output Loaded Summary
```
=== CONTEXT LOADED ===
Orient:   {filename or "first iteration — no history"}
          velocity_trend: {value or "unknown"}
Manifest: ITER-{slug}.yaml — {N} scenarios
Scenarios:
  S{N} [{group}] {title} — #{issue} — {N} footprint files
  ...
System deps declared: {list or "none"}
Spot-check: {N}/{N} context_map refs confirmed
Next: MIN-03 Sequence from Manifest
======================
```

## Success Criteria
- Orient summary loaded OR first-iteration defaults applied (never a hard stop here)
- Execution manifest loaded (hard stop if missing — return to PIN)
- `feature_file_paths[]` and `system_dependencies[]` extracted per scenario
- Context map spot-check complete
- Ready to proceed to MIN-03

## Inputs
- **Orient Summary** (`docs/plans/iterations/pin-orient-{date}.md`) — produced by PIN-02 (optional; missing on first iteration is normal)
- **Execution Manifest** (`docs/plans/iterations/ITER-*.yaml`) — produced by PIN-03 (required)

> PIN-02 read the BDD specs and wrote the orient summary. PIN-03 read SAO.md and built the context maps, do-not-do lists, and skeletons.
> MIN-02 consumes those artifacts; it does not rebuild them.

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
