# Activity: Build

**Activity ID**: 181
**Order**: 3
**Phase**: None
**Dependencies**: Predecessor: Activity 179 (Load Context & Sequence)
Successor: Activity 182 (Integrate & Gate)

## Description

Team Lead (advanced reasoning model) dispatches cheap-fast dr-dobbs worker subagents — one per `feature_execution_graph` node, one issue at a time. TL sequences, monitors, reviews NODE_PASS, and handles drift. TL never writes implementation code. Workers are stateless, single-node, disposable.

## Guidance

## Model Tiers — READ BEFORE STARTING

| Role | Model tier | Responsibility |
|------|-----------|----------------|
| **Team Lead (TL)** | Advanced reasoning model | Orchestrates queue, dispatches workers, reviews NODE_PASS, handles escalations — **no implementation** |
| **dr-dobbs (Worker)** | Cheap-fast model | Implements exactly one graph node per invocation, runs node gate, posts NODE_PASS, stops |

**TL law:** If you find yourself writing code, filling a stub, or running a feature test yourself — stop. That is dr-dobbs work. Dispatch a worker subagent.

---

## Step 1: Pick the Next READY Issue

From the execution queue (MIN-02 output), select the next READY scenario (all `dependencies[]` closed with `status-done`, respecting group order A → B → C).

If multiple READY scenarios are in the same parallel group and have no shared `conflict_map` entries: dispatch them concurrently.

Claim the scenario:

```bash
gh issue edit {N} --add-label "status-in-progress" --remove-label "status-queued"
gh issue comment {N} --body "<!-- EXECUTION_START -->
Started: {ISO8601_timestamp}
TL: dispatching graph nodes
<!-- /EXECUTION_START -->"
```

## Step 2: Read the Feature Execution Graph

```bash
gh issue view {N} --json number,title,body,labels
```

Parse `<!-- FEATURE_EXECUTION_GRAPH -->` from the issue body (fallback: `iteration_execution_manifest.scenarios.{SN}.feature_execution_graph`).

Extract all nodes: `id`, `bpe`, `depends_on`, `footprint[]`, `gate.command`, `gate.log_story_command`.

Identify the **first ready nodes**: those with no `depends_on`, or whose deps already show `NODE_PASS`.

## Step 3: Dispatch Worker Subagents (one per ready node)

For each ready node, assemble the dr-dobbs task prompt:

```
You are dr-dobbs — a cheap-fast implementation worker. Implement ONLY node {node_id} for GitHub issue #{N}.

1. Read the issue: gh issue view {N} --json number,title,body,labels
2. Assemble your guidance bundle per skill "Assemble Guidance Bundle" (your node from FEATURE_EXECUTION_GRAPH).
3. Implement only the files in this node's footprint[]: {footprint_list}
4. Fill raise NotImplementedError() stubs — do not change method signatures.
5. If this node introduces new Django models: run makemigrations && migrate before the gate.
6. Run gate: {gate.command}
   {gate.log_story_command if declared}
7. If exit 0: post NODE_PASS comment (template below) and stop.
8. If exit non-0: one targeted fix, retry gate once. PASS → post NODE_PASS. FAIL → post NODE_FAIL and stop.

NODE_PASS template:
<!-- NODE_PASS -->
node: {node_id}
gate: {command} — exit 0
commits: {sha list}
<!-- /NODE_PASS -->

NODE_FAIL template:
<!-- NODE_FAIL -->
node: {node_id}
gate: {command} — exit {code}
error: {last 10 lines of stderr}
<!-- /NODE_FAIL -->

Do NOT:
- Change method signatures or return types
- Touch files outside this node's footprint[]
- Add unplanned public methods
- Implement other nodes
- Proceed to the next node
- Redesign the skeleton
```

**Launch as a fresh Task subagent** — never resume a prior worker. Model: cheap-fast.

## Step 4: Monitor and Advance the Node Graph

Wait for the subagent to complete. Then:

**On NODE_PASS:**
- Mark node done on the issue Acceptance Criteria checklist (if present)
- Check which nodes are now unblocked (all `depends_on` now NODE_PASS)
- Dispatch fresh subagents for each newly unblocked node (Step 3)
- Continue until all nodes in the graph show NODE_PASS

**On NODE_FAIL:**
- This is the worker's second failure (worker already retried once internally)
- Apply drift protocol:

```bash
gh issue comment {N} --body "<!-- DRIFT -->
type: node_fail_after_retry
node: {node_id}
gate: {command}
error: {summary}
action: targeted fix dispatched
<!-- /DRIFT -->"
```

Dispatch one more targeted dr-dobbs subagent scoped narrowly to the failure (not the full node — just the broken line). If that also fails: **escalate**.

**On footprint violation (worker touched files outside node footprint[]):**
```bash
gh issue comment {N} --body "<!-- ESCALATE -->
type: footprint_violation
node: {node_id}
evidence: {filename} not in footprint[]
await_human_decision: true
<!-- /ESCALATE -->"
gh issue edit {N} --add-label "drift-escalated" --remove-label "status-in-progress"
```
Stop. Do not continue this issue until human responds.

**On time overrun (> 2× expected per node):** escalate with evidence.

## Step 5: Terminal Node — Handoff to MIN-04

When **all nodes** in the feature execution graph show `NODE_PASS`:

Post a handoff comment:
```bash
gh issue comment {N} --body "<!-- BUILD_COMPLETE -->
All nodes NODE_PASS.
Nodes: {node_id_list}
Ready for: MIN-04 Integrate & Gate
<!-- /BUILD_COMPLETE -->"
```

Then immediately begin MIN-04 (Integrate & Gate) for this issue. If parallel scenarios are running concurrently, MIN-04 can process one while MIN-03 continues dispatching nodes for others.

## Step 6: Advance the Queue

After each issue enters MIN-04: check whether any BLOCKED scenario is now unblocked (its dependency issues are closed `status-done`). If yes, move it to READY and dispatch it (Step 1).

The Build phase is complete when no issues remain in the execution queue (all are in Integrate & Gate or already closed).

---

## Drift Handling Reference

| Signal | Threshold | Action |
|--------|-----------|--------|
| node gate fail | first time | worker retries once internally |
| node gate fail after retry | second time | TL dispatches targeted fix subagent |
| node gate fail after TL fix | third time | ESCALATE |
| footprint violation | any | ESCALATE immediately |
| time overrun | > 2× per node | ESCALATE with evidence |
| 2+ absorbed signals same node | — | ESCALATE |

---

## Rules

Before dispatching any worker, read each Rule below (by slug) and embed the relevant constraint in the worker prompt. Do not rely on memory of the rule text.

Required:
- `do-skeletons-first`
- `do-test-first`
- `do-not-mock-in-integration-tests`
- `do-informative-logging`
- `do-assert-log-story`
- `do-write-concise-methods`
- `do-follow-commit-convention`
- `do-small-increments`
- `pytest`

## Success Criteria

- Model tiers respected: TL never wrote implementation code
- All graph nodes implemented via fresh dr-dobbs subagents (cheap-fast model)
- Each node gated; every terminal node has `NODE_PASS` posted on the issue
- `makemigrations && migrate` ran within any node that introduced a new Django model
- Parallel nodes dispatched concurrently where `conflict_map` allows
- Drift absorbed below threshold; escalations surfaced immediately
- All issues have `BUILD_COMPLETE` comment; ready for MIN-04

## Agent

**Name**: dr-dobbs

**Model tier**: cheap-fast (e.g. composer-2.5-fast or equivalent low-cost model)

**Role**: Implements exactly one `feature_execution_graph` node per invocation. Fills `raise NotImplementedError()` stubs within the declared `footprint[]`. Runs node gate. Posts `NODE_PASS` or `NODE_FAIL`. Stops.

**Authority:**
- Can decide: implementation details within a method signature, which existing utility to call within footprint, order of operations within a method, one targeted retry of a failed gate
- Must escalate: gate fails after retry, file outside footprint needs touching, new public method not in skeleton, `do_not_do[]` constraint would be violated
- Cannot do: change signatures, create files outside footprint, claim more than one node, pick up next node without TL assignment

**Team Lead (Orchestrator):**

**Model tier**: advanced reasoning model (e.g. claude-opus-5-thinking-high or equivalent)

**Role**: Reads execution queue, dispatches dr-dobbs subagents, monitors NODE_PASS/NODE_FAIL, handles escalations, advances the node graph. Writes no implementation code.

## Skill

- **Assemble Guidance Bundle** (used by dr-dobbs workers)
- **Pytest Log Story Assertions** (used by dr-dobbs workers when `log_story_command` declared)

## Artifacts Produced

None

## Artifacts Consumed

None

## Notes

No additional notes.
