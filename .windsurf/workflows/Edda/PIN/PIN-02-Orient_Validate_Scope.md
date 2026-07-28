# Activity: Orient & Validate Scope

**Activity ID**: 140
**Order**: 2
**Phase**: Construction
**Dependencies**: Predecessor: Activity 136 (Readiness Check)

## Description

Orient & Validate Scope

## Guidance

## Purpose
Build the iteration orient summary from the feature files identified in PIN-01, using historical lesson data where available. Establishes what the iteration will deliver and any risk flags.

## Session Resume Check
If `docs/plans/iterations/pin-orient-{today's date}.md` already exists → skip this activity, load it as the orient summary, proceed to PIN-03.

## Prerequisites
- `target_act` and `feature_files[]` from PIN-01
- `docs/lessons_learned/log.yaml` (may not exist on first iteration)

## Steps

### Step 1: Read Feature Specs
For each file in `feature_files[]`, read the BDD scenarios. Extract:
- Scenario titles
- Given/When/Then outlines (to understand scope boundaries)
- Tags if present (e.g. `@wip`, `@smoke`) — optional; scenarios with no tags are treated as fully eligible

### Step 2: Read Learning Log
```bash
cat docs/lessons_learned/log.yaml 2>/dev/null
```
If missing → first iteration. Create:
```bash
mkdir -p docs/lessons_learned
cat > docs/lessons_learned/log.yaml << 'EOF'
# Iteration learning log — append only
entries: []
EOF
```
If exists → read last 5 entries. Compute:
- **velocity_ratio trend**: improving / stable / degrading
- **dominant_drift**: most frequent signal type
- **footprint_accuracy trend**: improving / stable / degrading

### Step 3: Validate Scope
- If `velocity_ratio` degrading AND >2 scenarios: flag scope risk
- If `dominant_drift` was `footprint_violation` in 2+ of last 5: flag complexity risk

### Step 3b: Scope Bounding
Count total scenarios across all `feature_files[]`. Assess whether the full scope fits your effective context window:

- Estimate complexity: scan each scenario's step count and whether it touches new models, new pages, or new infrastructure.
- If the full scope feels manageable (scenarios are simple CRUD / UI checks with predictable footprints), proceed with all scenarios.
- If the scope is large **and** scenarios are complex (new models, cross-cutting concerns, unresolved system dependencies), ask:

> "This iteration has {N} scenarios. Some appear complex — would you like to:
> A) Proceed with all {N}
> B) Take a subset (tell me which scenarios or feature files)
> C) Split across multiple iterations — first file's scenarios now, remainder via a second PIN run"

Handle user response:
- **A**: Proceed with all scenarios; record `scope_override: confirmed` in orient summary
- **B**: Filter to the user-selected subset; record deferred scenarios in `scenarios_deferred[]`
- **C**: Take only the first feature file's scenarios (or user-specified first batch); record `scope_deferred_files[]`

If the full scope is simple and clearly manageable, do not ask — just proceed and note `scope_override: not_needed`.

### Step 4: Write Orient Summary
Create `docs/plans/iterations/pin-orient-{YYYYMMDD}.md`:
```markdown
## Orient Summary — {date}

### Target
Act: {target_act}
Feature files: {list}

### Scenarios in Scope
{list of scenario titles — after scope bounding}

### Scenarios Deferred
{list or "None"}

### Velocity Trend
{improving/stable/degrading or "First iteration"}

### Dominant Drift
{signal_type or "None — first iteration"}

### Scope Validation
{per-scenario risk flags or "No risks detected"}
```

## Success Criteria
- Orient summary written to `docs/plans/iterations/pin-orient-{date}.md`
- Scenarios in scope identified (after scope bounding — may be a subset of all feature file scenarios)
- Deferred scenarios recorded if scope was reduced
- Risk flags computed or noted as first iteration
- Ready for PIN-03

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
