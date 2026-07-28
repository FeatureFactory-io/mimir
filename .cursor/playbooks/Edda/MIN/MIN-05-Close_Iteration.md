# Activity: Close Iteration

**Activity ID**: 182
**Order**: 5
**Phase**: None
**Dependencies**: None

## Description

Close Iteration

## Guidance

APPEND TO GUIDANCE:

---

## TAF Integration: Test Health Validation at Iteration Close

Before declaring an iteration closed, invoke TAF activities to validate test health and produce actionable reports:

### 1. Invoke TAF-08 "Validate Test Health"

- Run full coverage analysis across all test levels
- Quality audit: flag useless tests, mocking violations, fat controllers, tests > 10 lines
- Verify all test levels pass: `make test` + `make test-at` + `make test-e2e`
- Produce health summary with CRITICAL/WARNING/INFO findings

### 2. Invoke TAF-09 "Prepare Test Report"

- Analyze TAF-08 findings + CI/CD run history + E2E screenshots
- Identify coverage gaps and quality issues
- Create GitHub Issues for each actionable finding
- Link issues to the Test Report for tracking

### 3. Iteration Close Gate

The iteration cannot be closed if:
- Any CRITICAL findings remain unresolved
- E2E tests fail on staging
- Coverage has regressed below established baseline

WARNING-level findings are documented as issues for the next iteration but do not block close.

## Agent

None

## Skill

None

## Rules

None

## Artifacts Produced

None

## Artifacts Consumed

None

## Notes

No additional notes.
