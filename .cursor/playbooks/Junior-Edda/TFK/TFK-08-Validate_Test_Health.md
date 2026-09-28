# Activity: Validate Test Health

**Activity ID**: 194
**Order**: 8
**Phase**: Construction
**Dependencies**: Predecessor: Activity 193 (Add Step and/or Fixture to Library)
Successor: Activity 195 (Prepare Test Report)

## Description

Validate Test Health

## Guidance

# Validate Test Health

## Objective

Periodic health check of the test suite: analyze coverage quality (not just quantity), flag anti-patterns, identify tests that need strengthening, and verify all test levels pass.

---

## Process

### 1. Run Coverage Analysis

```bash
make test-coverage
```

Review coverage report, but remember: **coverage is meaningless without quality**.

### 2. Quality Audit — Flag Anti-Patterns

Check for typical mistakes:

**Useless Tests:**
- Testing default Model methods (`model.save()`, `model.delete()`, `model.__str__()`)
- Testing Django auto-generated views without custom logic
- Tests that only check return codes without verifying side effects

**Testing Implementation, Not Behavior:**
- Test checks `save_changes()` returns OK but never verifies changes actually persisted
- Test is tightly coupled to implementation details

**Fat Controller Signal:**
- Logic in views/controllers instead of services → tests are hard to write
- Guideline: Services do the thinking → Views package and provide formatted data → Templates render it

**Mocking Violations:**
- Any mock/patch in integration tests → violation of no-mock rule

### 3. Verify All Test Levels Pass

```bash
make test          # unit + integration
make test-at       # acceptance
make test-e2e      # E2E (if staging available)
```

When SAO §17 applies:

```bash
make test-agent-proof    # lane 1 (when AGENTS_ENABLED=true)
make test-agent-live     # lane 3 (nightly / manual)
make test-agent-quality  # lane 4 (promotion band)
```

### 4. Produce Health Summary

Categorize findings as CRITICAL / WARNING / INFO.

---

## Agent eval health audit (when SAO §17 applies)

Skip this subsection when SAO §17 is N/A.

### FakeLLM / ScriptedLLM script hygiene

| Check | Severity | Action |
|-------|----------|--------|
| FakeLLM or test double returns `[]` / empty string on queue exhaustion | CRITICAL | Replace with explicit raise; add `reject_exhausted` script variant |
| Script turn count < PRF test's expected agent loop iterations | WARNING | Extend `llm_scripts/<prf-id>/happy.json` |
| Live LLM used in `@agent_proof` test | CRITICAL | Move to `@live_llm` or switch to ScriptedLLM |
| `assert_agent_story` beats missing for declared PRF row | CRITICAL | Add happy/reject test per rule `do-assert-agent-story` |

### Tool / domain mocks in `@agent_proof`

| Check | Severity | Action |
|-------|----------|--------|
| `@patch` on ToolExecutor, broker, or domain service in `@agent_proof` | CRITICAL | Remove patch — lane 1 requires real DB + real tool registry |
| Asserting assistant chat prose instead of trace beats | WARNING | Refactor to `assert_agent_story` control-plane keys |
| Lane 2 deterministic test uses ScriptedLLM | INFO | Use plain pytest — no LLM for D0/parse/validate |

Carve-out: **only CAP-004 ScriptedLLM** may stand in for the LLM in integration tests (rule `do-not-mock-in-integration-tests` ALTER).

### PRF coverage vs SAO §17

Build a matrix from SAO §17 PRF checkbox table vs repo:

| SAO §17 PRF row | `llm_scripts/` present | `@agent_proof` test | happy + reject | Status |
|-----------------|------------------------|---------------------|----------------|--------|
| e.g. PRF-SC01-04 | yes/no | yes/no | yes/no | PASS / GAP |

**CRITICAL gaps:** in-scope PRF row with no linked test or missing reject variant when artifact 56 marks adverse.

**WARNING gaps:** test exists but catalog row in Fixture Library missing `sao_ref` / `linked_test`.

### TASK coverage vs SAO §17 (lane 4)

| SAO §17 TASK row | `agent_tasks/` oracle | `@quality` test | pass_band documented | Status |
|------------------|----------------------|-----------------|----------------------|--------|
| e.g. TASK-SC02-01 | yes/no | yes/no | yes/no | PASS / GAP |

Lane 4 gaps are WARNING until promotion window — do not fail PR CI for missing TASK tests.

Include agent audit findings in the TAF-08 health summary with lane tags (L1–L4) for TFK-09 scoreboard input.

## Agent

None

## Skill

None

## Rules

None

## Artifacts Produced

None

## Artifacts Consumed

- **Step Library Catalog** (Document) - Required
- **Fixture Library Catalog** (Document) - Required
- **E2E Test Configuration** (Code) - Required

## Notes

No additional notes.
