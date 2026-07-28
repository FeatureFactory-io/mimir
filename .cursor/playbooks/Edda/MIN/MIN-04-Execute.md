# Activity: Execute

**Activity ID**: 181
**Order**: 4
**Phase**: None
**Dependencies**: None

## Description

Execute

## Guidance

## Purpose
Implement all issues from the execution queue. Assume **dr-dobbs** agent identity. Dispatch subagents in parallel for independent groups; execute sequentially within conflicting groups.

## Identity
Assume the **dr-dobbs** agent identity for all implementation work in this activity. dr-dobbs is a precise, test-driven implementer: fills skeletons without redesigning them, never touches files outside the declared footprint, and surfaces uncertainty rather than guessing.

## Steps

### Step 1: Check System Dependencies Before Starting
From the manifest loaded in MIN-02, check `system_dependencies[]` for each scenario in scope.

For each declared dependency, verify it exists in the codebase:
- `notification_service` → check for a notification module/service (e.g. `methodology/services/notification_service.py`)
- `email_backend` → check Django email settings are configured
- `task_queue` → check for Celery or equivalent
- `search_backend` → check for search index setup

If a declared system dependency does **not** exist:
> **STOP — escalate before any implementation.**
> Post on the first affected issue:
> ```bash
> gh issue comment {N} --body "<!-- ESCALATE -->\
type: system_dependency_missing\
evidence: {dependency_name} required by {scenario_id} but not found in codebase\
recommendation: A: build dependency first | B: stub it | C: defer affected scenarios\
await_human_decision: true\
<!-- /ESCALATE -->"
> ```
> Do not proceed with affected scenarios until human decides.

### Step 2: Dispatch Parallel Groups
For each parallel group from MIN-03's execution queue:
- Multiple READY scenarios in the group → dispatch one subagent per scenario using the `Task` tool concurrently
- Single scenario in the group → execute inline

Subagent task template:
```
Assume dr-dobbs identity. Implement GitHub issue #{N}: {title}.
Get the issue: gh issue view {N} --json number,title,body,labels
Follow BPE-02 → BPE-05 to fill the skeleton.
Run the behavior checkpoint from the issue SCENARIO / manifest.
If log_story_command (or log_tests) is present, run it too — both must PASS in the same commit.
Do not list other issues — get this one only.
```

### Step 3: Per-Issue Execution Loop
For each issue (dispatched or inline):

**a) Get the issue — one at a time, never list-all:**
```bash
gh issue view {N} --json number,title,body,labels
```

**b) Claim it:**
```bash
gh issue edit {N} --add-label "status-in-progress" --remove-label "status-queued"
gh issue comment {N} --body "<!-- EXECUTION_START -->\nStarted: {timestamp}\n<!-- /EXECUTION_START -->"
```

**c) Fill the skeleton** following BPE-02 → BPE-05:
- **BPE-02**: Implement backend (replace `raise NotImplementedError()` with logic), including Log Story Script emission and caplog tests in the same slice
  - If the scenario introduced **new Django models**: run migrations immediately after the model is defined:
    ```bash
    python manage.py makemigrations
    python manage.py migrate
    ```
  - Verify migrations apply cleanly before continuing.
- **BPE-03**: Implement frontend (if applicable)
- **BPE-04**: Feature acceptance tests
- **BPE-05**: Journey certification tests (if applicable)

Do NOT:
- Change method signatures
- Create files outside `codebase_footprint[]`
- Add unplanned public methods
- Quietly redesign the skeleton
- Close on behavior-only green when `log_story_command` is declared

**d) Run checkpoint:**
```bash
{checkpoint.command}
# When declared in the manifest / SCENARIO block:
{checkpoint.log_story_command}
pytest tests/ -x --ignore=tests/e2e 2>&1 | tail -5
```

**e) Evaluate result:**

Checkpoint PASS means **both** behavior and log_story commands pass when `log_story_command` is present, plus regression PASS:
```bash
git add -A
git commit -m "feat({scope}): {title}

Implements {scenario_id} from ITER-{slug}
Checkpoint: {command} — PASSED
Log story: {log_story_command} — PASSED"
gh issue close {N} --comment "<!-- CHECKPOINT_PASS -->\nPassed: {timestamp}\n<!-- /CHECKPOINT_PASS -->"
gh issue edit {N} --remove-label "status-in-progress" --add-label "status-done"
```

Checkpoint FAIL (first time): apply targeted fix, retry once.
- Retry PASS → commit and close as above. Post absorbed drift:
```bash
gh issue comment {N} --body "<!-- DRIFT absorbed -->\ntype: checkpoint_fail\naction: {what was fixed}\nretry: PASS\n<!-- /DRIFT -->"
gh issue edit {N} --add-label "drift-absorbed"
```
- Retry FAIL → escalate:
```bash
gh issue comment {N} --body "<!-- ESCALATE -->\ntype: checkpoint_fail_retry\nevidence: {error summary}\nrecommendation: A: fix and retry | B: resequence | C: scope reduce\nawait_human_decision: true\n<!-- /ESCALATE -->"
gh issue edit {N} --add-label "drift-escalated" --remove-label "status-in-progress"
```

Footprint violation:
```bash
gh issue comment {N} --body "<!-- ESCALATE -->\ntype: footprint_violation\nevidence: File {filename} not in codebase_footprint[]\nawait_human_decision: true\n<!-- /ESCALATE -->"
```

### Step 4: Advance the Queue
After each issue closes: check if any BLOCKED scenario is now unblocked. If yes, dispatch it.

Iteration complete when:
```bash
gh issue list --milestone {N} --state open  # returns empty
```


## Rules

Before filling skeletons and running checkpoints, **read** each Rule below in this playbook (by slug), then **apply** it. Do not rely on memory of the rule text.

Required:
- `do-skeletons-first`
- `do-test-first`
- `do-not-mock-in-integration-tests`
- `do-informative-logging`
- `do-assert-log-story`
- `do-write-concise-methods`
- `do-follow-commit-convention`
- `do-small-increments`
- `pytest`

Activity-specific (not a substitute for the rules above):
- When `checkpoint.log_story_command` is declared, Checkpoint PASS requires **both** behavior and log-story commands in the same commit.

## Success Criteria
- System dependencies checked before any implementation begins
- Migrations run immediately after any new model is defined
- All issues implemented, checkpointed (behavior + log_story when declared), committed, closed with `status-done`
- Parallel groups dispatched concurrently where possible
- Each issue fetched one at a time (`gh issue view`, never list-all)
- Escalations surfaced immediately; no autonomous action while awaiting human
- Ready to proceed to MIN-05

## Agent

None

## Skill

**Title**: Pytest Log Story Assertions

## Rules

- **Assert Log Story** (`assert-log-story`)
- **Informative Logging** (`do-informative-logging`)

## Artifacts Produced

None

## Artifacts Consumed

None

## Notes

No additional notes.
