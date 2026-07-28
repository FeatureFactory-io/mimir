# Activity: Define Test Architecture

**Activity ID**: 187
**Order**: 1
**Phase**: Inception
**Dependencies**: Successor: Activity 188 (Bootstrap Test Harness)

## Description

Define Test Architecture

## Guidance

# Define Test Architecture

## Objective

Consume DTA-06 "Define Test Strategy" decisions (already seeded into `docs/architecture/SAO.md` § Test Strategy) and **flesh out** that SAO section with the project's Test Trophy model, runner mapping, coverage policy, directory layout, and zero-bug / zero-length-feedback workflow.

**Authoritative output:** update `docs/architecture/SAO.md` § Test Strategy. Do **not** treat a separate Test Architecture Document as the source of truth. A thin local pointer file (e.g. `docs/architecture/test-architecture.md` linking to SAO §5) is allowed for navigation only.

**Handoff:** DTA-06 / DTA-18 write motivators and broad strokes. TFK-01 (run before BPE) completes directory layout, AT/E2E runner paths, and quality gates so construction can execute against a finished Test Strategy section.

---

## Decisions to Flesh Out in SAO.md

### 1. Test Trophy (not Pyramid)

Our model is the **Test Trophy** — integration tests are the main bet:

| Level | Weight | Runner | What it proves |
|-------|--------|--------|----------------|
| Unit | Thin | pytest | Custom queryset logic, pure utility functions, business logic methods — only where isolation adds value. Do NOT test default Model CRUD, auto-generated views, or framework behavior. |
| Integration | **Thick** | pytest | Feature works end-to-end with real DB, real services, real connections. **No mocking.** Think of them as acceptance tests minus the GUI. |
| Acceptance (AT) | Medium | behave-django | `.feature` scenarios in `docs/features/` executed against the app via Django test client. Steps from the TFK Step Library. BDD-grade executable requirements. |
| E2E | Selective | behave + Playwright | Full user journey in `tests/e2e/`. Sequential, slow, runs on staging before release. Screenshots for visual verification. |

### 2. Why Test Trophy over Pyramid

- Unit tests are limited: testing `model.save()` returns OK tells us nothing about whether data actually persisted
- Acceptance tests with a real browser are expensive: slow, flaky
- Integration tests hit the sweet spot: real thing, no GUI overhead, fast enough for CI
- AT tests are integration tests with BDD syntax — the `.feature` file IS the requirements document made executable

### 3. Runner Mapping

- **pytest**: everything up to and including integration tests
- **behave-django** (`make test-at`): acceptance tests — `docs/features/` (spec + runner; Django test client; `tags = ~@wip`)
- **behave + Playwright** (`make test-e2e`): E2E tests — `tests/e2e/` (LiveServer + browser; own `environment.py`)

### 4. Coverage Policy

- Coverage metrics are necessary but not sufficient
- **Coverage is meaningless without quality** — 90% coverage with useless tests is worse than 60% with real tests
- Quality gates: no mocking in integration tests, no testing framework behavior, no tests > 10 lines without extraction
- `@wip` scenarios excluded from CI; all other `docs/features/` scenarios must pass AT before merge

### 5. Zero-Bug and Zero-Length Feedback

Document in SAO: bug = failing integration/AT scenario; fix same day with a permanent regression test; continuous pytest feedback via `tests.log`.

---

## Deliverables

- ✅ **SAO.md § Test Strategy** fleshed out (Trophy, runners, paths, coverage, zero-bug, zero-length feedback)
- ✅ Ready for TFK-02 Bootstrap Test Harness and BPE

## Agent

None

## Skill

**Title**: Test Trophy Architecture
**Capability Domain**: Test Strategy & Design
**Technology Stack**: testing-trophy, integration-testing

## Rules

None

## Artifacts Produced

- **SAO.md § Test Strategy** (Document) - Required

## Artifacts Consumed

None

## Notes

No additional notes.
