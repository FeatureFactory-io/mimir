# Activity: Contract

**Activity ID**: 142
**Order**: 3
**Phase**: Construction
**Dependencies**: Predecessor: Activity 140 (Orient & Validate Scope)

## Description

Contract

## Guidance

## Purpose
For each BDD scenario in scope: run BPE-01 planning, create code skeletons (public + private helpers), build the context map and do-not-do list, verify checkpoint commands (behavior and log-story when applicable). After all scenarios: derive the file-level conflict map and write the execution manifest YAML.

## Prerequisites
- Orient summary from PIN-02
- `docs/architecture/SAO.md`
- BDD feature specs from `docs/features/act-{N}/`

## Steps

### Step 1: Create Iteration Branch (once)
```bash
# Safe for retries — checks before creating
git show-ref --verify --quiet refs/heads/iteration/YYYYMMDD-{goal-slug} \
  && git checkout iteration/YYYYMMDD-{goal-slug} \
  || git checkout -b iteration/YYYYMMDD-{goal-slug}
```

### Steps 2–8 repeat for each scenario

### Step 2: Read Specification and Record Feature File Path
Read the BDD feature spec for this scenario. Note the exact `.feature` file path — you will record it in the manifest.

Record: `feature_file_path: docs/features/act-{N}/{filename}.feature`

Read `docs/architecture/SAO.md`. Note governing sections.

### Step 3: Identify System Dependencies
Before running BPE-01, scan the scenario's steps for capabilities that require external infrastructure (not part of this feature's codebase footprint):

Common patterns to check for:
- "receives a notification" → `notification_service`
- "receives an email" → `email_backend`
- "background task" → `task_queue`
- "search index" → `search_backend`

If any are found: record them as `system_dependencies` for this scenario.

**If the infrastructure doesn't exist in the codebase, choose a resolution before proceeding:**

| Option | When to use | Action |
|--------|-------------|--------|
| A — Prerequisite scenario | Infrastructure is reusable across multiple scenarios | Create a separate scenario S0 covering the infrastructure; add it as a dependency to all affected scenarios. Ask user before doing this. |
| B — Stub & proceed | Infrastructure is minor and can be stubbed | Note stub in BPE-01 plan; create a stub file named **exactly** after the dependency identifier (e.g. `notification_service` → `methodology/services/notification_service.py`) with a no-op implementation; include it in the skeleton commit; annotate the manifest entry as `notification_service [STUBBED]`. MIN-04 checks for this file by name — the naming must match or MIN-04 will falsely escalate. Decide autonomously, note in manifest. |
| C — Skip this iteration | Infrastructure is substantial and out of scope | Remove scenario from `scenarios_in_scope[]`; add to `scenarios_deferred[]` in orient summary. Ask user before doing this. |

### Step 4: Run BPE-01
Follow BPE/BPE-01 completely. Output must include:

**a) Context Map** — 3–5 `file:line_range` references with one-line note each.

**b) Do-Not-Do List** — derived from SAO.md sections:
```
- Do NOT create a new Django app
- Do NOT add a manager/repository layer
```

**c) Applicable SAO.md Sections** — list by heading name.

**d) Checkpoint Command** — pytest command that proves behavior done.

**e) Log Story Script** — from BPE-01 Section E (Where / Beat / Trigger / Must include).

**f) Log-story tests + command** — when Section E is non-empty: `log_tests[]` names/paths and `checkpoint.log_story_command`.

**Important:** When running BPE-01 inside PIN-03, **skip BPE-01 Step 9 (Submit for Approval) and BPE-01 Step 10 (GitHub/Issue Management)**. The implementation plan is captured in the manifest; GitHub/GitLab issues are created in PIN-04. Running those steps here would produce duplicates.

### Step 5: Create Thorough Skeleton
Write skeletons for every class and method — public AND private helpers. The skeleton is the complete architecture; an implementor must not need to add new methods.

Production skeleton example:
```python
class FeatureService:
    def execute(self, id: int, user) -> dict:
        """
        :param id: Feature ID. Example: 42
        :param user: Requesting user.
        :return: dict. Example: {"id": 42, "name": "..."}
        :raises PermissionError: If user cannot access
        :raises ValueError: If not found
        """
        raise NotImplementedError()

    def _validate(self, id, user) -> None:
        raise NotImplementedError()

    def _serialize(self, obj) -> dict:
        raise NotImplementedError()
```

### Step 6: Verify Checkpoint Commands
```bash
{checkpoint.command} 2>&1 | tail -5
# When log_tests present:
{checkpoint.log_story_command} 2>&1 | tail -5
```
Acceptable: `NotImplementedError` or `collected 0 items`.
Not acceptable: `ImportError`, `SyntaxError`.

### Step 7: Commit Skeleton
```bash
git add -A
git commit -m "chore(pin): skeleton S{N} — {scenario title}"
```

### Step 8: Record Footprint
```bash
git diff HEAD~1 --name-only
```
Record as `codebase_footprint[]`. Record `skeleton_commit` hash.

### After All Scenarios:

### Step 9: Build Conflict Map
For each scenario pair, check footprint intersection:
```
S1 ∩ S2 = {tools.py} → CONFLICT → serialize
S1 ∩ S3 = {} → no conflict → parallel
```

### Step 10: Assign Parallel Groups
Non-conflicting → same group. Conflicting → different groups with dependency.

### Step 11: Write Execution Manifest
Create `docs/plans/iterations/ITER-YYYYMMDD-HHmm-{goal-slug}.yaml`:
```yaml
iteration:
  goal: "{iteration_goal}"
  doctrine_version: "2.0"
  created_at: "{ISO8601}"

conflict_map:
  path/to/file.py: [S1, S2]

parallel_groups:
  A: [S1]
  B: [S3]
  C: [S2]

drift_thresholds:
  absorbed:
    checkpoint_fail_retry: 1
  escalated:
    footprint_violation: true
    method_explosion: true
    sao_violation: true
    checkpoint_fail_after_retry: true

scenarios:
  S1:
    title: "{title}"
    parallel_group: A
    skeleton_commit: "{hash}"
    codebase_footprint: [...]
    feature_file_paths:
      - docs/features/act-{N}/{filename}.feature
    system_dependencies:
      - notification_service   # or empty list [] if none; append [STUBBED] if stubbed
    log_story_script:
      - {beat: entry, where: "LoginView.post", trigger: method_called, must_include: ["email="]}
      - {beat: branch, where: "LoginView.post", trigger: bad_credentials, must_include: ["authentication failed"]}
    log_tests:
      - {name: test_login_log_story_reject, path: src/yggdrasil/auth/tests/test_login_view.py}
    checkpoint:
      command: "pytest ...::test_login_post_failure_rerenders_with_error -x"
      expected_exit_code: 0
      log_story_command: "pytest ...::test_login_log_story_reject -x"  # required when log_tests non-empty
    dependencies: []
    context_map: [...]
    do_not_do: [...]
    sao_sections: [...]
```

Rules:
- If `log_tests` is non-empty, `checkpoint.log_story_command` is **required**
- Omit `log_story_script` / `log_tests` / `log_story_command` only when BPE-01 Section E is empty (document why)
- PIN-04 consumers may embed both commands in the issue SCENARIO block


## Rules

Before running BPE-01 inside this activity and writing the manifest, **read** each Rule below in this playbook (by slug), then **apply** it. Do not rely on memory of the rule text.

Required:
- `do-plan-before-doing`
- `do-skeletons-first`
- `do-test-first`
- `do-informative-logging`
- `do-assert-log-story`
- `do-follow-commit-convention`
- `do-small-increments`
- `pytest`

Activity-specific (not a substitute for the rules above):
- When BPE-01 Section E (Log Story Script) is non-empty, the manifest must include `log_story_script[]`, `log_tests[]`, and `checkpoint.log_story_command`.

## Success Criteria
- Skeleton committed for every scenario
- `feature_file_paths[]` recorded per scenario (paths to .feature files)
- `system_dependencies[]` recorded per scenario (empty list if none)
- All system_dependencies resolved (stubbed, prerequisite scenario, or deferred) before proceeding
- Stub files named to match their dependency identifier so MIN-04's codebase check succeeds
- Execution manifest YAML written to `docs/plans/iterations/`
- Conflict map derived from actual skeleton commits
- All checkpoint commands verified (NotImplementedError or 0 items), including `log_story_command` when declared

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
