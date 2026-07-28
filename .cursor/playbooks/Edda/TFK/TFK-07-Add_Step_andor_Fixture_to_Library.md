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

## Process

### 1. Assess What's Needed

- Identify the gap: missing step pattern, missing fixture, or both
- Check if an existing step can be generalized/parameterized instead of creating a new one

### 2. Create Step Definition (if needed)

Follow library conventions:
- Place in appropriate domain file (navigation, forms, tables, auth, assertions)
- Use `data-testid` selectors
- Parameterize generically
- Log actions at INFO level

### 3. Create Fixture (if needed)

Follow library conventions:
- JSON for static reference data → `tests/fixtures/presets/`
- FactoryBoy for dynamic data → `tests/fixtures/factories/`
- Document scope and dependencies

### 4. Update Catalogs

- Add new step to Step Library Catalog
- Add new fixture to Fixture Library Catalog

### 5. Verify

- Write a small test scenario using the new step/fixture
- Run it to verify it works
- Ensure existing tests are not broken

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
