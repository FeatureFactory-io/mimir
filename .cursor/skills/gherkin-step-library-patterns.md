# Skill: Gherkin Step Library Patterns

**Capability Domain**: BDD_AUTHORING
**Technology Stack**: Gherkin+behave

## Overview

Patterns for organizing, versioning, and composing reusable Gherkin step definitions. The step library is the shared vocabulary between ESM (which writes .feature files) and TFK (which implements the steps).

**AT steps** live under `docs/features/steps/` (Django test client). **E2E counterparts** live under `tests/e2e/steps/` (Playwright). Catalog phrases are shared; Python implementations are not merged.

## Reference Implementation

### Pattern 1: Step Library Organization

```
docs/features/steps/          # AT — Django test client
├── navigation_steps.py
├── form_steps.py
├── table_steps.py
├── auth_steps.py
├── assertion_steps.py
├── dialog_steps.py
├── common_steps.py
└── (catalog: docs/features/CATALOG.md)

tests/e2e/steps/              # E2E — Playwright-backed counterparts
```

### Pattern 2: Step Naming Convention

Steps should be generic and parameterized. Entity names come from parameters, not hardcoded:

```gherkin
# GOOD — reusable across any entity
Given a "Playbook" named "FeatureFactory" exists
When the user clicks "Create" button

# BAD — hardcoded to one entity
Given the FeatureFactory playbook exists
```

### Pattern 3: Step Composition in .feature Files

ESM writes scenarios by composing steps from the library like building blocks **when the catalog already exists**. Write `.feature` files to `docs/features/act-*/`. On greenfield first-pass ESM (before TFK), write clear unconstrained Gherkin; TFK later binds phrases to implementations (see ESM-05 guidance).
