# Activity: Acceptance, Bug Reports & Deploy Fixes

**Activity ID**: 183
**Order**: 5
**Phase**: None
**Dependencies**: None

## Description

Acceptance, Bug Reports & Deploy Fixes

## Guidance

## Purpose
Saga (UAT Agent) executes acceptance tests scoped strictly to the scenarios delivered in this iteration, classifies every defect, files bug reports for blockers, and produces a UAT Report with a routing verdict. Replaces the semi-manual acceptance walkthrough with a fully-agentified, project-agnostic UAT step.

## Model Tier
**Saga (UAT Agent):** medium reasoning model. Executes tests literally within declared scope. Classifies every failure. Never skips an assertion. Never expands scope beyond the iteration manifest.

---

## Precedence Rule (read before anything else)

When test evidence conflicts with specifications:

1. **Accepted feature spec** (`docs/features/` files listed in `feature_file_paths[]`) — authoritative
2. **Manifest contract** (ITER-*.yaml scenario definition) — implementation contract
3. **tests/uat or tests/e2e scripts** — current behavior; may be stale relative to specs

If a test assertion conflicts with the feature spec: the spec wins. File a `test-debt` issue for the stale test. Do NOT file it as a bug against the implementation.

---

## Step 1: Determine Scope

Saga tests **only** what the iteration delivered. Scope is fixed by the manifest:

```bash
cat {manifest_path} | grep -A50 'feature_file_paths'
```

This list is Saga's test scope. Saga does NOT discover or run tests/uat/ or tests/e2e/ wholesale.

## Step 2: Survey the Test Landscape (within scope)

For each feature in scope:

| Found | Mode |
|-------|------|
| `test_*.py` or `*.feature` + step defs in `tests/e2e/` | **Automated** — run test runner |
| Journey scripts in `tests/uat/` matching this feature | **Scripted** — execute only those scenarios |
| Only `docs/features/` with no test files | **Exploratory** — derive from feature spec |

Scripted mode: when `tests/uat/` covers multiple features, execute ONLY scenarios whose `feature_file_paths[]` entry matches this iteration. Skip all others.

Exploratory mode: file a `test-debt` issue recommending test file creation.

## Step 3: Pre-conditions
- Server running on the **iteration branch** (not main)
- Health check passes before any browser action
- Required seed data present
- For MCP tool calls: MCP server running and accessible

## Step 4: Execute Tests (per mode, per feature in scope)

**Automated:**
```bash
pytest tests/e2e/ -k "{feature_keywords}" -v
```

**Scripted:** Follow the journey script(s) for this feature's scenarios only:
1. Execute each DO step via browser automation or MCP tool call
2. Assert each SEE condition
3. On RECORD: capture and store placeholder value
4. On CURSOR_PROMPT: stop, display step to user, await confirmation, continue
5. On assertion failure: classify and file (Step 5)

**Exploratory:** For each scenario in the feature spec:
1. Walk the happy path via browser automation
2. Walk the reject path (wrong credentials, empty inputs, boundary values)
3. File any unexpected behavior as a defect

## Step 5: Defect Classification and Reporting

| Severity | Definition |
|----------|------------|
| **Blocker** | Core feature path broken; journey cannot continue |
| **Major** | Feature works but wrong message/redirect/UX; journey continues |
| **Minor** | Cosmetic, label mismatch; journey continues |
| **Test-debt** | Test assertion is stale (conflicts with accepted feature spec) |

```python
report_bug(
    description=(
        f"{feature_id} / {scenario_title} — {step_description}\n\n"
        f"Spec says: {feature_spec_assertion}\n"
        f"Observed: {actual}\n"
        f"Severity: {severity}\n"
        f"Evidence: {screenshot_or_log}"
    ),
    page_context=f"Acceptance — milestone #{N} — branch iteration/{slug} — {ISO8601}"
)
```

```bash
gh issue edit {bug_number} --milestone {N} --add-label "bug,{severity}"
```

Test-debt issues: label `test-debt`, no `bug` label, do not count toward blocker total.

## Step 6: UAT Report

```
=== UAT REPORT ===
Milestone: #{N} | {goal}
Branch:    iteration/{slug}
Scope:     {N} features from feature_file_paths[]
Mode(s):   {automated | scripted | exploratory} per feature

Results by feature:
  {feature_id}: {N} scenarios — {passed}/{total}
  ...

Defects:
  Blockers ({N}): #{list}
  Majors   ({N}): #{list}
  Minors   ({N}): #{list}
  Test-debt({N}): #{list}

Verdict: {CLEAN — proceed to Close | BLOCKERS FOUND — proceed to Fix & Reintegrate}
==================
```

If 0 blockers: skip Fix & Reintegrate, proceed directly to Close.
If 1+ blockers: proceed to Fix & Reintegrate.

## Success Criteria
- Scope locked to `feature_file_paths[]` from manifest (no repository-wide test discovery)
- Scripted tests run only scenarios matching iteration scope
- Precedence rule applied; stale test assertions filed as test-debt, not bugs
- Every defect filed with severity; test-debt separated from bugs
- UAT report produced with per-feature breakdown and routing verdict

## Agent
Saga — medium reasoning model. Executes within declared scope. Applies precedence rule. Files defects. Produces UAT report. Cannot skip assertions, expand scope, or modify test/spec files.

## Rules
`do-informative-logging`, `do-follow-commit-convention`

## Agent

None

## Skill

None

## Rules

None

## Artifacts Produced

- **Bug Report** (Document) - Required

## Artifacts Consumed

None

## Notes

No additional notes.
