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

### 2. Analyze Coverage Gaps

For each area with insufficient coverage:
- Identify which scenarios from .feature files lack corresponding tests
- Identify services/methods with zero or low coverage
- Assess risk and prioritize

### 3. Analyze Quality Issues

| Category | Examples | Issue Type |
|----------|----------|------------|
| Missing tests | Service method with no test | Scenario issue |
| Weak tests | Tests check return code but not side effects | Enhancement issue |
| Fat controllers | Logic in views needing extraction | Refactoring issue |
| Mocking violations | Mocks in integration tests | Bug issue |
| Flaky tests | Non-deterministic pass/fail | Bug issue |

### 4. Produce Report and Create Issues

For each finding, create a GitHub Issue with:
- **What**: specific test/file/scenario that needs work
- **Why**: what risk the gap exposes
- **How**: concrete action
- **Effort**: easy/medium/hard
- **Priority**: critical/important/nice-to-have

## Agent

None

## Skill

None

## Rules

None

## Artifacts Produced

None

## Artifacts Consumed

- **E2E Test Configuration** (Code) - Required

## Notes

No additional notes.
