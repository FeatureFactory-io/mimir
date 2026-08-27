# Activity: Close Iteration

**Activity ID**: 185
**Order**: 7
**Phase**: None
**Dependencies**: Predecessor: Activity 184 (Fix & Reintegrate)

## Description

Final iteration close: verify the graph execution record, run the TAF health gate, aggregate lessons learned, apply SAO updates, create the GitHub Release, and close the milestone. Nothing ships until TAF is green and lessons are written.

## Guidance

**Entry conditions (verify before doing anything):**
- Zero open blocker issues on milestone
- Saga regression UAT report: CLEAN
- All scenario issues closed with `status-done` and `GATE_PASS` comment

---

## Step 1: Graph Execution Verification

For every closed scenario issue in this milestone, confirm:

```bash
gh issue view {N} --json comments | jq '
  [.comments[] | select(.body | contains("NODE_PASS"))] | length,
  [.comments[] | select(.body | contains("GATE_PASS"))] | length,
  [.comments[] | select(.body | contains("BUILD_COMPLETE"))] | length
'
```

Each scenario must have:
- `N_nodes` × NODE_PASS comments (one per node)
- 1 × BUILD_COMPLETE comment
- 1 × GATE_PASS comment

Any gap: return to the responsible activity (MIN-03 or MIN-04) to close it before proceeding.

---

## Step 2: TAF Health Gate

### 2a. Invoke TAF-08 — Validate Test Health

Run full coverage and quality audit:

```bash
pytest tests/ --cov=methodology --cov=mcp_integration --cov-report=term-missing 2>&1 | tail -30
make test-at   # acceptance tests
```

Quality audit — flag any of:
- Tests longer than 10 lines without extraction
- Mocking violations in `tests/integration/`
- Fat controller tests (testing views directly without service layer)
- Coverage regression below established baseline

Produce a health summary with `CRITICAL` / `WARNING` / `INFO` classifications.

### 2b. Invoke TAF-09 — Prepare Test Report

For each finding from TAF-08:
- `CRITICAL`: must resolve before close — file a blocking GitHub issue, fix it (dispatch dr-dobbs if needed), rerun TAF-08
- `WARNING`: file a GitHub issue tagged `test-debt`, defer to next iteration
- `INFO`: document in lessons learned, no issue required

```bash
gh issue create --title "test: {finding_title}" \
  --body "{finding detail}\n\nDiscovered: TAF-09 iteration close ITER-{slug}" \
  --label "test-debt" --milestone {next_milestone_or_backlog}
```

**CRITICAL findings block close.** Do not proceed until all CRITICAL findings are resolved and TAF-08 reruns clean.

---

## Step 3: Lessons Learned Aggregation

### Collect from closed issues

```bash
gh issue list --milestone {N} --state closed --json number,body \
  | jq -r '.[] | "### Issue #\(.number)\n\(.body | split("## Lessons Learned")[1] // "— not found")"'
```

If any issue is missing a Lessons Learned section: reconstruct from its commit messages and gate comments.

### Write the iteration file

Create `docs/lessons_learned/ITER-{YYYYMMDD}-{slug}.md`:

```markdown
---
iteration: ITER-{YYYYMMDD}-{slug}
date: {YYYYMMDD}
milestone: #{N} — {goal}
scenarios_planned: {N}
scenarios_delivered: {N}
fix_cycles: {N}   # number of MIN-06 loops
velocity_ratio: "{delivered}/{planned}"
dominant_drift: none  # none | footprint_violation | checkpoint_fail | sao_violation | uat_blocker
uat_blockers_found: {N}
uat_blockers_resolved: {N}
---

# Lessons Learned — ITER-{YYYYMMDD}-{slug}

## Build Phase (MIN-03)
{aggregated dr-dobbs worker drift patterns}

## Integration Gate (MIN-04)
{DoD deviations, fix patterns}

## UAT (MIN-05 / MIN-06)
{blocker themes, fix cycle count, Saga regression result}

## Architecture Notes
{any SAO.md updates identified}

{aggregated observations from all issues, grouped by theme — not forced into categories}
```

---

## Step 4: Apply SAO.md Updates

For every architecture decision or deviation flagged in any issue's Lessons Learned:

- If it is clear and non-controversial: apply it to `docs/architecture/SAO.md` now
- If it requires human judgment: open a GitHub issue tagged `sao-update`, describe the decision, and link it to this iteration

Do not defer silently.

---

## Step 5: Commit Lessons and SAO

```bash
git add docs/lessons_learned/ITER-{YYYYMMDD}-{slug}.md docs/architecture/SAO.md
git commit -m "docs(lessons): aggregate iteration lessons ITER-{YYYYMMDD}-{slug}

Scenarios: {N}/{N} delivered
Fix cycles: {N}
UAT blockers: {N} found, {N} resolved"
```

---

## Step 6: Create GitHub Release

```bash
gh release create "ITER-{YYYYMMDD}-{slug}" \
  --title "Iteration: {goal}" \
  --notes "$(cat <<'EOF'
## Delivered Scenarios

{list of scenario titles with issue links}

## UAT

Journeys passed: {N}
Blockers found: {N} — resolved: {N}
Deferred (non-blockers): {N}

## Known Deferred Issues

{list of deferred issues or "none"}

## Test Health

TAF-08: {CLEAN | WARNINGS documented}
Coverage: {%}
EOF
)"
```

---

## Step 7: Close the Milestone

```bash
gh api repos/{owner}/{repo}/milestones/{N} -X PATCH -f state=closed
```

Post final summary on the first delivered issue:

```bash
gh issue comment {first_issue_number} --body "<!-- ITERATION_CLOSED -->
Iteration: ITER-{YYYYMMDD}-{slug}
Release: ITER-{YYYYMMDD}-{slug}
Scenarios: {N}/{N}
UAT: CLEAN
TAF: CLEAN
Lessons: docs/lessons_learned/ITER-{YYYYMMDD}-{slug}.md
Closed: {ISO8601}
<!-- /ITERATION_CLOSED -->"
```

---

## Rules

- `do-follow-commit-convention`
- `do-github-issues`

## Success Criteria

- All scenario issues have complete NODE_PASS + GATE_PASS record
- TAF-08 health audit: no CRITICAL findings remaining
- TAF-09: WARNING/INFO findings filed as deferred issues
- Lessons learned file committed with velocity and drift metadata
- SAO.md updates applied or filed as `sao-update` issues
- GitHub Release created with delivery summary
- Milestone closed

## Agent

None — Team Lead (TL) runs this activity inline.

## Skill

None

## Artifacts Produced

- `docs/lessons_learned/ITER-{YYYYMMDD}-{slug}.md`
- GitHub Release
- SAO.md updates (or `sao-update` issues)
- TAF test-debt issues

## Artifacts Consumed

- UAT Report (from MIN-05)
- Lessons Learned sections from all closed issues

## Notes

No additional notes.
