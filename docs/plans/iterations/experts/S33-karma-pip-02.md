# S33: KARMA-PIP-02 Award an accepted minor change

This plan uses [the consolidated contract](../pin-convergence-20261123-experts.md). Its shared interfaces, ownership decisions and verification-layer mapping govern this scenario. Commands in the graph below are the canonical execution gates; implementation and test bodies remain unimplemented.

```yaml
scenario: S33
acceptance_id: KARMA-PIP-02
feature_file_path: docs/features/act-18-experts/karma-accrual.feature
feature_line: 32
primary_execution_layer: at
expanded_case_count: 20
dependencies:
- S32
system_dependencies: []
status: skeleton_applied_unimplemented
source_report_sha256:
- da438dce2cc147d34e49ade3a65b2d848e88ac902ca23a75ee4c5d7daf7a5603
```

## A — Verified context map


| File:lines | Relevant contract or implemented behavior |
|---|---|
| `docs/features/act-18-experts/karma-accrual.feature:32–57` | Exactly 20 independently restored Examples: seven ALTER, seven DROP, LINK, UNLINK and four ADD. |
| `methodology/services/pip_apply_changes_service.py:251–330,450–640` | Actual ADD Workflow/Phase/Agent/Rule and ALTER/DROP of all seven entities exist; DROP Phase rejects assigned activities. |
| `methodology/services/pip_apply_changes_service.py:360–438,757–801` | Actual relationship application and existing single major-version publication/history receipt. |
| `methodology/services/pip_admin_service.py:24–114,132–147` | Staff/reviewed/released preconditions; atomic application, version, terminal state and `decided_at`; email registered after commit; returns proposal. |
| `test-data/experts/cedar-rfp-01.json:114–185,990–1013` | Maria starts at 8,200 total/7,200 Design; Hana’s target 6106 already reached 2.0 through historical acceptance. |

Read additionally: AGENTS/CLAUDE, Orient roster, supplied PIN/BPE/rules/ownership notes, SAO delta, delivered S30/S32/S45 reports and actual model/service/test bodies.

Existing proofs worth preserving: `test_pip_entity_crud.py::test_alter_and_drop_rule_via_pip`, `::test_alter_and_drop_phase_via_pip`, `::test_add_phase_then_activity_with_phase_ref`; `test_pip_link_changes.py:68–103` proves real `skill_activity` LINK/UNLINK; `test_pip_lifecycle.py:122–170` proves finalization mutates content/version and emails the submitter. Existing email tests prove submitter recipient and change decisions.

## B — Do not do


- Do not equate minor Karma with minor versioning: every accepted single-row PIP still publishes target **2.0 → 3.0**, through existing policy.
- Do not award Hana, administrator Mike, summary generation, fixture construction or historical import.
- Do not classify “anything except major” as minor. Unknown operation/entity/relationship receives zero; S32 owns that policy and its reject proof.
- Exclude ADD Activity/Skill/Artifact from this matrix; their 500-point contract belongs to S32. Partial decisions belong to S34.
- Do not add another award writer, schema, migration, production helper, notification provider or queue.
- Do not weaken staff/submitter permissions, replace working behavior with raising stubs, change finalization return type or republish to test award retry.
- Do not claim fixture-established Reviewed state proves actual Galdr submission/review. Those lifecycle proofs remain S23/S25.
- Do not duplicate S32-owned shared AT total/category/version/notification phrases.

## C — Architecture and implementation contract


Applicable SAO headings: **Awards, projections and transaction boundaries** (`3836–3861`), **Web delivery and notification reuse** (`3897–3910`), **Test strategy for this delta** (`3912–3928`), **Version Management**, **Email Architecture / PIP Decision Email Content / Testing Strategy**.

Use S03 `load_cedar_baseline() → CedarDataset`, including `users_by_username` and `playbooks_by_pk`. Each Example/test invocation restores baseline independently.

Fixture sequence: create dedicated real target entities under Hana’s released playbook 6106; use actual `PIPService.create_draft_for_playbook` and `add_change`; establish a **documented real-ORM Reviewed fixture boundary** with review timestamps/recommendation, leaving admin decision unset; then use actual administrator POST or actual finalization service. No Galdr mock, no deferred callback masquerading as assessment, no S23 dependency.

For ALTER, supply a distinct nonblank name/content and assert the actual entity field changed. For DROP, supply a real existing target and rationale, retain integer snapshots before deletion and assert absence afterward. Use a dedicated empty Phase for DROP; fixture Workflow/Activity/Artifact dependencies must be valid and independent of historical evidence.

Both outline relationship rows mean **`skill_activity`**, with real Skill/Activity IDs in the target playbook. LINK starts absent and ends present; UNLINK starts present and ends absent. Relationship changes persist `entity_type=""`, not an invented entity named “supported existing relationship” (`pip_service.py:389–400`).

For ADD Workflow/Phase/Agent/Rule, use unique names, valid content and real branch requirements. Resolve newly created rows from target/name/internal reference; do not expect finalization to populate `change.target_id`.

S32/S30 receipt contract: singleton `accepted_change:<actual_change_pk>`, channel `accepted_change`, source `minor`, points 100, recipient Maria, canonical category `design`, playbook snapshot 6106, change snapshot actual PK, aware `occurred_at == pip.decided_at`. S45 retry/race policy is consumed, never reimplemented.

## D — Tests and precise assertions


| New test | Assertions |
|---|---|
| `test_minor_case_matrix_with_literal_examples_matches_all_twenty_rows` | Explicit literal matrix equals exact feature Examples in order; length 20, no duplicates, no ADD Activity/Skill/Artifact, neither enum Cartesian product nor sampled subset. |
| `test_finalize_pip_with_each_minor_change_applies_once_and_awards_submitter` | **20 parameters**; actual staff POST succeeds; concrete operation effect verified; PIP accepted; one new PIP-source version receipt for this PIP, 2.0→3.0; Maria 8,300/Design 7,300; Hana 5,800 and Mike 12,450 unchanged; exactly one new 100/minor award with complete receipt/category/time/recipient snapshots; no new release/major award. Real locmem mail contains one decision email to Maria, accepted change and 3.0. |
| `test_finalize_pip_with_minor_service_call_preserves_proposal_return` | Real finalization directly returns persisted `ProcessImprovementProposal`, same PK, accepted status; mutation/history/award agree. |
| `test_finalize_pip_with_nonstaff_preserves_minor_target_and_ledger` | Actual nonstaff POST returns 403; reviewed state, entity, version/history and every ledger total unchanged; no mail. |
| `test_minor_fixture_with_unknown_or_major_row_rejects_before_writes` | Unsupported operation/entity, invented relationship and excluded major ADD rejected by fixture boundary without domain/ledger writes; fixture cannot silently substitute a supported case. Production zero-award policy remains S32’s separate proof. |
| `test_minor_acceptance_log_story_happy` | Explicit 20-case parameterization; `caplog` + existing `assert_log_story` prove minor classification and created singleton with common correlation/PIP/change IDs. Award log records contain no body/email/secrets. |

Use real DB, actual services/views and locmem backend, never patched award/email services. Integration cases use `django_db(transaction=True)` so normal postcommit email actually runs. Behave’s transactional test case uses its existing `captureOnCommitCallbacks(execute=True)` around finalization; report this as callback capture, not a production commit proof.

AT adds only the independent operation/entity When. Reuse S03’s Cedar background and S32-owned parameterized total/category Then bindings. Shared context: `cedar_dataset`, `pip`, `change`, `target_playbook`, `response`; optionally retain `minor_pip_case` for operation-effect assertions.

Future implemented Make targets:

```makefile
test-at-experts-s33:
	DJANGO_SETTINGS_MODULE=mimir.settings.acceptance $(PYTHON) manage.py behave --simple --tags=@experts --name='^KARMA-PIP-02 Award an accepted minor change' docs/features/act-18-experts/karma-accrual.feature
test-experts-s33:
	$(PYTEST) tests/integration/test_experts_karma_minor_pip.py -x
	$(PYTEST) tests/integration/test_experts_karma_minor_pip.py -k log_story -x
	$(MAKE) test-at-experts-s33
	$(PYTEST) tests/integration/test_pip_entity_crud.py tests/integration/test_pip_link_changes.py tests/integration/test_pip_admin_review_view.py -x
```

Require **20 executed AT Examples**, no undefined/failed/skipped selected cases; require all 20 integration happy cases and all 20 log cases. Exact `@experts`/name selection intentionally overrides feature-level WIP. Aggregate Experts readiness remains separate. Do not run broad legacy feature discovery. During PIN reserve these names as comments only.

## E — Log story


S32 supplies production beats; S33 proves their minor classification across the complete matrix.

| Where | Beat | Trigger | Must include |
|---|---|---|---|
| `KarmaService.award_accepted_changes` | entry | Finalization hook | `entry`, `pip_id=`, `correlation_id=` |
| `KarmaService._accepted_change_policy` | processing | Each supported minor row | `processing`, `change_id=`, `operation=`, `source_kind=minor`, `points=100`; actual entity or `relationship_type=skill_activity` |
| `KarmaService.award_accepted_changes` | exit | Singleton persisted | `exit`, `pip_id=`, `created_count=1`, `existing_count=0` |
| `PIPAdminService._award_finalized_pip` | exit | Transaction-local hook returns | `exit`, `pip_id=`, `actor_id=`, `recipient_id=` |

No “committed” claim inside the surrounding atomic block. Existing notification logging is outside the new award-logger privacy assertion. Rejection/unsupported policy log stories remain required S32 evidence; S33 does not duplicate that production responsibility.

## F — MCP tools


Not applicable: no modified MCP tool, registration, facade, client or transport. Existing administrator HTTP/service path only.

## G — Agent proofs


Not applicable: this contract certifies deterministic awards after the real-ORM Reviewed fixture boundary. It neither invokes nor changes agent capability/orchestration. No PRF row, ScriptedLLM, provider, registry or ToolExecutor is introduced. Submission/assessment remains explicitly unproven here.

## H — Mockup graduation and delivery slices


No new UI, production template or browser interaction; BPE-03/BPE-05 omitted. The actual Django-client staff POST proves existing UI delivery wiring. S32 separately certifies the existing browser finalization flow.

PIN-04/05 owns combined approval. Before behavior, require issue A–H/graph/Lessons inline plus docs handoff commit `docs(plan): … Refs #N`. One commit/comment per graph slice; final verified slice `Closes #N`. All gates are proposed, not executed.

## Parent convergence

Authoritative acceptance source: `docs/features/act-18-experts/karma-accrual.feature:32`; 20 expanded case(s), primary layer `at`. Dependencies: S32. The full scenario includes all composed journey/UAT obligations assigned in the consolidated contract. Shared Make/catalog registration belongs only to S03.

## Canonical feature execution graph

```yaml
feature_execution_graph:
  feature_ref: KARMA-PIP-02
  nodes:
  - id: N1-minor-fixtures
    title: Explicit supported matrix and real Reviewed fixtures
    bpe: BPE-02
    depends_on: []
    footprint:
    - tests/integration/test_experts_karma_minor_pip.py
    - tests/support/experts_pip_minor.py
    tests:
    - test_minor_case_matrix_with_literal_examples_matches_all_twenty_rows
    - test_minor_fixture_with_unknown_or_major_row_rejects_before_writes
    gate:
      command: pytest tests/integration/test_experts_karma_minor_pip.py -k 'matrix or fixture' -x
    guidance_bundle:
      activity: BPE/BPE-02-Implement_Backend.md
      rules:
      - do-skeletons-first
      - do-test-first
      - do-not-mock-in-integration-tests
      - do-docstring-format
      - do-write-concise-methods
  - id: N2-minor-finalization
    title: Twenty real finalizations with publication, receipt, notification and logs
    bpe: BPE-02
    depends_on:
    - N1-minor-fixtures
    footprint:
    - tests/integration/test_experts_karma_minor_pip.py
    tests:
    - test_finalize_pip_with_each_minor_change_applies_once_and_awards_submitter
    - test_finalize_pip_with_minor_service_call_preserves_proposal_return
    - test_finalize_pip_with_nonstaff_preserves_minor_target_and_ledger
    - test_minor_acceptance_log_story_happy
    log_story_rows:
    - KarmaService.award_accepted_changes:entry
    - KarmaService._accepted_change_policy:processing
    - KarmaService.award_accepted_changes:exit
    - PIPAdminService._award_finalized_pip:exit
    gate:
      command: pytest tests/integration/test_experts_karma_minor_pip.py -x
      log_story_command: pytest tests/integration/test_experts_karma_minor_pip.py -k log_story -x
    guidance_bundle:
      activity: BPE/BPE-02-Implement_Backend.md
      rules:
      - do-test-first
      - do-not-mock-in-integration-tests
      - do-assert-log-story
  - id: N3-minor-living-at
    title: Run the exact twenty-example living contract
    bpe: BPE-04
    depends_on:
    - N2-minor-finalization
    footprint:
    - docs/features/steps/experts_karma_pip_steps.py
    gate:
      command: make test-experts-s33-at
    guidance_bundle:
      activity: BPE/BPE-04-Implement_Feature_Acceptance_Tests.md
      rules:
      - do-test-first
      - do-not-mock-in-integration-tests
  - id: N4-minor-done
    title: Conjunctive matrix, logs, twenty-example AT and regression certification
    bpe: BPE-06
    depends_on:
    - N3-minor-living-at
    footprint: []
    gate:
      command: make test-experts-s33
      log_story_command: pytest tests/integration/test_experts_karma_minor_pip.py -k log_story -x
    guidance_bundle:
      activity: BPE/BPE-06-Check_Definition_of_Done.md
      rules:
      - do-test-first
      - do-assert-log-story
      - do-github-issues
  scenario_dependencies:
  - S32
```

## Lessons Learned

- Current Phase is a real model with apply support; stale CLAUDE hierarchy prose must not exclude its Examples.
- Relationship change rows have blank entity type; checking entity enums first would wrongly suppress valid minor awards.
- A 100-point change still creates a major publication; assert both independent contracts.
- DROP tests need valid deletion preconditions and durable IDs, otherwise a classification test can pass without proving successful application.
- Historical Maria PIP points already exist; independent baseline restoration and event-specific deltas prevent accidental replay.
- Reviewed fixture certification is deliberately narrower than Galdr lifecycle certification. All gates above remain unexecuted.

## Structural application evidence

`docs/experts-replay/pin-evidence/S33.json` records positive scaffold selection and deliberate NotImplementedError. Existing callable ASTs were preserved. Browser collection is not interaction certification.

## Actual structural footprint

`docs/experts-replay/pin-evidence/S33.json`, `docs/features/steps/experts_karma_pip_steps.py`, `docs/plans/iterations/experts/S33-karma-pip-02.md`, `tests/integration/test_experts_karma_minor_pip.py`, `tests/support/experts_pip_minor.py`

Skeleton: `ff853d42744a376507131344913dfdacd047851e`; shared reconciliation: `39d598328d438d09723b6eb14574fbf92fab71c9`. Semantic and physical-file dependencies are recorded separately in the iteration manifest. Context-map line ranges record the workers’ inspection baseline; headers and the final scaffold remain authoritative.
