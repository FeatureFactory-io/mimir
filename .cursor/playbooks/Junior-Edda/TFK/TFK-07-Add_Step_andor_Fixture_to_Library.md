# Activity: Add Step and/or Fixture to Library

**Activity ID**: 193
**Order**: 7
**Phase**: Construction
**Dependencies**: Predecessor: Activity 192 (Establish E2E Infrastructure)
Successor: Activity 194 (Validate Test Health)

## Description

Add Step and/or Fixture to Library

## Guidance

# Add Step and/or Fixture to Library

## Objective

On-demand activity invoked when ESM-05 "Write Feature Files" or BPE cannot assemble a scenario from existing steps/fixtures. Creates new reusable step definitions and/or fixtures following library conventions, then updates the catalogs.

---

## Trigger

Called by other workflows when:
1. ESM-05 is writing a .feature and cannot find a matching step in the Step Library
2. BPE-04 needs a fixture preset that doesn't exist
3. A new domain area requires new step patterns
4. BPE-02 / MIN-04 declares a **PRF-*** row in SAO §17 but `tests/fixtures/llm_scripts/<prf-id>/` has no happy/reject script — add ScriptedLLM queue fixture(s) and catalog row (lane 1; pytest, not Gherkin)
5. DTA-19 / BPE adds a **TASK-*** golden row but `tests/fixtures/agent_tasks/<task-id>/` is missing input corpus, `expected.yaml`, or oracle `meta.yaml` — add frozen task fixture and catalog row (lane 4)
6. An existing PRF script needs a new **reject_*** variant (429, parse fail, HITL block, exhausted queue) per artifact 56 adverse sketch

## Process

### 1. Assess What's Needed

- Identify the gap: missing step pattern, missing fixture, or both
- Check if an existing step can be generalized/parameterized instead of creating a new one
- For PRF/TASK triggers: confirm the gap is fixture/oracle catalog — **not** a missing Gherkin step (see TFK-03 footnote)

### 2. Create Step Definition (if needed)

Follow library conventions:
- Place in appropriate domain file (navigation, forms, tables, auth, assertions)
- Use `data-testid` selectors
- Parameterize generically
- Log actions at INFO level

Skip step creation when trigger is PRF script or TASK golden only.

### 3. Create Fixture (if needed)

Follow library conventions:
- JSON for static reference data → `tests/fixtures/presets/`
- FactoryBoy for dynamic data → `tests/fixtures/factories/`
- **PRF ScriptedLLM queue** → `tests/fixtures/llm_scripts/<prf-id>/` (`happy.json`, `reject_*.json`)
- **TASK golden task** → `tests/fixtures/agent_tasks/<task-id>/` (`input/`, `expected.yaml`, `meta.yaml` per TFK-04 oracle schema)
- Document scope and dependencies

### 4. Update Catalogs

- Add new step to Step Library Catalog (GUI/AT only)
- Add new fixture to Fixture Library Catalog
- For agent fixtures: include `prf_id` / `task_id`, `oracle_type`, `pass_band`, `linked_test`, `sao_ref`

### 5. Verify

- Write a small test scenario using the new step/fixture
- Run it to verify it works
- Ensure existing tests are not broken
- PRF: run `pytest -m agent_proof` on the linked test; TASK: run `pytest -m quality` on the linked test (local or `agent-eval.yml` — not default PR until lane rules say so)

## Agent

None

## Skill

**Title**: AutoFixture and FactoryBoy Patterns
**Capability Domain**: Test Data Management
**Technology Stack**: factory-boy, pytest-fixtures, django-orm

**Title**: Gherkin Step Library Patterns
**Capability Domain**: BDD Step Engineering
**Technology Stack**: gherkin, behave, step-definitions

## Rules

None

## Artifacts Produced

None

## Artifacts Consumed

- **Behave Configuration** (Code) - Required
- **Step Library Catalog** (Document) - Required
- **Fixture Library Catalog** (Document) - Required
- **E2E Test Configuration** (Code) - Required

## Notes

No additional notes.
