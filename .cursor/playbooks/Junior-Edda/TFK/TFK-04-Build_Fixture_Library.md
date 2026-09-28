# Activity: Build Fixture Library

**Activity ID**: 190
**Order**: 4
**Phase**: Elaboration
**Dependencies**: Predecessor: Activity 189 (Build Step Library)
Successor: Activity 191 (Wire CICD Integration)

## Description

Build Fixture Library

## Guidance

# Build Fixture Library

## Objective

Create a shared library of test fixtures at multiple scopes (session, suite, test) using both JSON fixtures and FactoryBoy. Establish patterns for context passing, AutoFixture support, and fixture presets.

---

## Process

### 1. Fixture Organization

```
tests/fixtures/
├── seed.json                # Base data loaded once per session
├── presets/
│   ├── team_preset.json     # A group with set of users with specific roles
│   ├── project_preset.json  # Project with workflows, activities, artifacts
│   └── empty_preset.json    # Clean slate for isolation tests
├── factories/
│   ├── user_factory.py      # FactoryBoy user factory
│   ├── model_factories.py   # Domain model factories
│   └── __init__.py
├── autofixture/
│   └── fixture_creator.py   # AutoFixture helper
├── llm_scripts/             # Lane 1 — ScriptedLLM queues (when SAO §17 applies)
│   └── <prf-id>/
│       ├── happy.json
│       └── reject_*.json
└── agent_tasks/             # Lane 4 — frozen TASK-* corpora (when SAO §17 applies)
    └── <task-id>/
        ├── input/
        ├── expected.yaml
        └── meta.yaml
```

### 2. When to Use JSON vs FactoryBoy

| Use JSON fixtures when... | Use FactoryBoy when... |
|---------------------------|------------------------|
| Data is static reference data | Data needs to be parameterized per test |
| Loaded once per session (seed data) | Created dynamically with variations |
| Represents "the world as it is" | Represents "arrange" step of a specific test |
| Shared across many tests unchanged | Tests need unique data to avoid collisions |

### 3. Fixture Scopes

- **Session-level** (`seed.json`): loaded once via `loaddata` in `before_all`
- **Suite-level** (`presets/`): loaded for a specific group of related tests
- **Test-level** (FactoryBoy): created per test function, rolled back after

### 4. AutoFixture Support

For lazy fixture creation — create model instances with sensible random defaults when you don't care about specific field values.

---

## Idempotent behave Given Steps (Background + scenario)

When a feature file uses `Background:` to seed reference entities and scenarios add their own `Given` steps for the same natural keys (slug, code, username, composite unique):

1. Step definitions MUST use `get_or_create` or update-in-place — never blind `Model.objects.create()` for keys Background may already insert.
2. Document in the Step Library Catalog which Givens are idempotent vs create-only.
3. On `IntegrityError` during AT, first suspect double-seeding — fix the step, not the scenario order.

Reference: Skill 45 Pattern 5 (Behave-Django BDD Runner).

---

## Fixture Library Catalog — agent eval entries

When SAO §17 applies, extend the **Fixture Library Catalog** with two agent-specific roots. Skip catalog rows when §17 is N/A.

### `llm_scripts/<prf-id>/` (lane 1 — PRF integration proof)

| Catalog field | Purpose | Example |
|---------------|---------|---------|
| `prf_id` | Artifact 56 row id | `PRF-SC01-04` |
| `path` | Relative to `tests/fixtures/` | `llm_scripts/PRF-SC01-04/happy.json` |
| `variant` | happy / reject_* | `reject_429` |
| `turn_count` | Expected ScriptedLLM queue length | `3` |
| `linked_test` | pytest module | `tests/integration/agent/test_prf_sc01_04.py` |
| `sao_ref` | SAO §17 checkbox | `PRF-SC01-04 dual-tool mode` |

**File shape:** ordered JSON array of LLM response strings or objects consumed by CAP-004 ScriptedLLM. Reject variants must exhaust the queue with an explicit error — never silent empty fallback (see TFK-08).

### `agent_tasks/<task-id>/` (lane 4 — TASK golden eval)

| Catalog field | Purpose | Example |
|---------------|---------|---------|
| `task_id` | Artifact 56 Part 4.6 row | `TASK-SC02-01` |
| `path` | Relative to `tests/fixtures/` | `agent_tasks/TASK-SC02-01/` |
| `sc_xx` | Scenario family | `SC-02` |
| `fixture_ref` | Frozen input corpus subpath | `input/corpus.json` |
| `oracle_type` | Assert strategy | `set_recall` / `graph_diff` / `schema_bounds` |
| `pass_band` | Promotion thresholds | `min_recall: 0.95`, `max_extras: 1` |
| `n_runs` | Stability runs at temp=0 | `3` |
| `linked_test` | pytest module | `tests/integration/agent/test_task_sc02_01.py` |

**Oracle schema (`expected.yaml` / `meta.yaml`):**

| Field | Required | Description |
|-------|----------|-------------|
| `task_id` | yes | Matches catalog row |
| `oracle_type` | yes | Drives assert helper selection |
| `expected_names` | set_recall | Ground-truth name set |
| `expected_graph` | graph_diff | Nodes/edges or ops diff spec |
| `schema_bounds` | schema_bounds | JSON schema or field bounds |
| `pass_band` | yes | min_recall, max_extras, max_latency_ms, etc. |
| `n_runs` | promotion | Runs before certifying band |
| `provider_pin` | optional | Model id for scoreboard (lane 3/4) |

Document dependencies (seed preset, factory hooks) in catalog notes. TFK-07 adds new rows when BPE/MIN introduces a PRF script or TASK golden not yet cataloged.

## Agent

None

## Skill

**Title**: Agent Task Eval

**Title**: AutoFixture and FactoryBoy Patterns
**Capability Domain**: Test Data Management
**Technology Stack**: factory-boy, pytest-fixtures, django-orm

**Title**: Behave-Django BDD Runner
**Capability Domain**: BDD Test Execution
**Technology Stack**: behave, django, behave-django

## Rules

None

## Artifacts Produced

- **Fixture Library Catalog** (Document) - Required

## Artifacts Consumed

- **SAO.md § Test Strategy** (Document) - Required
- **Behave Configuration** (Code) - Required

## Notes

No additional notes.
