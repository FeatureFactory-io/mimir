# Activity: Wire CICD Integration

**Activity ID**: 191
**Order**: 5
**Phase**: Elaboration
**Dependencies**: Predecessor: Activity 190 (Build Fixture Library)
Successor: Activity 192 (Establish E2E Infrastructure)

## Description

Wire CICD Integration

## Guidance

# Wire CICD Integration

## Objective

Configure the CI/CD pipeline to run tests at appropriate stages: unit+integration+AT on CI (every push), E2E on staging (before release swap). Define pass/fail gates at each stage.

---

## Process

### 1. CI Pipeline Test Stages

Modify `.github/workflows/ci.yml` (DCD-04 artifact) to add acceptance test stage:

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install dependencies
        run: make provision
      - name: Lint
        run: make lint
      - name: Unit tests
        run: make test-unit
      - name: Integration tests
        run: make test-integration
      - name: Acceptance tests          # NEW — TAF addition
        run: make test-at
```

**Gate:** All three test levels must pass before container build proceeds.

### 2. CD Pipeline E2E Stage

Modify `.github/workflows/cd.yml` (DCD-05 artifact) to add E2E stage on staging:

```yaml
  e2e-staging:
    needs: deploy-idle
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install Playwright browsers
        run: playwright install chromium
      - name: Run E2E against staging
        run: make test-e2e BASE_URL=${{ vars.STAGING_URL }} DB_URI=${{ vars.STAGING_DB_URI }}
      - name: Upload screenshots
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: e2e-screenshots
          path: tests/e2e/screenshots/
```

**Gate:** E2E must pass on staging → create release → swap with prod.

### 3. Screenshot Archival

- E2E tests capture a screenshot after every step
- Screenshots uploaded as GitHub Actions artifacts for human review

---

## Agent eval CI (optional)

When SAO §17 applies, add **agent eval lanes** without changing the default PR job shape in `ci.yml`. Agent-less projects: skip this section; Makefile targets no-op.

### Default `ci.yml` — UNCHANGED for agent-less and baseline PR flow

The existing `test` job (unit → integration → AT) remains the merge gate for all projects. Do **not** add `-m live_llm`, `-m quality`, or unconditional `-m agent_proof` to the default PR workflow.

**Optional PR extension (agents only):** append a conditional step when the repo enables agents:

```yaml
      - name: Agent control-plane proofs (lane 1)
        if: vars.AGENTS_ENABLED == 'true'
        env:
          AGENTS_ENABLED: true
        run: make test-agent-proof
```

Lane 2 (deterministic shell) already runs inside `make test-integration`. No separate job.

### Separate `.github/workflows/agent-eval.yml`

Lanes 3–4 run outside the PR merge path:

```yaml
name: Agent Eval
on:
  workflow_dispatch:
  schedule:
    - cron: '0 6 * * *'   # nightly lane 3

jobs:
  live-contract:
    if: vars.AGENT_EVAL_ENABLED == 'true'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: make provision
      - name: Lane 3 — live contract eval
        env:
          AGENTS_ENABLED: true
          LIVE_LLM_API_KEY: ${{ secrets.LIVE_LLM_API_KEY }}
        run: make test-agent-live

  task-quality:
    if: vars.AGENT_EVAL_ENABLED == 'true'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: make provision
      - name: Lane 4 — TASK golden quality
        env:
          AGENTS_ENABLED: true
          LIVE_LLM_API_KEY: ${{ secrets.LIVE_LLM_API_KEY }}
        run: make test-agent-quality
```

**CD optional cert (lane 3):** in `cd.yml`, add staging agent contract step guarded by `if: vars.AGENT_EVAL_ENABLED == 'true'` — not required for promote when agents N/A.

### Gated Makefile targets (artifact 11)

```makefile
test-agent-proof:
ifeq ($(AGENTS_ENABLED),true)
	uv run pytest -m agent_proof tests/
else
	@echo "skip: agents N/A (SAO §17)"
endif

test-agent-live:
ifeq ($(AGENTS_ENABLED),true)
	uv run pytest -m live_llm tests/
else
	@echo "skip: agents N/A (SAO §17)"
endif

test-agent-quality:
ifeq ($(AGENTS_ENABLED),true)
	uv run pytest -m quality tests/
else
	@echo "skip: agents N/A (SAO §17)"
endif
```

**Gate summary:**

| Target | Lane | PR (`ci.yml`) | `agent-eval.yml` | Promotion |
|--------|------|---------------|------------------|-----------|
| `test-agent-proof` | 1 | optional if `AGENTS_ENABLED` | — | — |
| `test-integration` | 2 | always | — | — |
| `test-agent-live` | 3 | never | nightly / dispatch | optional CD |
| `test-agent-quality` | 4 | never | manual / pre-promote | pass band vs last cert |

Do not block merge on lane 3/4 flake. Empty `agent_proof` collection must not fail PR CI — enable the conditional step only after at least one PRF test lands.

## Agent

None

## Skill

**Title**: Agent Task Eval

## Rules

None

## Artifacts Produced

None

## Artifacts Consumed

- **SAO.md § Test Strategy** (Document) - Required
- **Step Library Catalog** (Document) - Required
- **Fixture Library Catalog** (Document) - Required

## Notes

No additional notes.
