# Activity: Build Step Library

**Activity ID**: 189
**Order**: 3
**Phase**: Elaboration
**Dependencies**: Predecessor: Activity 188 (Bootstrap Test Harness)
Successor: Activity 190 (Build Fixture Library)

## Description

Build Step Library

## Guidance

# Build Step Library

## Objective

Create a reusable library of Gherkin step definitions that ESM can compose scenarios from **when the library already exists**. The library grows over time — initial seed covers generic patterns, project-specific steps are added via TFK-07 as needed.

**Same phrases, different engines:** AT steps in `docs/features/steps/` use the Django test client. E2E counterparts in `tests/e2e/steps/` use Playwright. Gherkin vocabulary is shared via the Step Library Catalog; implementations are not merged into one module.

---

## Process

### 1. Organize Steps by Domain

```
docs/features/steps/          # AT — Django test client
├── navigation_steps.py
├── form_steps.py
├── table_steps.py
├── auth_steps.py
├── assertion_steps.py
├── dialog_steps.py
├── common_steps.py
└── __init__.py

tests/e2e/steps/              # E2E — Playwright-backed counterparts
```

### 2. Generic Step Patterns

**Navigation:**
- `Given {user} is on the "{page_name}" page`
- `When {user} navigates to "{url}"`
- `Then {user} should see the "{page_name}" page`

**Forms:**
- `When {user} enters "{value}" into "{field}"`
- `When {user} selects "{option}" from "{dropdown}"`
- `When {user} clicks "{button}"`
- `When {user} submits the form`

**Tables:**
- `Then {user} sees table "{table_name}" with {n} rows`
- `Then the table "{table_name}" should contain "{text}"`
- `When {user} sorts table "{table_name}" by "{column}"`

**Auth:**
- `Given {user} is logged in as "{role}"`
- `Given {user} is not authenticated`

**Assertions:**
- `Then {user} should see "{text}"`
- `Then {user} should not see "{text}"`
- `Then the element "{test_id}" should be visible`

### 3. Step Implementation Conventions

- All steps use `data-testid` selectors for element targeting
- Parameterize generically — avoid hardcoding entity names
- Log actions at INFO level
- Add module-level docstring listing all steps

## Agent

None

## Skill

**Title**: Behave-Django BDD Runner
**Capability Domain**: BDD Test Execution
**Technology Stack**: behave, django, behave-django

**Title**: Gherkin Step Library Patterns
**Capability Domain**: BDD Step Engineering
**Technology Stack**: gherkin, behave, step-definitions

## Rules

None

## Artifacts Produced

- **Step Library Catalog** (Document) - Required

## Artifacts Consumed

- **SAO.md § Test Strategy** (Document) - Required
- **Behave Configuration** (Code) - Required

## Notes

No additional notes.
