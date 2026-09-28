# Activity: Contract

**Activity ID**: 142
**Order**: 3
**Phase**: Construction
**Dependencies**: Predecessor: Activity 140 (Orient & Validate Scope)

## Description

Contract

## Guidance

## Purpose
For each BDD scenario in scope: plan and skeleton it. Planning (BPE-01 — Activity 96, Plan Feature — reasoning: context map, do-not-do list, applicable SAO sections, checkpoint commands, drafted skeleton content) is dispatched **in parallel, one worker per scenario** — it is pure analysis with no repository writes, so there is nothing to conflict over yet. Applying those plans to the working tree (writing skeleton files, verifying checkpoints, committing) is done **sequentially**, one scenario at a time, because that is where real git state is touched. After all scenarios are applied, derive the file-level conflict map from the real commits and write the execution manifest YAML — unchanged from before.

Scope note: this PIP changes *how* scenario planning and skeleton-writing happen (Steps 2-5, below). It does not change the activity's boundary — Steps 6-8 (conflict map, parallel groups, manifest) stayed inside this same activity in the pre-existing version of Contract, and stay here for the same reason: the manifest can't be written until every scenario's real footprint is known, which only happens at the end of Step 5. Splitting manifest-writing into a separate activity is a legitimate structural question, but it's orthogonal to fan-out and is not addressed by this PIP.

## Prerequisites
- Orient summary from PIN-02
- `docs/architecture/SAO.md`
- BDD feature specs from `docs/features/act-{N}/`

## Step 1: Create Iteration Branch (once)
```bash
# Safe for retries — checks before creating
git show-ref --verify --quiet refs/heads/iteration/YYYYMMDD-{goal-slug} \
  && git checkout iteration/YYYYMMDD-{goal-slug} \
  || git checkout -b iteration/YYYYMMDD-{goal-slug}
```

## Step 2: Dispatch Planning Workers (parallel — one per scenario)

Apply rule `do-fan-out-independent-work`. The item list is every scenario in scope. Each worker performs pure analysis and returns a plan — **it must not write to the working tree or make any commit.**

For each scenario, a worker does:

**a) Read Specification and Record Feature File Path.** Read the BDD feature spec for this scenario. Note the exact `.feature` file path.
Record: `feature_file_path: docs/features/act-{N}/{filename}.feature`
Read `docs/architecture/SAO.md`. Note governing sections.

**b) Identify System Dependencies.** Scan the scenario's steps for capabilities requiring external infrastructure not part of this feature's own footprint:

Common patterns to check for:
- "receives a notification" → `notification_service`
- "receives an email" → `email_backend`
- "background task" → `task_queue`
- "search index" → `search_backend`

If found, record as `system_dependencies` and propose a resolution — but **do not act on Option A or C unilaterally**; a worker cannot ask the user mid-dispatch while other workers are also running. Instead the worker records its proposed resolution for the orchestrator to batch:

| Option | When to use | Worker records |
|--------|-------------|-----------------|
| A — Prerequisite scenario | Infrastructure reusable across multiple scenarios | Proposed new scenario S0 + which scenarios would depend on it. Orchestrator batches all such proposals and asks the user once, after all workers report. |
| B — Stub & proceed | Infrastructure is minor, can be stubbed | Worker proceeds autonomously: notes stub in its plan, drafts a stub file named **exactly** after the dependency identifier under the project's existing service-module path (e.g. `notification_service` → `methodology/services/notification_service.py` — this naming convention is pre-existing in Contract, unchanged by this PIP), annotates its manifest entry as `notification_service [STUBBED]`. No user round-trip needed. |
| C — Skip this iteration | Infrastructure substantial, out of scope | Worker flags scenario as a proposed removal from `scenarios_in_scope[]`. Orchestrator batches all such proposals and asks the user once. |

**c) Run BPE-01 (Activity 96, Plan Feature).** Follow BPE/BPE-01 completely, in planning mode. Output must include:
- Context Map — 3–5 `file:line_range` references with one-line note each
- Do-Not-Do List — derived from SAO.md sections
- Applicable SAO.md Sections — by heading name
- Checkpoint Command — pytest command proving behavior done
- Log Story Script — from BPE-01 Section E (Where / Beat / Trigger / Must include)
- Log-story tests + command, when Section E is non-empty

**Important:** skip BPE-01 Step 9 (Submit for Approval) and Step 10 (GitHub/Issue Management) — captured in the manifest instead; PIN-04 creates issues.

**d) Draft the skeleton — as text, not a write.** Draft every class and method (public and private helpers) the implementor will need. The skeleton is the complete architecture; an implementor must not need to add new methods.

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

**e) Return the worker's report.** Each worker's output: proposed `codebase_footprint` (file paths it expects to create/modify — an estimate, not yet a git diff), the drafted skeleton content in full, and all of (a)-(d). This is returned to the orchestrator; nothing is written to disk yet.

## Step 3: Resolve Batched Proposals

Collect every Option-A and Option-C proposal from Step 2b across all workers. Present them to the user together, once:

> "N workers flagged shared-infrastructure or scope proposals: {list}. Confirm before I apply skeletons."

Apply the user's decisions: add any approved S0 prerequisite scenarios (looping them through Step 2 themselves before continuing), remove any approved scope exclusions from `scenarios_in_scope[]` into `scenarios_deferred[]`.

## Step 4: Sanity-Check Proposed Footprints

Before writing anything, compare workers' proposed footprints pairwise. If two scenarios propose creating the *same new file*, resolve it now — ask the user which scenario owns it, or merge the two plans — rather than discovering the collision after skeletons are already committed.

## Step 5: Apply Skeletons Sequentially

For each scenario (order no longer matters for contention — planning is already done, this pass is now fast mechanical work):

1. Write the drafted skeleton content to disk.
2. Verify checkpoint commands:
```bash
{checkpoint.command} 2>&1 | tail -5
# When log_tests present:
{checkpoint.log_story_command} 2>&1 | tail -5
```
Acceptable: `NotImplementedError` or `collected 0 items`. Not acceptable: `ImportError`, `SyntaxError`.
3. Commit:
```bash
git add -A
git commit -m "chore(pin): skeleton S{N} — {scenario title}"
```
4. Record the **actual** footprint (authoritative — supersedes the worker's proposed footprint from Step 2e):
```bash
git diff HEAD~1 --name-only
```
Record as `codebase_footprint[]`. Record `skeleton_commit` hash.

## After All Scenarios Are Applied (same activity, same boundary as before this PIP — see Scope note above):

### Step 6: Build Conflict Map
For each scenario pair, check actual footprint intersection:
```
S1 ∩ S2 = {tools.py} → CONFLICT → serialize
S1 ∩ S3 = {} → no conflict → parallel
```

### Step 7: Assign Parallel Groups
Non-conflicting → same group. Conflicting → different groups with dependency. (This grouping feeds MIN-03's build-time dispatch — not this activity's own already-completed apply pass.)

### Step 8: Write Execution Manifest
Create `docs/plans/iterations/ITER-YYYYMMDD-HHmm-{goal-slug}.yaml`. `doctrine_version` below is a free-text version tag inside this manifest template (not a separate Mimir entity); it is bumped from the pre-existing "2.0" to "2.1" to signal that the manifest is now produced by the fan-out process this PIP introduces, not because a new lookup entity was added:
```yaml
iteration:
  goal: "{iteration_goal}"
  doctrine_version: "2.1"
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

Before dispatching planning workers and writing the manifest, **read** each Rule below in this playbook (by slug), then **apply** it. Do not rely on memory of the rule text.

Required:
- `do-plan-before-doing`
- `do-fan-out-independent-work`
- `do-skeletons-first`
- `do-test-first`
- `do-informative-logging`
- `do-assert-log-story`
- `do-follow-commit-convention`
- `do-small-increments`
- `pytest`

Activity-specific (not a substitute for the rules above):
- Planning workers (Step 2) never write to the working tree or commit — only the sequential apply pass (Step 5) does.
- When BPE-01 Section E (Log Story Script) is non-empty, the manifest must include `log_story_script[]`, `log_tests[]`, and `checkpoint.log_story_command`.

## Success Criteria
- Every in-scope scenario planned by a dedicated worker before any skeleton is written
- Batched Option-A/Option-C proposals resolved with the user in a single round-trip, not per-worker
- Proposed footprints sanity-checked for same-file collisions before Step 5
- Skeleton committed for every scenario, with the *actual* git-diff footprint recorded (not the proposed one)
- `feature_file_paths[]` recorded per scenario
- `system_dependencies[]` recorded per scenario (empty list if none)
- All system_dependencies resolved (stubbed, prerequisite scenario, or deferred) before the manifest is written
- Stub files named to match their dependency identifier so MIN-04's codebase check succeeds
- Execution manifest YAML written to `docs/plans/iterations/`
- Conflict map derived from actual skeleton commits
- All checkpoint commands verified (NotImplementedError or 0 items), including `log_story_command` when declared

## Agent

None

## Skill

None

## Rules

- **Fan Out Independent Work** (`fan-out-independent-work`)

## Artifacts Produced

None

## Artifacts Consumed

None

## Notes

No additional notes.
