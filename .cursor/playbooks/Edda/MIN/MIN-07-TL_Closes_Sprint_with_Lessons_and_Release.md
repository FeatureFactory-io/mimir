# Activity: TL Closes Sprint with Lessons and Release

**Activity ID**: 223
**Order**: 7
**Phase**: None
**Dependencies**: None

## Description

TL Closes Sprint with Lessons and Release

## Guidance

## Purpose
Final iteration close: verify the full graph execution record, run the TAF health gate, aggregate lessons learned, apply SAO updates, merge the iteration PR (human gate), tag, create GitHub Release (human gate), and close the milestone.

**Relationship to Activity 182 (Close Iteration):** This activity supersedes Activity 182 'Close Iteration' in Workflow 17, which is deprecated by a companion DROP change in this same PIP submission. Activity 182 predates the TL/worker/Saga model tier separation and lacks the TAF gate, UAT sign-off, and human approval gates introduced here.

**Predecessor activities in this PIP submission:** This activity follows TL Fixes Blockers and Regresses (companion ADD in this PIP, inserted after Activity 183) and TL Integrates and Gates Each Feature (companion ADD in this PIP, inserted after Activity 181 Execute).

**Entry conditions:**
- Zero open blocker issues on milestone
- Acceptance testing regression verdict: CLEAN (from Activity 183)
- Iteration PR open against main

---

## Agent

**Team Lead** — advanced-reasoning AI model (companion ADD Agent in this PIP submission). Operates autonomously throughout this activity except at the two explicit STOP gates (Steps 6 and 7). At those gates the TL presents its work product and waits for human confirmation before taking irreversible actions.

When a TAF CRITICAL finding requires a code fix, the TL dispatches a dr-dobbs worker (Agent [9]) and re-runs Validate Test Health (Activity 194) before proceeding.

---

## Step 1: Graph Execution Verification

For every closed scenario issue:
```bash
gh issue view {N} --json comments | jq '{
  node_pass: [.comments[] | select(.body | contains("NODE_PASS"))] | length,
  bpe06_node: [.comments[] | select(.body | contains("NODE_PASS")) | select(.body | contains("BPE-06"))] | length,
  build_complete: [.comments[] | select(.body | contains("BUILD_COMPLETE"))] | length,
  gate_pass: [.comments[] | select(.body | contains("GATE_PASS"))] | length
}'
```
All four counts must be >= 1. Any gap: return to Execute (Activity 181) before proceeding.

## Step 2: TAF Health Gate

### 2a. Invoke Validate Test Health (Activity 194)
```bash
pytest tests/ --cov=. --cov-report=term-missing
make test-at 2>/dev/null || echo "no test-at target"
```
Flag: tests > 10 lines without extraction, mocking violations in integration tests, coverage regression. Produce CRITICAL / WARNING / INFO summary.

### 2b. Invoke Prepare Test Report (Activity 195)
- **CRITICAL:** dispatch dr-dobbs worker (Agent [9]), rerun Activity 194. Blocks merge.
- **WARNING:** file `test-debt` issue, defer
- **INFO:** document in lessons

## Step 3: Lessons Learned Aggregation

Create the **Iteration Lessons Learned Document** (companion ADD Artifact in this PIP submission; see Skill 28 — Lessons Learned Writing):

`docs/lessons_learned/ITER-{YYYYMMDD}-{slug}.md`
```markdown
---
iteration: ITER-{YYYYMMDD}-{slug}
milestone: #{N} — {goal}
scenarios_planned: {N}
scenarios_delivered: {N}
fix_cycles: {N}
uat_blockers_found: {N}
uat_blockers_resolved: {N}
test_debt_found: {N}
---

## Execution Review (per-scenario deviations and drift signals)
## Acceptance Testing (Saga scope, blockers found, fix cycles)
## Test Debt (stale tests filed, coverage gaps)
## Architecture Notes (SAO.md updates applied or deferred)
```

Consumed by: Orient & Validate Scope (Activity 140 in Plan Iteration workflow) as velocity context for the next iteration.

## Step 4: Apply SAO.md Updates
Clear and non-controversial → apply to `docs/architecture/SAO.md` now. Requires human judgment → open `sao-update` issue.

## Step 5: Commit Lessons and SAO
```bash
git add docs/lessons_learned/ docs/architecture/SAO.md
git commit -m "docs(lessons): ITER-{YYYYMMDD}-{slug} — {N}/{N} scenarios, {N} fix cycles"
```

## Step 6: Human Merge Gate — STOP

**TL presents work product. Human must say "merge" before proceeding.**

```
=== MERGE GATE ===
PR:        #{pr_number} — iteration/{slug} → main
Delivered: {N} scenarios
Acceptance: CLEAN ({N} blockers resolved, {N} deferred)
TAF:       {CLEAN | {N} warnings deferred as test-debt}
Lessons:   docs/lessons_learned/ITER-{YYYYMMDD}-{slug}.md

Await: user says "merge" to proceed.
==================
```

On user "merge":
```bash
gh pr merge {pr_number} --squash --delete-branch \
  --subject "feat(iteration): {slug} — {goal}"
```

## Step 7: Tag and Release — STOP

Assemble the **Release Notes Draft** (companion ADD Artifact in this PIP submission) and present for human approval:

```
=== RELEASE GATE ===
Tag target:  {merge_sha} on main
Release tag: ITER-{YYYYMMDD}-{slug}

Draft notes:
  Delivered: {scenario list with issue links}
  Acceptance: CLEAN
  Test health: {summary}
  Deferred: {list or none}

Await: user says "release" to proceed.
====================
```

On user "release":
```bash
git checkout main && git pull
git log --oneline -1
git tag ITER-{YYYYMMDD}-{slug} {merge_sha}
gh release create "ITER-{YYYYMMDD}-{slug}" \
  --target {merge_sha} \
  --title "Iteration: {goal}" \
  --notes "{approved_notes}"
```

## Step 8: Close Milestone
```bash
gh api repos/{owner}/{repo}/milestones/{N} -X PATCH -f state=closed
```

## Artifacts Produced
- **Iteration Lessons Learned Document** — `docs/lessons_learned/ITER-{YYYYMMDD}-{slug}.md`; consumed by Orient & Validate Scope (Activity 140)
- **Release Notes Draft** — approved by human and published as the GitHub Release body

## Success Criteria
- Graph execution record complete per issue
- Validate Test Health (Activity 194) CRITICALs resolved; WARNINGs deferred as test-debt
- Lessons Learned Document committed
- SAO.md updated or sao-update issues filed
- User explicitly approved merge; PR squash-merged; branch deleted
- Tag points to merge commit on main
- User explicitly approved release; GitHub Release created with --target {merge_sha}
- Milestone closed

## Skill
Skill 28 (Lessons Learned Writing) for Step 3.
Skill 32 (GitHub Issue Operations) for Steps 6–8.

## Rules
Follow Commit Convention (Rule [6]), Github Issues (Rule [14]), Small Increments (Rule [4])

## Agent

None

## Skill

**Title**: Lessons Learned Writing
**Capability Domain**: LESSONS_LEARNED
**Technology Stack**: Markdown + GitHub CLI

## Rules

None

## Artifacts Produced

- **Iteration Lessons Learned Document** (Document) - Required
- **Release Notes Draft** (Document) - Required

## Artifacts Consumed

None

## Notes

No additional notes.
