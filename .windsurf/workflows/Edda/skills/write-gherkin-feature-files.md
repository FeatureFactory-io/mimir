# Skill: Write Gherkin Feature Files

**Capability Domain**: BDD_AUTHORING  
**Technology Stack**: Gherkin + Playwright + pytest-bdd

## Overview

Gherkin `.feature` files are the **single source of truth** for acceptance criteria. They are not documentation — they are executable tests. Every scenario must be specific enough that an automated test runner can determine PASS or FAIL without human interpretation.

This skill covers two non-negotiable principles and the patterns that enforce them.

---

## Principle 1 — Scenarios Must Be Executable Tests

A scenario is a good test when a developer who has never spoken to you can implement it from the Gherkin alone and get the same result as you intended.

### The Test-Readiness Checklist

Before committing a scenario, verify:

| Check | Question | Fail signal |
|-------|----------|-------------|
| **Concrete data** | Does every Given/When/Then use real names, real values, real counts? | "some playbooks", "enters details", "valid data" |
| **Specific selector** | Does every interaction reference the exact button label or `data-testid`? | "clicks the button", "uses the action" |
| **Verifiable assertion** | Can the Then be checked by `assert element.text == '...'`? | "page updates", "something happens" |
| **Single behaviour** | Does the scenario test exactly one thing? | Scenario with 4 Whens and 6 Thens |
| **State independence** | Can it run in any order without depending on prior test state? | Given that depends on another scenario's outcome |

### Pull Data from `user_journey.md`

`docs/features/user_journey.md` defines the canonical personas (**Maria Rodriguez**, **Mike Chen**) and all example entity names. Always use those names — never invent generic placeholders.

**Anti-pattern (untestable):**
```gherkin
Scenario: Create activity successfully
  Given Maria is on the create activity form
  When she enters a name and description
  And she creates the activity
  Then the activity is created
```

**Good pattern (executable test):**
```gherkin
Scenario: FOB-ACTIVITIES-CREATE_ACTIVITY-02 Create activity successfully
  Given Maria is on the create activity form for workflow "Component Development"
  When she enters "Setup component structure" in Name
  And she enters "Create folder structure and base files" in Description
  And she clicks [Create Activity]
  Then the activity "Setup component structure" appears in the activity list
  And she sees success notification "Activity created successfully"
  And she is redirected to FOB-ACTIVITIES-VIEW_ACTIVITY-1
```

Key differences:
- Entity name comes from user_journey.md ("Component Development", "Setup component structure")
- Button references exact label in brackets: `[Create Activity]`
- Then assertions name the exact element and exact text
- Then includes navigation assertion (which screen)

### Counts and Quantities Must Be Concrete

**Anti-pattern:** `Given she has multiple playbooks`  
**Good pattern:** `Given Maria has 3 playbooks in her FOB:`  (followed by a data table)

**Anti-pattern:** `Then she sees all playbooks`  
**Good pattern:** `Then the header shows "Playbooks (3)"` and `And she sees all 3 playbooks in the table`

### Use Data Tables for Multi-Row Setup

```gherkin
Given Maria has 3 playbooks in her FOB:
  | name                       | author          | version | status   |
  | React Frontend Development | Mike Chen       | v1.2    | Active   |
  | UX Research Methodology    | Maria Rodriguez | v2.1    | Active   |
  | Design System Patterns     | Community       | v1.0    | Disabled |
```

Never say "she has a playbook" when you can give its full identity. The test framework sets up exactly this data — vague rows produce unpredictable fixtures.

### Use `Scenario Outline` for Parametric Cases

When the same flow runs for N values (status filter, column sort), avoid duplicating scenarios:

```gherkin
Scenario Outline: FOB-PLAYBOOKS-LIST+FIND-10 Sort by different columns
  Given Maria is on the playbooks list page
  When she clicks the "<column>" column header
  Then playbooks are sorted by "<column>" in ascending order

  Examples:
    | column        |
    | Author        |
    | Version       |
    | Status        |
    | Last Modified |
```

---

## Principle 2 — Unified Step Vocabulary

Every team member and every automated step definition uses the **same English phrase** for the same UI gesture. Fragmented synonyms mean duplicate step definitions and inconsistent tests.

### Canonical Step Dictionary

#### Navigation & Entry Points
| Canonical Phrase | Do NOT Use |
|-----------------|------------|
| `she clicks "Playbooks" in the main navigation` | presses, taps, selects from nav, uses the nav link |
| `she is on FOB-{ENTITY}-LIST+FIND-1` | she visits, she navigates to, she opens the page |
| `she is redirected to FOB-{ENTITY}-VIEW_{ENTITY}-1` | she goes to, she lands on, she ends up at |

#### Button Interactions
| Canonical Phrase | Do NOT Use |
|-----------------|------------|
| `she clicks [Create New Playbook]` | presses [Create...], taps [Create...], engages [Create...], uses the create button |
| `she clicks [Save]` | submits, confirms, applies |
| `she clicks [Cancel]` | dismisses, aborts, closes |
| `she clicks [Delete]` | removes, destroys |
| `she clicks [Edit]` | modifies, updates, opens edit |
| `she clicks [View]` | opens, inspects, reads |
| `she opens the Actions menu for "{name}"` | she right-clicks, she uses the kebab, she accesses actions |

Rule: **always use square brackets `[Label]` for button references**, matching the exact label in the UI.

#### Form Field Interactions
| Canonical Phrase | Do NOT Use |
|-----------------|------------|
| `she enters "{value}" in {Field Name}` | types in, fills in, inputs, puts |
| `she selects "{value}" from the {Field} filter` | picks, chooses, uses filter |
| `she selects "{value}" from {Field} dropdown` | picks, chooses |
| `she leaves {Field} empty` | does not fill, skips, omits |
| `she clears {Field}` | empties, removes text from |

#### Search & Filter
| Canonical Phrase | Do NOT Use |
|-----------------|------------|
| `she enters "{query}" in the search box` | types in search, uses search field, searches for |
| `she clicks [Clear Filters]` | resets, removes filters |

#### Assertions
| Canonical Phrase | Do NOT Use |
|-----------------|------------|
| `she sees "{exact text}"` | text appears, she notices, page shows |
| `she sees success notification "{exact text}"` | success message appears, toast shows |
| `she sees validation error "{exact text}"` | error appears, field is invalid |
| `the header shows "{Entity} ({N})"` | count is shown, number appears |
| `{Entity} "{name}" appears in the {list/table}` | she can see it, it is listed |
| `{Entity} "{name}" is not in the {list/table}` | it is gone, it disappears, it is removed |
| `the [Button] is disabled` | button is grayed out, button cannot be clicked |
| `a tooltip shows "{exact text}"` | tooltip appears, tooltip says, hint text |

#### Modal / Dialog
| Canonical Phrase | Do NOT Use |
|-----------------|------------|
| `the {FOB-ENTITY-DELETE_ENTITY-1} modal appears` | a dialog pops up, the confirmation box shows |
| `she confirms` | she agrees, she accepts (use only inside a modal context) |
| `she sees "Discard changes?" confirmation` | a prompt appears |

---

## Standard Scenario Coverage per Screen

For every screen (CRUDLF operation), cover these scenario groups in order:

1. **Entry navigation** — how the user reaches this screen (from LIST, from detail, from nav)
2. **Happy path** — successful operation with concrete data from user_journey.md
3. **Required field validation** — every required field, one scenario per field (or `Scenario Outline`)
4. **Optional fields** — verify they save correctly or can be left empty
5. **Cancel / discard** — user abandons the form, no data is persisted
6. **Edge cases** — empty state, max length, special characters, duplicate names
7. **Permission / ownership** — actions unavailable to non-owners
8. **Navbar integration** (last section, marked with comment) — link visible, active state

---

## File Naming & Header Convention

```
docs/features/act-{N}-{entity}/{entity}-{operation}.feature
```

Header template:
```gherkin
Feature: FOB-{ENTITY}-{OPERATION}-1 {Human Readable Title}
  As a {persona from user_journey.md}
  I want to {goal}
  So that {benefit}

  Background:
    Given {persona} is authenticated in FOB
    And she {is on / owns / has set up} {specific context}
```

Scenario IDs:
```
FOB-{ENTITY}-{OPERATION}-{NN}   (zero-padded: 01, 02, 03 ...)
```

---

## Anti-Pattern Reference Card

| Anti-Pattern | Why Bad | Fix |
|-------------|---------|-----|
| `she enters valid data` | Cannot automate — "valid" is undefined | Name every field with its exact value |
| `she clicks the button` | Which button? Multiple may exist | `she clicks [Create Skill]` |
| `the page updates` | No assertion possible | `the header shows "Skills (4)"` |
| `given some skills exist` | Test fixture is non-deterministic | Provide a full data table |
| `she performs the action` | Action is ambiguous | Use exact click step |
| `it works correctly` | Tautology — tests nothing | State the exact observable outcome |
| `she can see the form` | Vague — what form? what state? | `she is on FOB-SKILLS-CREATE_SKILL-1` and `the form shows "Create Skill in {playbook}"` |

---

## Quick Self-Review Before Committing

Read each scenario aloud and ask:

1. Could a junior developer write the Playwright test from this Gherkin alone? → If no, add data.
2. Does every step use a word from the canonical dictionary? → If no, rename the step.
3. Does every Then contain an exact string or exact count to assert? → If no, add specificity.
4. Would this scenario still pass if the wrong entity was created? → If yes, add identity assertions.
5. Is there a scenario testing what happens when the operation FAILS? → Add validation/error scenarios.
