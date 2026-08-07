# Skill: Assemble Guidance Bundle

**Capability Domain**: EXECUTION_ORCHESTRATION  
**Technology Stack**: Cursor Agent / dr-dobbs subagent

## Overview

Deterministic recipe for MIN-04 (or a solo orchestrator) to build a **fresh subagent prompt** for one `feature_execution_graph` node. The worker implements **only that node** and exits on gate PASS.

Schema: artifact **Feature Execution Graph** (`feature-execution-graph-schema.md`).

## When to use

- MIN-04 before each `Task` / dr-dobbs invocation
- Solo BPE execution without PIN/MIN
- Copy-prompt flows that target a single graph node

## Input

1. **Node** — one element from `feature_execution_graph.nodes[]` (issue body, manifest embed, or standalone YAML)
2. **Handoff** — `NODE_PASS` comments / commit SHAs from `depends_on` predecessor nodes
3. **Scenario context** (when under PIN) — `codebase_footprint[]`, `do_not_do[]`, context map from issue or manifest

## Output prompt sections (in order)

### 1. Identity and scope

```
Assume dr-dobbs identity.
Implement ONLY node {node.id}: {node.title}.
Issue #{N} (if applicable). Do not list or implement other nodes.
Do not resume a prior subagent session.
```

### 2. Node contract

```yaml
id: {node.id}
bpe: {node.bpe}
footprint: {node.footprint}
depends_on: {node.depends_on}
gate.command: {node.gate.command}
gate.log_story_command: {node.gate.log_story_command}  # if present
```

### 3. Predecessor handoff

For each id in `depends_on`, include:

- Latest `<!-- NODE_PASS -->` comment for that node
- Commit SHA(s) from handoff

If a dependency lacks `NODE_PASS`, **STOP** — do not start this node.

### 4. Activity (node type spec)

Read and follow the full activity file:

`{guidance_bundle.activity}`

(e.g. `.cursor/playbooks/Edda/BPE/BPE-02-Implement_Backend.md`)

### 5. Rules

Before editing, **read** each rule in this playbook by slug (do not paraphrase from memory):

{guidance_bundle.rules[]}

### 6. Skills

Apply patterns from:

{guidance_bundle.skills[]}

### 7. Tests and log story

When `tests[]` or `log_story_rows[]` are set:

- Write/run behavior tests before implementation (red → green)
- Log-story tests in the **same slice** as behavior when `log_story_rows` present
- Use skill *Pytest Log Story Assertions* (`assert_log_story`)

### 8. Scenario guardrails (PIN / issue)

When available from issue or manifest:

- Context map subset relevant to this footprint
- Do-not-do list
- Do not touch files outside `node.footprint` (subset of scenario footprint)

### 9. Exit condition

```
Run gate.command (+ gate.log_story_command when declared).
On exit 0: post <!-- NODE_PASS --> with node id, gate, commits.
Stop. Do not pick up the next node — orchestrator assigns it.
```

On gate FAIL: one targeted retry per drift protocol; escalate on second failure.

## Orchestrator responsibilities (not the worker)

- Parse `<!-- FEATURE_EXECUTION_GRAPH -->` from issue body (fallback: `iteration_execution_manifest.scenarios.SN`)
- Compute `ready_nodes` where all `depends_on` have `NODE_PASS`
- Respect iteration `parallel_groups` and `conflict_map` across scenarios
- Launch **new** subagent per node (`no resume`)
- After all nodes `NODE_PASS`, run scenario terminal checkpoint and close issue
- Invoke BPE-07 per feature when all scenarios for that feature are green

## Anti-patterns

- One subagent for multiple nodes or “BPE-02 through BPE-05”
- Worker continuing to next node without orchestrator
- Gate pass without `NODE_PASS` comment
- Behavior-only green when `log_story_command` is declared
