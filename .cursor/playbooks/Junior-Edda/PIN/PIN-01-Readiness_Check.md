# Activity: Readiness Check

**Activity ID**: 136
**Order**: 1
**Phase**: Construction
**Dependencies**: None

## Description

Readiness Check

## Guidance

## Purpose
Validate all prerequisites before planning begins. User provides a goal sentence (e.g. "we aim to complete act-11"). Each gate is checked in order — if any fails, stop with specific remediation instructions.

## Input
The user's stated goal sentence. Example: "we aim to complete act-11" or "implement team management features".

## Gates

### Gate 1 — BSP (Bootstrap)
Check that the project has been bootstrapped:
```bash
test -f Makefile && echo "PASS" || echo "FAIL: Run BSP workflow — project not bootstrapped"
test -f requirements.txt && echo "PASS" || echo "FAIL: Run BSP workflow — requirements.txt missing"
```
If either fails: **STOP** — "Project not bootstrapped. Run the BSP (Bootstrap Project) workflow first."

### Gate 2 — User Journey Coverage
Identify the target act from the user's goal (e.g. "act-11", "team management"). Check `docs/features/user_journey.md` for a matching section:
```bash
grep -i "act-{N}" docs/features/user_journey.md && echo "PASS" || echo "FAIL"
```
If missing: **STOP** — "No user journey section found for {target}. Add the act section to `docs/features/user_journey.md` before planning."

### Gate 3 — Feature Specs (BDD)
Check that `docs/features/act-{N}/` exists and contains `.feature` files:
```bash
ls docs/features/act-{N}/*.feature 2>/dev/null && echo "PASS" || echo "FAIL"
```
If missing: **STOP** — "No feature specs found for act-{N}. Run the ESM (Envision the System) workflow to produce `.feature` files."

### Gate 4 — Architecture (SAO.md)
```bash
test -f docs/architecture/SAO.md && echo "PASS" || echo "FAIL"
```
If missing: **STOP** — "No `docs/architecture/SAO.md` found. Run the DTA (Define Architecture) workflow first."

### Gate 5 — AI IDE Config (DSP)
```bash
test -f CLAUDE.md && echo "PASS" || echo "FAIL"
```
If missing: **STOP** — "No `CLAUDE.md` found. Run the DSP (Deploy Software Process) workflow to configure the AI IDE."

### Gate 6 — Agent proof harness (optional; when SAO §17 applies)
When `docs/architecture/SAO.md` §17 documents in-app LLM agents (not "Not applicable"):
```bash
test -f tests/support/agent_story.py && echo "PASS" || echo "FAIL: TFK-02 must bootstrap tests/support/agent_story.py before agent-feature BPE"
```
If SAO §17 is N/A: **SKIP** — record `agent_harness: n/a`.

If SAO §17 applies and the file is missing: **STOP** — "Agent proof helper missing. Run TFK-02 (Bootstrap Test Harness) to create `tests/support/agent_story.py` and ScriptedLLM fixtures before planning agent features."

## Mockup Check (advisory, after all gates pass)
```bash
ls docs/ux/mockups/act-{N}/ 2>/dev/null && echo "Mockups found" || echo "No mockups"
```
If no mockups: ask — "No mockups found for {target}. Create them per ESM-04 before planning? (yes/no)"
- Yes → run ESM-04, then return to PIN-01 after mockups are created
- No → proceed with feature specs only

## Output
When all gates pass:
- `target_act`: extracted act identifier (e.g. "act-11")
- `feature_files[]`: list of `.feature` files in `docs/features/act-{N}/`
- `has_mockups`: boolean
- `agent_harness`: `ready` | `n/a` (from Gate 6)

Proceed to PIN-02 Orient & Validate Scope.

## Success Criteria
- All required gates pass (Gates 1–5; Gate 6 pass or skipped when SAO §17 N/A)
- User has confirmed mockup status
- `target_act` and `feature_files[]` identified
- `agent_harness` recorded when SAO §17 applies

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
