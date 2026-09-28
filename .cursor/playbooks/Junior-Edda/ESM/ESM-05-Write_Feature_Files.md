# Activity: Write Feature Files

**Activity ID**: 39
**Order**: 5
**Phase**: Inception
**Dependencies**: Predecessor: Activity 38 (Create Dialogue Maps)

## Description

Write Feature Files

## Guidance

APPEND TO GUIDANCE:

---

## Feature file location (layout)

Write `.feature` files to `docs/features/act-*/`. That tree is the living BDD specification. After TFK-02 is in place, the same tree is also the AT runner path (`behave.ini` `paths = docs/features`) — there is no separate promote/copy into `tests/acceptance/` or `features/at/`.

Tag not-yet-implemented scenarios `@wip` so CI can exclude them (`tags = ~@wip`) once behave is configured.

---

## TFK Integration: Step Library Consumption (optional, when TFK exists)

**ESM does not depend on TFK.** Workflow order is ESM → … → TFK. On a greenfield first pass, write clear, unconstrained Gherkin that expresses user goals. Do **not** block ESM-05 waiting for Step/Fixture Library Catalogs.

**When TFK already exists** (bootstrap repos, later iterations, or after TFK-03/04 have run):

1. **Prefer catalog phrases**: Open the Step Library Catalog (TFK-03) and reuse existing step patterns (navigation, forms, tables, auth, assertions, dialogs).
2. **Assemble from library**: Compose scenarios from catalog building blocks so they become immediately executable once AT steps exist.
3. **If a phrase is missing**: Do not invent one-off step wording that will never be implemented. Either (a) write natural Gherkin and note a follow-up TFK-07 to add the phrase, or (b) if TFK-07 is available in this iteration, invoke it to extend the catalog.
4. **Fixtures**: Same rule for Fixture Library Catalog (TFK-04) — optional when present; otherwise describe data needs in scenario prose / examples tables.

### Why this split matters

- **Specification first (ESM):** feature files are requirements, not a hostage of the test harness.
- **Automation second (TFK):** TFK binds phrases to Django-client (AT) and Playwright (E2E) implementations.
- **No circular dependency:** ESM-05 never lists TFK-03/04 artifacts as *required* inputs.

## Inputs (additional)

- **Step Library Catalog** (Document, Optional) — produced by TFK-03 Build Step Library; use when available.
- **Fixture Library Catalog** (Document, Optional) — produced by TFK-04 Build Fixture Library; use when available.

---

## Feature file location (layout)

Write `.feature` files to `docs/features/act-*/`. That tree is the living BDD specification. After TFK-02 is in place, the same tree is also the AT runner path (`behave.ini` `paths = docs/features`) — there is no separate promote/copy into `tests/acceptance/` or `features/at/`.

Tag not-yet-implemented scenarios `@wip` so CI can exclude them (`tags = ~@wip`) once behave is configured.

---

## TFK Integration: Step Library Consumption (optional, when TFK exists)

**ESM does not depend on TFK.** Workflow order is ESM → … → TFK. On a greenfield first pass, write clear, unconstrained Gherkin that expresses user goals. Do **not** block ESM-05 waiting for Step/Fixture Library Catalogs.

**When TFK already exists** (bootstrap repos, later iterations, or after TFK-03/04 have run):

1. **Prefer catalog phrases**: Open the Step Library Catalog (TFK-03) and reuse existing step patterns (navigation, forms, tables, auth, assertions, dialogs).
2. **Assemble from library**: Compose scenarios from catalog building blocks so they become immediately executable once AT steps exist.
3. **If a phrase is missing**: Do not invent one-off step wording that will never be implemented. Either (a) write natural Gherkin and note a follow-up TFK-07 to add the phrase, or (b) if TFK-07 is available in this iteration, invoke it to extend the catalog.
4. **Fixtures**: Same rule for Fixture Library Catalog (TFK-04) — optional when present; otherwise describe data needs in scenario prose / examples tables.

### Why this split matters

- **Specification first (ESM):** feature files are requirements, not a hostage of the test harness.
- **Automation second (TFK):** TFK binds phrases to Django-client (AT) and Playwright (E2E) implementations.
- **No circular dependency:** ESM-05 never lists TFK-03/04 artifacts as *required* inputs.

## Inputs (additional)

- **Step Library Catalog** (Document, Optional) — produced by TFK-03 Build Step Library; use when available.
- **Fixture Library Catalog** (Document, Optional) — produced by TFK-04 Build Fixture Library; use when available.

---

## Responsive Acceptance Scenarios

Read the Responsive Coverage Contract and Screen ID-to-recipe coverage table in `docs/ux/IA_guidelines.md` before writing scenarios.

- Shared page-layout recipes carry the default behavior; do not duplicate identical viewport scenarios in every feature file.
- When a screen departs from its recipe, add focused Gherkin scenarios for each affected target viewport or viewport class.
- Express observable outcomes: stacking order, action reachability, navigation collapse, intentional component overflow, full-viewport behavior, and absence of clipping, overlap, or unintended page-level horizontal scrolling.
- Use exact CSS viewport dimensions from the IA matrix in Examples tables when size matters. Do not use only vague labels such as mobile, tablet, or desktop.
- Keep the Screen ID, recipe name, affected viewport profile, and expected behavior traceable in the scenario or accompanying Examples table.

ESM-05 specifies behavior. Pixel-perfect comparison and screenshot evidence belong to ESM-06 and BPE-05.

## Agent

None

## Skill

**Title**: Write Gherkin Feature Files
**Capability Domain**: BDD_AUTHORING
**Technology Stack**: Gherkin + Playwright + pytest-bdd

## Rules

- **Github Issues** (`do-github-issues`)
- **Write Scenarios** (`do-write-scenarios`)

## Artifacts Produced

- **Feature Files** (Document) - Required
- **Feature File Template (Gherkin)** (Template) - Required

## Artifacts Consumed

- **User Journey** (Document) - Required
- **Screen Flow / Dialogue Map** (Diagram) - Required

## Notes

No additional notes.
