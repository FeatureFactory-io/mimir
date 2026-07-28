# Activity: Bootstrap Test Harness

**Activity ID**: 188
**Order**: 2
**Phase**: Elaboration
**Dependencies**: Predecessor: Activity 187 (Define Test Architecture)
Successor: Activity 189 (Build Step Library)

## Description

Bootstrap Test Harness

## Guidance

# Bootstrap Test Harness

## Objective

Set up the complete test infrastructure: directory structure, pytest configuration, behave-django configuration, Playwright integration, Makefile targets, continuous test runner, and the **Log Story** helper (`tests/support/log_story.py`) used by BPE/MIN caplog gates.

**Layout rule:** AT scenarios live in `docs/features/` (spec + runner — single source of truth). There is **no** separate `tests/acceptance/` or `features/at/` tree. E2E is a standalone suite under `tests/e2e/` with its own `environment.py` and Playwright-backed steps.

---

## Process

### 1. Create Test Directory Structure

```
tests/
├── unit/                    # pytest -m unit
│   └── conftest.py
├── integration/             # pytest -m integration
│   └── conftest.py
├── e2e/                     # behave + Playwright (E2E)
│   ├── *.feature            # journey scenarios
│   ├── steps/               # Playwright-backed steps (same Gherkin phrases as AT)
│   └── environment.py       # LiveServer + browser + screenshots
├── infra/                   # CDK assertion tests
├── fixtures/                # Shared fixture data
│   ├── seed.json
│   └── presets/
├── support/                 # Shared pytest helpers
│   ├── __init__.py
│   └── log_story.py         # assert_log_story(caplog, where=..., beats=...)
└── conftest.py

docs/features/               # BDD spec + AT runner (behave.ini paths = docs/features)
├── act-*/                   # .feature files per act
├── steps/                   # AT Step Library (Django test client)
├── support/                 # page registry
└── environment.py           # behave-django AT lifecycle (atomic rollback)
```

Document the log-story helper import path in root `tests/conftest.py` so BPE/MIN agents discover it. Recipes: skill *Pytest Log Story Assertions* (`LOG_STORY_TESTING`). Log-story tests run inside existing `make test` / pytest — **no new CI job**.

### Helper contract

```python
def assert_log_story(
    caplog,
    *,
    where: str,
    beats: dict[str, list[str]],
    level: str = "INFO",
) -> None:
    """Fail with which beat/key was missing; do not swallow AssertionError."""
```

### 2. Configure pytest

```ini
[pytest]
DJANGO_SETTINGS_MODULE = {project}.settings
python_files = test_*.py
python_classes = Test*
python_functions = test_*
testpaths = tests
addopts =
    -v --strict-markers --tb=short
    --log-file=tests.log --log-file-level=INFO
markers =
    unit: Unit tests (fast, isolated)
    integration: Integration tests (real deps, no mocking)
    acceptance: Acceptance tests (behave BDD)
    e2e: End-to-end tests (Playwright, excluded from default runs)
    slow: Slow running tests
```

### 3. Configure behave

```ini
# behave.ini
[behave]
paths = docs/features
format = pretty
logging_level = INFO
tags = ~@wip
```

Create `docs/features/environment.py` (AT: Django test client / atomic fixtures) and `tests/e2e/environment.py` (E2E: Playwright + LiveServer) separately — engines differ; do not share one environment for both.

Makefile:
- `make test-at` → `manage.py behave --simple docs/features/`
- `make test-e2e` → `manage.py behave tests/e2e/`

### 4. Configure Playwright Integration

For E2E tests using behave + Playwright with LiveServerTestCase under `tests/e2e/`.


## Rules

Before bootstrapping the harness, **read** each Rule below in this playbook (by slug), then **apply** it. Do not rely on memory of the rule text.

Required:
- `pytest`
- `do-continuous-testing`
- `do-assert-log-story`
- `do-informative-logging`
- `do-test-fixture-data-management`

Activity-specific (not a substitute for the rules above):
- Ship `tests/support/log_story.py` (`assert_log_story`) as part of harness bootstrap; log-story tests use the existing pytest runner (no new CI job).

## Success Criteria
- Directory layout matches Process §1 (including `tests/support/log_story.py`)
- pytest and behave configured
- At least one golden `*_log_story_*` test can import and use `assert_log_story`

## Agent

None

## Skill

**Title**: Behave-Django BDD Runner
**Capability Domain**: BDD Test Execution
**Technology Stack**: behave, django, behave-django

**Title**: Pytest Log Story Assertions

## Rules

- **Assert Log Story** (`assert-log-story`)

## Artifacts Produced

- **Behave Configuration** (Code) - Required

## Artifacts Consumed

- **SAO.md § Test Strategy** (Document) - Required

## Notes

No additional notes.
