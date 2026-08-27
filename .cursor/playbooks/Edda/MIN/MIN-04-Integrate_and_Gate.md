# Activity: Integrate & Gate

**Activity ID**: 182
**Order**: 4
**Phase**: None
**Dependencies**: Predecessor: Activity 181 (Build)
Successor: Activity 183 (UAT Agent)

## Description

Team Lead runs one full integrate-and-gate cycle per feature, issue by issue: verify node commits landed, run BPE-06 (Definition of Done), run BPE-07 (Finalize Feature), commit, and close the issue. No issue advances to UAT until its gate is clean. The iteration exits this activity only when every issue is closed with `status-done`.

## Guidance

This activity runs **interleaved with MIN-03 Build**: as soon as an issue receives `BUILD_COMPLETE`, TL starts its gate cycle — without waiting for all other issues to finish building. Parallel build + integrate is the default when conflict_map allows.

---

## Per-Issue Cycle

Repeat the following for each issue that posts `BUILD_COMPLETE`:

### Step 1: Verify Node Commits

```bash
gh issue view {N} --json comments | jq '[.comments[] | select(.body | contains("NODE_PASS"))] | length'
```

Count must equal the total number of nodes in this issue's `feature_execution_graph`. If any node is missing NODE_PASS: do not proceed — return to MIN-03 Build for that node.

Verify commits landed on the current branch:

```bash
git log --oneline -20   # confirm node commit messages reference issue #{N}
```

### Step 2: Run BPE-06 — Check Definition of Done

Run BPE-06 inline (TL acts as DoD reviewer — not a subagent).

Read the full BPE-06 checklist from `.cursor/playbooks/Edda/BPE/BPE-06-Check_Definition_of_Done.md` and apply each item to this issue's commits.

**Mandatory checks (must all pass before closing):**

| Domain | Check |
|--------|-------|
| Test-first | Every new method/function has corresponding pytest tests |
| Continuous testing | `pytest tests/ -x --ignore=tests/e2e` exits 0 |
| Concise methods | Public methods ≤ 30 lines; helpers extracted |
| Import management | All imports at module level; none inside functions |
| Log story | If `checkpoint.log_story_command` declared: caplog test passes (`pytest {log_story_command}`) |
| Commit convention | Recent commits follow Angular format (`feat`, `fix`, etc.) |
| Semantic naming | All interactive elements have `data-testid` attributes |
| No mocks | Integration tests use real objects/DB |
| Feature files | BDD `.feature` files exist and match behavior |

**On deviation found:**
1. If fixable in < 5 lines (missing testid, import placement, commit message): fix inline.
2. If non-trivial: dispatch a targeted dr-dobbs worker with the exact deviation description. After worker posts NODE_PASS for the fix: re-run BPE-06 check for that domain only.
3. If user approval needed (deferred cleanup): file a GitHub issue with label `deferred` and document the skip in the gate comment.

**Log story gate:**

```bash
{checkpoint.log_story_command}   # must exit 0; skip only if not declared in manifest
```

### Step 3: Run BPE-07 — Finalize Feature

Run BPE-07 inline. Read `.cursor/playbooks/Edda/BPE/BPE-07-Finalize_Feature.md` and apply:

**3a. Full test suite:**

```bash
pytest tests/ -x --ignore=tests/e2e 2>&1 | tail -20
```

100% pass rate required. Any failure: dispatch targeted dr-dobbs fix, rerun. Do not proceed with failures.

**3b. Dependencies:**

```bash
pip freeze | diff - requirements.txt   # or manual diff
```

If any package was installed during this feature and is missing from `requirements.txt`: add it.

**3c. Scenario terminal checkpoint:**

```bash
{checkpoint.command}
```

This must exit 0. On fail: targeted dr-dobbs fix → retry once → escalate if still failing.

**3d. Screen-flow diagram (when applicable):**

If this feature adds or changes screens: update `docs/ux/2_dialogue-maps/screen-flow.drawio`:
- Change completed screen `strokeColor` to `#22c55e`
- Add `strokeWidth=3` if not present
- Add ✅ prefix to screen label

**3e. Final commit:**

```bash
git add -A
git commit -m "$(cat <<'EOF'
feat({scope}): finalize {feature_title}

Closes #{N} — all nodes NODE_PASS; DoD clean; checkpoint PASS.
EOF
)"
```

### Step 4: Close Issue

```bash
gh issue close {N} --comment "$(cat <<'EOF'
<!-- GATE_PASS -->
DoD: clean
Checkpoint: {command} — PASS
Log story: {log_story_command} — PASS (or: not declared)
Commits: {sha_list}
Ready for: MIN-05 UAT Agent
<!-- /GATE_PASS -->
EOF
)"
gh issue edit {N} --remove-label "status-in-progress" --add-label "status-done"
```

### Step 5: Advance the Queue

After closing this issue: check MIN-03 Build for any newly unblocked READY scenarios (their `dependencies[]` now satisfied). Signal MIN-03 to dispatch them.

---

## Exit Gate — All Issues Integrated

Iteration exits this activity when:

```bash
gh issue list --milestone {N} --state open --json number,title | jq 'length'
# must return 0
```

Verify every closed issue has:
- All NODE_PASS comments present
- `GATE_PASS` comment present
- Label `status-done`

Then proceed to MIN-05 UAT Agent.

---

## Rules

Required:
- `do-test-first`
- `do-continuous-testing`
- `do-write-concise-methods`
- `do-import-on-module-level`
- `do-informative-logging`
- `do-assert-log-story`
- `do-not-mock-in-integration-tests`
- `do-follow-commit-convention`
- `do-semantic-versioning-on-ui-elements`
- `do-write-scenarios`

## Success Criteria

- Every issue has all NODE_PASS comments before gate begins
- BPE-06 DoD checklist applied and clean (or deviations documented + deferred)
- Log story gate passed when `log_story_command` declared
- Full test suite at 100% pass before each issue closes
- Scenario terminal checkpoint passes
- Screen-flow diagram updated for any new/changed screens
- All issues closed with `status-done` and `GATE_PASS` comment
- Zero open issues in milestone before proceeding to MIN-05

## Agent

None — Team Lead (TL) runs this activity inline. TL may dispatch targeted dr-dobbs workers for specific DoD deviations (see Step 2).

## Skill

None

## Artifacts Produced

None

## Artifacts Consumed

- **BPE-06 Check Definition of Done** — applied as inline checklist
- **BPE-07 Finalize Feature** — applied as inline steps

## Notes

No additional notes.
