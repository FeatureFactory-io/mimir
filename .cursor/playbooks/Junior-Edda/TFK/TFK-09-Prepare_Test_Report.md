# Activity: Prepare Test Report

**Activity ID**: 195
**Order**: 9
**Phase**: Construction
**Dependencies**: Predecessor: Activity 194 (Validate Test Health)

## Description

Prepare Test Report

## Guidance

# Prepare Test Report

## Objective

Analyze test coverage, last run results, and TAF-08 health findings to produce an actionable test report. Outcomes are turned into GitHub Issues assigned for implementation — closing the feedback loop between test health and development work.

---

## Process

### 1. Gather Inputs

- TAF-08 "Validate Test Health" findings
- Last CI/CD run results (pass/fail per stage, duration, flaky test history)
- E2E screenshot archive
- `tests.log` analysis

When SAO §17 applies, also gather:
- Last `agent-eval.yml` run (lanes 3–4): pass/fail, provider, model pin, duration
- Lane 1 PR `test-agent-proof` history when `AGENTS_ENABLED=true`
- TFK-08 PRF/TASK coverage matrix vs SAO §17

### 2. Analyze Coverage Gaps

For each area with insufficient coverage:
- Identify which scenarios from .feature files lack corresponding tests
- Identify services/methods with zero or low coverage
- Assess risk and prioritize

For agent projects: cross-check SAO §17 PRF/TASK rows against green tests (TFK-08 matrix).

### 3. Analyze Quality Issues

| Category | Examples | Issue Type |
|----------|----------|------------|
| Missing tests | Service method with no test | Scenario issue |
| Weak tests | Tests check return code but not side effects | Enhancement issue |
| Fat controllers | Logic in views needing extraction | Refactoring issue |
| Mocking violations | Mocks in integration tests | Bug issue |
| Flaky tests | Non-deterministic pass/fail | Bug issue |
| Agent proof gaps | PRF row unchecked vs repo | Scenario issue (lane 1) |
| FakeLLM hygiene | Silent queue exhaustion | Bug issue (lane 1) |
| Task band regression | recall below certified pass_band | Enhancement issue (lane 4) |

### 4. Produce Report and Create Issues

For each finding, create a GitHub Issue with:
- **What**: specific test/file/scenario that needs work
- **Why**: what risk the gap exposes
- **How**: concrete action
- **Effort**: easy/medium/hard
- **Priority**: critical/important/nice-to-have

---

## Agent eval scoreboard (lanes 3 & 4)

When SAO §17 applies, append a **Lane 3/4 scoreboard** section to the test report. Omit when agents N/A.

### Lane 3 — Live contract eval

| Run id | Date | Provider / model | Tests run | Pass | Fail | Flake | Notes |
|--------|------|------------------|-----------|------|------|-------|-------|
| … | … | e.g. anthropic/claude-* | `@live_llm` count | | | | temp=0; contract asserts only |

Track: tool-call envelope shape, rate-limit handling, timeout bounds. **Not** a merge gate — trend for infra/prompt regressions before promotion.

### Lane 4 — Task performance quality

| Task id | Oracle type | Pass band | Last N runs | Recall / metric | Extras | Certified | vs prior cert |
|---------|-------------|-----------|-------------|-----------------|--------|-----------|---------------|
| TASK-SC02-01 | set_recall | ≥0.95, extras≤1 | 3 | 0.97 | 0 | ✅ | +0.02 |

**Certification rule:** promote only when all in-scope TASK rows meet `pass_band` for `n_runs` consecutive evals at temp=0. Regression vs last certified band → open GitHub Issue (priority: important) with task id and metric delta.

### Combined agent summary (for PIN / release notes)

| Lane | CI home | Last green | Open gaps (from TFK-08) | Release impact |
|------|---------|------------|---------------------------|----------------|
| 1 PRF | optional PR step | … | … | blocks merge if enabled + red |
| 2 shell | `ci.yml` integration | … | … | blocks merge |
| 3 contract | `agent-eval.yml` | … | … | advisory / optional CD |
| 4 quality | promotion band | … | … | blocks promote if cert required |

**Production signals (outside pytest):** optionally note HITL reject rate, edit-before-approve ratio, learning-rule growth — feeds PIN-02; reference skill *Agent Task Eval* § Production quality.

Feed scoreboard CRITICAL/WARNING rows into §4 issue creation with labels `agent-lane-3`, `agent-lane-4`, or `agent-prf-gap` as appropriate.

## Agent

None

## Skill

**Title**: Agent Task Eval

## Rules

None

## Artifacts Produced

None

## Artifacts Consumed

- **E2E Test Configuration** (Code) - Required

## Notes

No additional notes.
