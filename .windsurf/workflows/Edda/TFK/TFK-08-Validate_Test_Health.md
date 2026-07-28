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

### 4. Produce Health Summary

Categorize findings as CRITICAL / WARNING / INFO.

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
