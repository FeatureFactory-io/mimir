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
└── autofixture/
    └── fixture_creator.py   # AutoFixture helper
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

## Agent

None

## Skill

**Title**: AutoFixture and FactoryBoy Patterns
**Capability Domain**: Test Data Management
**Technology Stack**: factory-boy, pytest-fixtures, django-orm

## Rules

None

## Artifacts Produced

- **Fixture Library Catalog** (Document) - Required

## Artifacts Consumed

- **SAO.md § Test Strategy** (Document) - Required
- **Behave Configuration** (Code) - Required

## Notes

No additional notes.
