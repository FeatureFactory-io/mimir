# Activity: Sequence from Manifest

**Activity ID**: 180
**Order**: 3
**Phase**: None
**Dependencies**: Predecessor: Activity 179 (Load Context from PIN Artifacts)
Successor: Activity 181 (Execute)

## Description

Sequence from Manifest

## Guidance

**Sequencing (authoritative):** Predecessor = Load Context from PIN Artifacts (Activity 179 / MIN-02).

## Purpose
Derive the execution queue from the PIN-built manifest. Do NOT rebuild the dependency graph or conflict map — PIN-02 already computed them from actual skeleton commits. This activity reads and validates.

## Steps

### Step 1: Parse Parallel Groups and Conflict Map
From the loaded ITER-*.yaml manifest (MIN-02 output):
- Extract `parallel_groups`: e.g. `A: [S1, S3]`, `B: [S2]`
- Extract `conflict_map`: e.g. `mcp_integration/tools.py: [S1, S2]`

> The conflict map was derived by PIN-02 from actual `git diff --name-only` per skeleton commit. Do not recompute it.

### Step 2: Check Dependency State
For each scenario, check `dependencies[]`. Get each dependency issue one at a time:
```bash
gh issue view {dependency_issue_number} --json number,state,labels
```
Mark scenario as:
- **READY** — no dependencies, or all dependency issues closed with `status-done`
- **BLOCKED** — one or more dependency issues still open

### Step 3: Build Ordered Execution Queue
Order: Group A → Group B → Group C … Within each group, READY scenarios before BLOCKED.

```
[READY]   S1 [A] {title} — #{issue}
[READY]   S3 [A] {title} — #{issue}  (parallel with S1)
[BLOCKED] S2 [B] {title} — #{issue}  (waits for S1: status-done)
```

### Step 4: Switch to Plan Mode and Present Queue
Switch to **Plan mode**. Present **two-level** diagrams:

**Outer** — scenario dependencies (iteration graph):

```mermaid
flowchart LR
  S1["S1: {title}"] --> S2["S2: {title}"]
  S3["S3: {title}"]
```

**Inner** — for each READY scenario, `feature_execution_graph` node deps:

```mermaid
flowchart LR
  N1["N1 backend BPE-02"] --> N2["N2 frontend BPE-03"]
  N2 --> N3["N3 DoD BPE-06"]
```

Label parallel scenarios clearly. Note BLOCKED scenarios and unmet scenario-level dependencies.

### Step 5: Output Execution Plan
```
=== EXECUTION QUEUE ===
Groups: {N} | Scenarios: {N} ready, {N} blocked

Group A (parallel):
  [READY] S1 #{issue} — {title} — nodes: N1→N2→…→N5
  [READY] S3 #{issue} — {title} — nodes: …

Group B (after A):
  [BLOCKED] S2 #{issue} — {title} — waiting for S1

READY nodes (next to execute across ready scenarios):
  S1/N1-backend-service [BPE-02]
  S3/N1-backend-service [BPE-02]  (parallel scenarios OK; respect conflict_map)

Conflicts: {file} shared by {S_N, S_M} — serialized in groups
Next: MIN-04 Execute (one fresh subagent per ready node)
======================
```

## Success Criteria
- `parallel_groups` and `conflict_map` parsed from manifest (not recomputed)
- Each scenario dependency state checked via `gh issue view` (one at a time)
- Execution queue ordered correctly: group order + dependency order within groups
- Mermaid diagrams presented in Plan mode (scenario + inner graph for READY scenarios)
- READY **nodes** listed for MIN-04, not scenarios alone
- Ready to proceed to MIN-04

> The conflict map and parallel groups were established by PIN-02 from actual skeleton commits.
> MIN-03 reads and validates them — it does not recompute them.

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
