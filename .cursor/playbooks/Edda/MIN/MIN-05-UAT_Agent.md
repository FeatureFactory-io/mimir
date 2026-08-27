# Activity: UAT Agent

**Activity ID**: 183
**Order**: 5
**Phase**: None
**Dependencies**: Predecessor: Activity 182 (Integrate & Gate)
Successor: Activity 184 (Fix & Reintegrate)

## Description

Saga (UAT Agent) runs the full user acceptance test suite from `tests/uat/` using browser automation and MCP tool calls — journey by journey, step by step. Every `IF DIFFER` becomes a filed bug. Every blocker gates MIN-06. The iteration does not close until UAT is clean.

## Guidance

## Model Tier

**Saga (UAT Agent):** medium reasoning model. Reads `.feature` files and executes them literally — no creative interpretation, no skipping. A step either passes or produces an `IF DIFFER` defect report.

---

## Pre-Conditions (verify before starting journeys)

**1. Server running:**

```bash
make run   # or: python manage.py runserver 8000 &
```

Wait for `Starting development server at http://127.0.0.1:8000/` in logs. Confirm with:

```bash
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/
# expect 200 or 302
```

**2. Admin superuser exists:**

```bash
python manage.py shell -c "from django.contrib.auth import get_user_model; print(get_user_model().objects.filter(is_superuser=True).exists())"
# must print True
```

If False: `python manage.py createsuperuser --username admin`

**3. MCP server accessible (for MCP journey legs):**

```bash
python manage.py mcp_server --user=admin &
```

**4. Placeholder registry initialized:**

Create an in-memory registry for `PLACEHOLDER REGISTRY` values declared in the feature files. Populate as you RECORD values during journey execution.

---

## Journey Execution Protocol

Read `tests/uat/e2e-uat-flow.feature` and `tests/uat/mcp-uat-flow.feature` in full before starting.

Follow the **Execution order** declared at the top of `e2e-uat-flow.feature`:
1. J0 (optional guest evaluation)
2. J1 (registration + token RECORD)
3. MCP-00 (token wire)
4. J3 (GUI CRUDL)
5. MCP-01/02/03
6. J5 (release)
7. MCP-06/07
8. J6 browser (PIP UI)
9. MCP-08/08b/08c/08d/09
10. J7 (admin finalize)
11. MCP-11

**For each scenario:**

1. Read the `# STEP` / `# DO` / `# SEE` / `# IF DIFFER` / `# RECORD` blocks literally
2. Execute the `DO` action using browser automation tools (`cursor-ide-browser` MCP) or MCP tool calls as appropriate
3. Assert the `SEE` condition:
   - For `data-testid` selectors: use `browser_snapshot` to locate the element
   - For URL assertions: use `browser_navigate` + `browser_snapshot`
   - For flash message assertions: locate `[data-testid="alert-message"]` text
   - For HTTP status assertions: use `browser_cdp` Network inspection
4. On `RECORD`: extract the value from the page and store in placeholder registry
5. On `IF DIFFER`: capture evidence and file a bug (see below)

**Browser tool priority for selectors:** `data-testid` → `name`/`id` attribute → readable label substring

---

## Defect Reporting Protocol

When a `SEE` assertion fails:

**1. Capture evidence:**

```bash
# Screenshot the current state
# Note: actual URL, actual element text or absence, HTTP status
```

Take a `browser_take_screenshot` of the current page state.

**2. Classify severity:**

| Severity | Definition |
|----------|-----------|
| **Blocker** | Core feature path broken; cannot continue this journey without a fix |
| **Major** | Feature works but degraded UX, wrong message, wrong redirect; journey can continue via workaround |
| **Minor** | Cosmetic mismatch, label text differs, style issue; journey continues normally |

**3. File the bug:**

```python
report_bug(
    description=(
        f"UAT {scenario_id} STEP {step_id} — IF DIFFER\n\n"
        f"Expected: {see_assertion}\n"
        f"Actual: {what_was_observed}\n"
        f"Severity: {severity}\n"
        f"Screenshot: {screenshot_path}\n"
        f"Placeholder state: {relevant_placeholder_values}"
    ),
    page_context=f"MIN-05 UAT Agent — milestone #{N} — {ISO8601_timestamp}"
)
```

Link to milestone:
```bash
gh issue edit {bug_issue_number} --milestone {N} --add-label "bug" --add-label "{blocker|major|minor}"
```

**4. On Blocker:** note that this journey leg cannot continue. Skip remaining steps of this scenario that depend on the failed step. Move to the next scenario. Do not mark the journey as passed.

**5. On Major/Minor:** file the issue, continue the journey.

---

## UAT Report

After all journeys complete, produce:

```
=== UAT REPORT ===
Milestone: #{N} | {goal}
Run date:  {ISO8601}

Journey results:
  J0  Guest eval:         {PASS | SKIP | N scenarios, M failed}
  J1  Registration:       {PASS | N scenarios, M failed}
  MCP-00  Token wire:     {PASS | FAIL}
  J3  GUI CRUDL:          {PASS | N scenarios, M failed}
  MCP-01/02/03:           {PASS | N scenarios, M failed}
  J5  Release:            {PASS | FAIL}
  MCP-06/07:              {PASS | FAIL}
  J6  PIP UI:             {PASS | N scenarios, M failed}
  MCP-08/08b/08c/08d/09:  {PASS | FAIL}
  J7  Admin finalize:     {PASS | FAIL}
  MCP-11:                 {PASS | FAIL}
  J8  Teams:              {PASS | N scenarios, M failed}

Defects filed:
  Blockers ({N}): #{issue_list}
  Majors   ({N}): #{issue_list}
  Minors   ({N}): #{issue_list}

Verdict: {CLEAN — proceed to MIN-07 | BLOCKERS FOUND — proceed to MIN-06}
==================
```

**If 0 blockers:** skip MIN-06, proceed directly to MIN-07 Close Iteration.
**If 1+ blockers:** proceed to MIN-06 Fix & Reintegrate.

---

## Rules

- `do-not-mock-in-integration-tests` — UAT tests real running system; no stubs
- `pytest` — when MCP tool tests are run via pytest, follow pytest conventions

## Success Criteria

- Server confirmed running before any journey begins
- All journeys executed in declared order (J0→J8 interleaved with MCP legs)
- Every `IF DIFFER` has a filed GitHub issue linked to milestone and classified by severity
- Placeholder registry kept current throughout (RECORD values flow forward correctly)
- UAT report produced with journey-level pass/fail breakdown
- Blocker count declared; routing to MIN-06 or MIN-07 determined

## Agent

**Name**: Saga

**Model tier**: medium reasoning model

**Role**: UAT acceptance runner. Reads `.feature` files literally. Executes DO steps via browser automation and MCP tools. Asserts SEE conditions. Files `IF DIFFER` as bug reports. Produces UAT report with severity-classified defect inventory.

**Authority:**
- Can decide: which `data-testid` selector to use when multiple options exist, whether to screenshot before or after an assertion
- Must stop and report: when a Blocker prevents journey from continuing, when the server is unreachable, when a CURSOR_PROMPT manual action is required
- Cannot do: skip a `SEE` assertion, change the journey order, modify `.feature` files, interpret an ambiguous step creatively (flag as `IF DIFFER` instead)

## Skill

None

## Artifacts Produced

- UAT Report (inline — posted as milestone comment)
- Bug issues (one per `IF DIFFER` on GitHub)

## Artifacts Consumed

- `tests/uat/e2e-uat-flow.feature`
- `tests/uat/mcp-uat-flow.feature`

## Notes

CURSOR_PROMPT steps in the feature files require manual user action. When Saga encounters one: stop, display the step to the user, wait for confirmation, then continue.
