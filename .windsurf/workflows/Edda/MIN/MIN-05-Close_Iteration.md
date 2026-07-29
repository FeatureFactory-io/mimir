# Activity: Close Iteration

**Activity ID**: 182
**Order**: 5
**Phase**: None
**Dependencies**: Predecessor: Activity 181 (Execute)
Successor: Activity 183 (Acceptance, Bug Reports & Deploy Fixes)

## Description

Close Iteration

## Guidance

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

---

## Lessons Learned Aggregation

After the TAF gate passes, aggregate lessons from all closed issues in this iteration.

### Collect

```bash
gh issue list --milestone {N} --state closed --json number,body \
  | jq -r '.[] | "### Issue #\(.number)\n\(.body | split("## Lessons Learned")[1] // "— not found")"'
```

If any issue is missing the section, reconstruct from commit messages and closing comments before continuing.

### Write Iteration File

Create `docs/lessons_learned/ITER-{YYYYMMDD}-{slug}.md`:

```markdown
---
iteration: ITER-{YYYYMMDD}-{slug}
date: {YYYYMMDD}
scenarios_planned: {N}
scenarios_delivered: {N}
velocity_ratio: "{delivered}/{planned}"
dominant_drift: none  # none | footprint_violation | checkpoint_fail | sao_violation
footprint_accuracy: stable  # improving | stable | degrading
---

# Lessons Learned — ITER-{YYYYMMDD}-{slug}

{aggregated observations from all issues, grouped by theme where natural — not forced into categories}
```

### Apply SAO.md Updates

For every SAO.md decision flagged in any issue: apply it to `docs/architecture/SAO.md` now, or open a GitHub issue tagged `sao-update` if it requires human review. Do not defer silently.

### Commit

```bash
git add docs/lessons_learned/ITER-{YYYYMMDD}-{slug}.md docs/architecture/SAO.md
git commit -m "docs(lessons): aggregate iteration lessons ITER-{YYYYMMDD}-{slug}"
```

## Agent

None

## Skill

None

## Rules

- **Follow Commit Convention** (`do-follow-commit-convention`)
- **Github Issues** (`do-github-issues`)

## Artifacts Produced

None

## Artifacts Consumed

None

## Notes

No additional notes.
