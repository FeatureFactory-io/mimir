# Activity: Establish E2E Infrastructure

**Activity ID**: 192
**Order**: 6
**Phase**: Elaboration
**Dependencies**: Predecessor: Activity 191 (Wire CICD Integration)
Successor: Activity 193 (Add Step and/or Fixture to Library)

## Description

Establish E2E Infrastructure

## Guidance

# Establish E2E Infrastructure

## Objective

Set up the end-to-end test infrastructure that enables "day in life" user journey testing via Playwright-driven browser automation.

**Location:** `tests/e2e/` — standalone suite with its own `environment.py`, `steps/`, and `*.feature` files. Not nested under AT. AT remains in `docs/features/` with Django test client steps.

---

## Sequencing contract (why order 6 after #189–#191 is correct)

**Chosen resolution (Galdr option c):** Activities #189–#191 cover **AT concerns only**. Activity #192 stands up **independent E2E** infrastructure. No resequence.

| Activity | TFK label | Scope | Needs Playwright / `tests/e2e/` harness? |
|----------|-----------|-------|------------------------------------------|
| #188 | TFK-02 Bootstrap Test Harness | Creates **directory layout** for both `docs/features/` (AT) and `tests/e2e/` (E2E placeholders), pytest, `behave.ini` | No — only scaffolds paths |
| #189 | TFK-03 Build Step Library | **AT** step implementations in `docs/features/steps/` + Step Library Catalog (phrases) | **No** |
| #190 | TFK-04 Build Fixture Library | Shared fixture data / presets used by AT (and later by E2E data load) | **No** |
| #191 | TFK-05 Wire CICD Integration | CI gates for unit/integration/`make test-at` | **No** (E2E stays staging/release-only) |
| #192 | TFK-06 Establish E2E Infrastructure | Playwright + LiveServer + `tests/e2e/environment.py` + journey features | **Yes — this activity** |
| #193 | TFK-07 Add Step and/or Fixture | Extends catalog; may add AT and/or E2E implementations | As needed |

**How #189–#191 exist without E2E infrastructure:** AT runs via Django test client against `docs/features/` (`manage.py behave --simple`). That path never starts a browser. Fixtures and CI wiring for AT do not call Playwright. Therefore predecessors #189–#191 are valid without #192 being complete.

**What #188 already did vs what #192 does:** #188 may create empty `tests/e2e/` directories and Makefile stubs. #192 makes that suite **runnable** (browser lifecycle, LiveServer, screenshots, `--base-url` / `--db-uri`). Empty dirs ≠ working E2E harness.

**Dual-path step maintenance:** Catalog phrases are owned by #189 (TFK-03). AT Python lives in `docs/features/steps/`. E2E Playwright counterparts live in `tests/e2e/steps/` and are added when journeys need them (#192 seeds the harness; #193 adds missing phrase implementations). Not one merged module.

**Naming:** Prefer Activity numeric IDs (#188–#195) in cross-references; TFK-0N labels are workflow abbreviations only.

---

## Clarifications (architecture contract)

1. **Shared catalog, separate implementations.** The Step Library Catalog (phrases/vocabulary) is shared between AT and E2E. Python step modules are **not** shared: AT in `docs/features/steps/` (Django test client); E2E in `tests/e2e/steps/` (Playwright).

2. **"Same Gherkin phrases" means catalog alignment, not one code tree.** Missing phrases → Activity #193 (TFK-07).

3. **No activity reorder.** Placement after #191 is intentional: AT stack first, E2E harness second. #192 does not unblock #189–#191.

---

## Key Concepts

### E2E vs Acceptance Tests

| Aspect | Acceptance Test (AT) | E2E Test |
|--------|---------------------|----------|
| Focus | Proving ONE feature works | Fulfilling a GOAL using system means |
| Path | `docs/features/` | `tests/e2e/` |
| Engine | Django test client (`behave --simple`) | Playwright + LiveServer |
| Scope | Single .feature, single scenario | Multi-phase .feature, sequential |
| Speed | Fast (no browser) | Slow (real browser, screenshots) |
| When | Every CI run | Staging before release |

### Big Idea: Certify Any Environment

Using `--base-url=...` we can point Playwright at any place where the application runs:
- `--base-url=http://localhost:8000` — local development
- `--base-url=https://staging.example.com` — staging
- `--base-url=https://app.example.com` — production smoke test

Similarly `--db-uri=...` points where initial setup has to be loaded.

---

## Process

### 1. E2E Configuration

```bash
make test-e2e BASE_URL=https://staging.example.com DB_URI=postgres://...
# → manage.py behave tests/e2e/
```

### 2. E2E Feature Structure

Each E2E test is written as one long multi-phase `.feature` file under `tests/e2e/` running sequentially.

### 3. Screenshot on Every Step

`tests/e2e/environment.py` captures a screenshot after every step for visual verification and debugging.

## Agent

None

## Skill

None

## Rules

None

## Artifacts Produced

- **E2E Test Configuration** (Code) - Required

## Artifacts Consumed

- **SAO.md § Test Strategy** (Document) - Required
- **Step Library Catalog** (Document) - Required
- **Fixture Library Catalog** (Document) - Required

## Notes

No additional notes.
