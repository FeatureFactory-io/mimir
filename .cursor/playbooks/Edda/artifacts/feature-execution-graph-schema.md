# Feature Execution Graph — Schema

**Artifact type**: Schema reference  
**Produced by**: BPE-01 Step 6G (Plan Feature)  
**Consumed by**: MIN-04 (Execute), solo orchestrator, copy-prompt flows

## Purpose

Define the **feature-level** execution graph: ordered nodes tagged with BPE activity types (`BPE-02`…`BPE-06`), dependencies, footprint slices, and pytest/`make` gates. One graph per feature or PIN scenario.

This is the **inner** graph. The **outer** graph is the **iteration execution manifest** (`ITER-*.yaml` from PIN-03), which embeds each scenario’s `feature_execution_graph`.

## Two-level naming

| Level | Root key / wrapper | Producer | Store |
|-------|---------------------|----------|-------|
| Feature | `feature_execution_graph` | BPE-01 | Issue body `<!-- FEATURE_EXECUTION_GRAPH -->`, or `docs/plans/{FEAT}-feature-execution-graph.yaml` |
| Iteration | `scenarios.{SN}.feature_execution_graph` | PIN-03 | `docs/plans/iterations/ITER-*.yaml`, milestone `<!-- MANIFEST -->` |

## Comment wrappers (issue body)

```html
<!-- FEATURE_EXECUTION_GRAPH -->
feature_execution_graph:
  nodes: [...]
<!-- /FEATURE_EXECUTION_GRAPH -->
```

## Node handoff (execution comments)

When a node gate passes, post:

```html
<!-- NODE_PASS -->
node: N2-backend-views
gate: pytest tests/integration/test_foo_views.py -x — exit 0
commits: abc1234
<!-- /NODE_PASS -->
```

## YAML schema

```yaml
feature_execution_graph:
  feature_ref: "{FEAT-SCREEN-ID or scenario id}"   # optional
  nodes:
    - id: N1-backend-service          # unique within this graph
      title: "Backend — FooService"
      bpe: BPE-02                     # BPE-02 | BPE-03 | BPE-04 | BPE-05 | BPE-06
      depends_on: []                  # other node ids in this graph
      footprint:
        - methodology/services/foo_service.py
        - tests/unit/test_foo_service.py
      tests:
        - test_create_foo_happy
        - test_create_foo_log_story_happy
        - test_create_foo_log_story_reject
      log_story_rows:                 # optional; ids matching Section E beats
        - LoginView.post:entry
        - LoginView.post:branch
      gate:
        command: "pytest tests/unit/test_foo_service.py -x"
        log_story_command: "pytest tests/unit/test_foo_service.py -k log_story -x"  # when log_story_rows set
      guidance_bundle:
        activity: BPE/BPE-02-Implement_Backend.md
        rules:
          - do-skeletons-first
          - do-test-first
          - do-assert-log-story
        skills:
          - Django Backend Implementation Patterns
          - Pytest Log Story Assertions

    - id: N2-frontend-form
      title: "Frontend — create form"
      bpe: BPE-03
      depends_on: [N1-backend-service]
      footprint:
        - templates/foo/form.html
      gate:
        command: "pytest tests/integration/test_foo_views.py -x"
      guidance_bundle:
        activity: BPE/BPE-03-Implement_Frontend.md
        rules:
          - do-semantic-versioning-on-ui-elements
        skills:
          - Django + HTMX Frontend Implementation Patterns

    - id: N3-acceptance-tests
      title: "Feature acceptance tests"
      bpe: BPE-04
      depends_on: [N2-frontend-form]
      gate:
        command: "make test-at"
      guidance_bundle:
        activity: BPE/BPE-04-Implement_Feature_Acceptance_Tests.md
        rules:
          - do-not-mock-in-integration-tests
        skills:
          - Behave-Django BDD Runner

    - id: N4-e2e-journey
      title: "Journey certification"
      bpe: BPE-05
      depends_on: [N3-acceptance-tests]
      gate:
        command: "make test-e2e"
      guidance_bundle:
        activity: BPE/BPE-05-Implement_Journey_Certification_Tests.md
        skills:
          - Playwright Semantic Naming for UI Testing

    - id: N5-definition-of-done
      title: "Definition of Done"
      bpe: BPE-06
      depends_on: [N4-e2e-journey]
      gate:
        command: "pytest tests/ -x --ignore=tests/e2e"
      guidance_bundle:
        activity: BPE/BPE-06-Check_Definition_of_Done.md
        rules:
          - do-test-first
          - do-assert-log-story
```

## Field reference

| Field | Required | Notes |
|-------|----------|-------|
| `id` | yes | Stable slug; used in `depends_on` and `NODE_PASS` |
| `title` | yes | Human-readable node label |
| `bpe` | yes | Node type spec: `BPE-02`…`BPE-06` |
| `depends_on` | yes | List of node ids; empty for roots |
| `footprint` | yes | Subset of scenario `codebase_footprint[]`; worker may touch only these paths |
| `tests` | when BPE-02/03 | Test names or paths the gate proves |
| `log_story_rows` | when Section E populated | Beat references from Log Story Script |
| `gate.command` | yes | **pytest or make only** — human-runnable |
| `gate.log_story_command` | when log_story_rows | Same commit as behavior green |
| `guidance_bundle.activity` | yes | Path to BPE activity file under playbook root |
| `guidance_bundle.rules` | yes | Rule slugs; worker must read each by slug |
| `guidance_bundle.skills` | recommended | Skill titles from playbook |

## Rules

- Prefer **4–8 nodes** per feature; split large backend work into multiple `BPE-02` nodes, not one mega-node.
- Every graph must include at least one `BPE-02` node and one terminal `BPE-06` node.
- `depends_on` enforces layer order (backend → frontend → AT → E2E → DoD). Skip node kinds not in scope (e.g. no UI → omit `BPE-03`).
- Terminal scenario `checkpoint.command` in the iteration manifest should match the **BPE-06** node’s `gate.command` (rollup).
- Do **not** use custom Python gate scripts — pytest/`make` strings only.

## Embedding in iteration execution manifest

PIN-03 Step 11 nests the graph under each scenario (existing fields unchanged):

```yaml
scenarios:
  S1:
    title: "..."
    parallel_group: A
    skeleton_commit: "..."
    codebase_footprint: [...]
    feature_execution_graph:
      nodes: [...]   # full graph from BPE-01 Step 6G
    checkpoint:
      command: "..."              # typically N5 (BPE-06) gate.command
      log_story_command: "..."    # when applicable
    dependencies: []
```

## Solo feature (no PIN/MIN)

Write standalone file:

`docs/plans/{FEAT}-feature-execution-graph.yaml`

Parent agent acts as orchestrator: fresh subagent per ready node, same gates and `NODE_PASS` protocol. Run BPE-07 when all nodes pass.

## Related artifacts

- **Implementation Plan Template** — Section G summarizes this graph in prose plans
- **assemble-guidance-bundle** skill — builds worker prompt from a node
- **BPE-02…BPE-06** — node type specifications referenced by `guidance_bundle.activity`
