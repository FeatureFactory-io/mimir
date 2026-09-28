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
├── integration/agent/       # pytest -m agent_proof (lane 1)
│   └── test_prf_*.py
├── e2e/                     # behave + Playwright (E2E)
│   ├── *.feature            # journey scenarios
│   ├── steps/               # Playwright-backed steps (same Gherkin phrases as AT)
│   └── environment.py       # LiveServer + browser + screenshots
├── infra/                   # CDK assertion tests
├── fixtures/                # Shared fixture data
│   ├── seed.json
│   ├── presets/
│   ├── llm_scripts/         # Ordered ScriptedLLM queues per PRF-* (lane 1)
│   │   └── <prf-id>/
│   │       ├── happy.json
│   │       └── reject_*.json
│   └── agent_tasks/         # Frozen TASK-* corpora + oracle YAML (lane 4)
│       └── <task-id>/
│           ├── input/
│           ├── expected.yaml
│           └── meta.yaml
├── support/                 # Shared pytest helpers
│   ├── __init__.py
│   ├── log_story.py         # assert_log_story(caplog, where=..., beats=...)
│   └── agent_story.py       # assert_agent_story(trace, workflow=..., beats=...)
└── conftest.py

docs/features/               # BDD spec + AT runner (behave.ini paths = docs/features)
├── act-*/                   # .feature files per act
├── steps/                   # AT Step Library (Django test client)
├── support/                 # page registry
└── environment.py           # behave-django AT lifecycle (atomic rollback)
```

Document the log-story helper import path in root `tests/conftest.py` so BPE/MIN agents discover it. Recipes: skill *Pytest Log Story Assertions* (`LOG_STORY_TESTING`). Log-story tests run inside existing `make test` / pytest — **no new CI job**.

When SAO §17 applies, also document `assert_agent_story` import path and the `scripted_llm` / `agent_harness` fixtures (skill *Agent Integration Proof Patterns*). Agent-proof tests use the existing pytest runner gated by `make test-agent-proof` — **no change to default `ci.yml`** until PRF tests exist.

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
    agent_proof: Lane 1 control-plane proofs (ScriptedLLM, real DB/tools)
    live_llm: Lane 3 live provider contract eval (excluded from default PR run)
    quality: Lane 4 TASK-* golden quality eval (promotion band, not PR gate)
```

Default `make test` / `pytest` collection MUST exclude `live_llm` and `quality` (and `agent_proof` until `AGENTS_ENABLED=true` — see TFK-05). Do not add `-m agent_proof` to bare PR CI until at least one PRF test exists (empty marker selection fails).

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
- `make test-agent-proof` → gated `pytest -m agent_proof` when `AGENTS_ENABLED=true` (TFK-05)

### 4. Configure Playwright Integration

For E2E tests using behave + Playwright with LiveServerTestCase under `tests/e2e/`.

### 5. Agent story harness

When SAO §17 applies, ship `tests/support/agent_story.py` alongside `log_story.py`. Rule: `do-assert-agent-story`. Skill: *Agent Integration Proof Patterns*.

**Helper contract:**

```python
def assert_agent_story(
    trace,
    *,
    workflow: str,
    beats: dict[str, list[str]],
) -> None:
    """Fail naming missing beat; trace from agent run recorder (not caplog)."""
```

**Fixtures (root `tests/conftest.py` or `tests/integration/agent/conftest.py`):**

```python
@pytest.fixture
def scripted_llm(prf_id):
    """Load ordered queue from tests/fixtures/llm_scripts/<prf-id>/happy.json."""
    return ScriptedLLM(load_script(f"tests/fixtures/llm_scripts/{prf_id}/"))

@pytest.fixture
def agent_harness(db):
    """Real DB, real tool registry, CAP-004 injectable LLM — no domain mocks."""
    ...
```

**Test naming:** `test_<prf>_agent_story_happy` / `test_<prf>_agent_story_reject` when the PRF row is adverse or has a reject sketch.

**Markers:**

| Marker | Lane | LLM | CI |
|--------|------|-----|-----|
| `agent_proof` | 1 | ScriptedLLM only | PR when `AGENTS_ENABLED=true` |
| `live_llm` | 3 | Live provider, temp=0 | Nightly `agent-eval.yml` |
| `quality` | 4 | Live provider, temp=0 | Promotion band |

Agent-story tests prove **control-plane trace beats**; log-story tests prove **logging beats** — complementary, both green in the same commit when declared (see rule `do-assert-log-story`).


## Rules

Before bootstrapping the harness, **read** each Rule below in this playbook (by slug), then **apply** it. Do not rely on memory of the rule text.

Required:
- `pytest`
- `do-continuous-testing`
- `do-assert-log-story`
- `do-informative-logging`
- `do-test-fixture-data-management`

When SAO §17 applies, also required:
- `do-assert-agent-story`

Activity-specific (not a substitute for the rules above):
- Ship `tests/support/log_story.py` (`assert_log_story`) as part of harness bootstrap; log-story tests use the existing pytest runner (no new CI job).
- Ship `tests/support/agent_story.py` (`assert_agent_story`) when §17 applies; agent-proof tests use gated `make test-agent-proof` (no change to default PR job until tests exist).

## Success Criteria
- Directory layout matches Process §1 (including `tests/support/log_story.py`)
- pytest and behave configured
- At least one golden `*_log_story_*` test can import and use `assert_log_story`
- When SAO §17 applies: directory layout includes `agent_story.py`, `llm_scripts/`, `agent_tasks/`; pytest markers `agent_proof`, `live_llm`, `quality` registered; at least one golden `test_*_agent_story_happy` imports `assert_agent_story` and runs green under ScriptedLLM

## Agent

None

## Skill

**Title**: Agent Integration Proof Patterns

**Title**: Behave-Django BDD Runner
**Capability Domain**: BDD Test Execution
**Technology Stack**: behave, django, behave-django

**Title**: Pytest Log Story Assertions

## Rules

- **Assert Agent Story** (`assert-agent-story`)
- **Assert Log Story** (`assert-log-story`)

## Artifacts Produced

- **Behave Configuration** (Code) - Required

## Artifacts Consumed

- **SAO.md § Test Strategy** (Document) - Required

## Notes

No additional notes.
