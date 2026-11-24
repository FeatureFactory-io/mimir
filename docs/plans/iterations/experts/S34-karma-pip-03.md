# S34: KARMA-PIP-03 Award only accepted changes in a partial decision

This plan uses [the consolidated contract](../pin-convergence-20261123-experts.md). Its shared interfaces, ownership decisions and verification-layer mapping govern this scenario. Commands in the graph below are the canonical execution gates; implementation and test bodies remain unimplemented.

```yaml
scenario: S34
acceptance_id: KARMA-PIP-03
feature_file_path: docs/features/act-18-experts/karma-accrual.feature
feature_line: 59
primary_execution_layer: at
expanded_case_count: 1
dependencies:
- S32
- S33
system_dependencies: []
status: skeleton_applied_unimplemented
source_report_sha256:
- f26ae2e2c3b925cd1b4447c01133fa798078fdc7c81ca19ae39c7c449d8b4104
```

## A — Verified context map


| Source | What the implementer must preserve |
|---|---|
| `docs/features/act-18-experts/karma-accrual.feature:59–62` | Exactly one ADD Activity accepted and one ALTER Activity rejected; Maria 8,700, never 8,800. |
| `methodology/services/pip_admin_service.py:24–114,132–147` | Staff-only reviewed-state finalization; accepted-only application; one publication; terminal partial status; email registered with `on_commit`. |
| `methodology/services/pip_apply_changes_service.py:198–235,757–801` | Real ADD requires a target workflow; publication creates one PIP-linked major version receipt with before/after snapshots. |
| `methodology/services/pip_notification_service.py:16–83` and `templates/pips/email_decision.txt:5–19` | Normal partial notification lists both decisions and resulting version; recipient is submitter; no existing Karma earnings copy. |
| `test-data/experts/cedar-rfp-01.json:114–192,308–355,762–772,990–1013` | Maria baseline 8,200/Design 7,200, Hana 5,800, target 6106 at 2.0; EV06 is partial acceptance. Historical Maria PIP already awarded 600 and must remain unchanged. |

Additional existing evidence: `tests/integration/test_pip_admin_review_view.py:225–250` proves partial application, but accepts ALTER and rejects ADD—the reverse of this contract. Reusing it unchanged would certify the wrong award. `tests/integration/test_pip_email.py:130–214` proves real locmem mail, but lacks this mixed-decision oracle. `methodology/pip_views.py:656–678` supplies the truthful existing message, “PIP partially accepted — changes applied.”

## B — Do not do


- No new production writer, classifier, hook, versioning logic, notification service or schema. S03 supplies foundation; S32 owns accepted-change policy and finalization wiring; S30 remains ledger writer.
- No 100-point award for rejected ALTER; no author/admin award or repeat first-release award.
- Do not equate a major version bump with every change earning 500.
- Do not grant Maria staff privileges or broaden PIP access.
- Do not replay historical Cedar PIPs through live hooks.
- Do not send mail before transaction commit, award inside the mail callback, or invent an earnings amount in existing messages.
- Do not claim manual reviewed fixtures prove submission, Galdr assessment or summary generation.
- No browser journey is needed for this domain acceptance contract; S32 certifies the existing administrator controls.

## C — Governing architecture and fixture


Applicable SAO headings: **Experts & Karma delivery architecture — planned delta**, **Awards, projections and transaction boundaries**, **Web delivery and notification reuse**, **Test strategy for this delta**, **4. Version Management**, **Email Architecture**, **PIP Decision Email Content**.

Create an independent real fixture after restoring S03 Cedar:

1. Resolve Maria `mrodriguez`, staff Mike `mchen`, Hana’s released public playbook `6106`, its real workflow and an existing Activity.
2. Through existing `PIPService.create_draft_for_playbook` and `add_change`, create a new proposal with exactly two distinct changes: ADD Activity and ALTER of that existing Activity. Reuse S32’s ADD payload builder; rejected content uses a unique sentinel.
3. Establish reviewed ORM fixture state with persisted timestamps/recommendations only after both draft changes exist. Leave admin decisions unset. This deliberately bypasses assessment, not authorization during finalization.
4. Preserve baseline totals, ledger rows and version history; no award or notification during fixture preparation.
5. Actual Django-client POST as Mike accepts ADD and rejects ALTER. Finalization uses existing services and S32 hook.
6. Compare actual persisted content, immutable ledger delta, publication receipt, response message and real postcommit mail.

Identity is S32’s `accepted_change:<accepted_change_pk>`; channel `accepted_change`; source `major`; points 500; recipient Maria; Design category snapshot; playbook/change integer snapshots; timestamp equals persisted decision time.

## D — Tests and exact assertions


| Test | Required assertions |
|---|---|
| `test_partial_fixture_with_reviewed_state_preserves_baseline` | Exactly two real distinct changes on Hana6106 v2.0; Maria creator; Mike already staff/Maria not staff; decisions unset; Maria8200/Design7200; no new award/history/mail. Does not claim full generation lifecycle. |
| `test_finalize_partial_with_accepted_add_awards_only_500` | Real staff POST redirects; PIP `accepted_partial`; one new Activity with actual submitted guidance; rejected target retains original guidance/name and other fields not intentionally affected by accepted insertion; Maria8700/Design7700/Development1000, not8800; Hana5800 and Mike12450 unchanged. Exactly one new award globally, matching complete accepted-change payload; none for rejected change; existing rows unchanged; no first-release award. Target3.0; exactly one new PIP_SOURCE/is_major receipt linked to this PIP, snapshots2.0→3.0; summary includes accepted ADD and excludes rejected ALTER sentinel. Existing success message exactly “PIP partially accepted — changes applied.” |
| `test_finalize_partial_with_outer_commit_sends_one_normal_notification` | With `django_db(transaction=True)`, invoke real finalization inside outer `transaction.atomic`; content/award exist transaction-locally and outbox remains empty inside. On actual outer commit exactly one email to Maria, partial subject/verdict, ADD/ACCEPT, ALTER/REJECT, new version3.0 and correct detail URL. No invented Karma earnings copy. |
| `test_finalize_partial_with_outer_rollback_preserves_baseline_and_sends_no_mail` | Deliberately roll back real outer transaction after finalization; no new Activity, award or receipt; target2.0; PIP remains reviewed with persisted pre-finalization fixture state; original ALTER target intact; Maria8200; outbox empty. Set initial decisions before outer block so rollback expectations are explicit. |
| `test_partial_decision_log_story_happy` | Real mixed finalization plus `caplog`/shared `assert_log_story`: entry, major500 classification, finalizer accepted1/rejected1, award created1 and postcommit partial notification. |
| `test_partial_decision_log_story_reject` | Rejected ALTER remains persisted as REJECT, receives no award and no minor100 classification. Captured finalization summary proves rejected1 alongside accepted1. No provider or domain mocks. |

S45 owns generalized retry/race/conflict certification; S34 does not duplicate it. S35 owns the full no-award lifecycle matrix.

## E — Log story


Consume S32’s declared logs and existing finalizer/notification records; add no competing logger or production path.

| Where | Beat | Trigger | Must include |
|---|---|---|---|
| `KarmaService.award_accepted_changes` | entry | Partial terminal PIP reaches S32 hook | `entry`, `pip_id=`, `correlation_id=` |
| `KarmaService._accepted_change_policy` | processing | Accepted ADD classified | accepted `change_id=`, `operation=ADD`, `entity=Activity`, `source_kind=major`, `points=500` |
| `KarmaService.award_accepted_changes` | exit | Single accepted specification persisted | `exit`, `pip_id=`, `created_count=1`, `existing_count=0` |
| `PIPAdminService.finalize_pip` | processing | Mixed decision finalized | actual `pk=`, `actor=`, `accepted=1`, `rejected=1` |
| `Sending PIP decision email` | processing | Actual postcommit callback | actual `pip_id=`, `verdict=partial` |

Existing finalizer/notification lines do not contain literal beat tokens; helper assertions match the declared required fragments. New Karma records follow S32’s beat format. Assert absence of rejected change classification/award separately; do not fabricate a rejected-row log from an accepted-only query. New award logs contain safe identifiers, not content, tokens or email addresses. No “committed” assertion occurs before outer commit.

## F — MCP


Not applicable. No MCP tool, facade registration or transport change.

## G — Agent proofs


Not applicable. Manual reviewed ORM state is a fixture for administrator decision acceptance, not proof of agent execution. No LLM is invoked. Existing legacy assessment test doubles are not copied. If real assessment becomes necessary, consume S23’s CAP-004 ScriptedLLM integration and corresponding trace proof rather than introducing a new stub; that change requires parent convergence.

## H — Mockup graduation


Not applicable. No frontend production changes or mockup graduation. Existing messages/email remain truthful. BPE-03 and BPE-05 are omitted.

## Parent convergence

Authoritative acceptance source: `docs/features/act-18-experts/karma-accrual.feature:59`; 1 expanded case(s), primary layer `at`. Dependencies: S32, S33. The full scenario includes all composed journey/UAT obligations assigned in the consolidated contract. Shared Make/catalog registration belongs only to S03.

## Canonical feature execution graph

```yaml
feature_execution_graph:
  feature_ref: KARMA-PIP-03
  nodes:
  - id: S34-N1-partial-domain-proof
    title: Prepare exact fixture and prove accepted-only atomic domain effects
    bpe: BPE-02
    depends_on: []
    footprint:
    - tests/integration/test_experts_karma_partial.py
    - tests/support/experts_data.py
    tests:
    - test_partial_fixture_with_reviewed_state_preserves_baseline
    - test_finalize_partial_with_accepted_add_awards_only_500
    - test_partial_decision_log_story_happy
    - test_partial_decision_log_story_reject
    log_story_rows:
    - KarmaService.award_accepted_changes:entry
    - KarmaService._accepted_change_policy:processing
    - KarmaService.award_accepted_changes:exit
    - PIPAdminService.finalize_pip:processing
    gate:
      command: pytest tests/integration/test_experts_karma_partial.py -k 'reviewed_state or accepted_add or
        log_story' -x
      log_story_command: pytest tests/integration/test_experts_karma_partial.py -k log_story -x
    guidance_bundle:
      activity: BPE/BPE-02-Implement_Backend.md
      rules:
      - do-skeletons-first
      - do-test-first
      - do-not-mock-in-integration-tests
      - do-assert-log-story
      - do-docstring-format
      - do-write-concise-methods
  - id: S34-N2-living-contract
    title: Bind the exact partial acceptance contract
    bpe: BPE-04
    depends_on:
    - S34-N1-partial-domain-proof
    footprint:
    - docs/features/steps/experts_karma_pip_steps.py
    gate:
      command: make test-experts-s34-at
    guidance_bundle:
      activity: BPE/BPE-04-Implement_Feature_Acceptance_Tests.md
      rules:
      - do-test-first
      - do-not-mock-in-integration-tests
      - pytest
  - id: S34-N3-postcommit-certification
    title: Prove actual commit and rollback notification boundaries
    bpe: BPE-04
    depends_on:
    - S34-N2-living-contract
    footprint:
    - tests/integration/test_experts_karma_partial.py
    tests:
    - test_finalize_partial_with_outer_commit_sends_one_normal_notification
    - test_finalize_partial_with_outer_rollback_preserves_baseline_and_sends_no_mail
    log_story_rows:
    - Sending PIP decision email:processing
    gate:
      command: pytest tests/integration/test_experts_karma_partial.py -k 'outer_commit or outer_rollback' -x
      acceptance_command: make test-experts-s34-at
      log_story_command: pytest tests/integration/test_experts_karma_partial.py -k log_story -x
    guidance_bundle:
      activity: BPE/BPE-04-Implement_Feature_Acceptance_Tests.md
      rules:
      - do-test-first
      - do-not-mock-in-integration-tests
      - do-assert-log-story
      - pytest
  - id: S34-N4-definition-of-done
    title: Conjunctively certify domain, exact AT, logs and existing regressions
    bpe: BPE-06
    depends_on:
    - S34-N3-postcommit-certification
    footprint: []
    gate:
      command: make test-experts-s34
      log_story_command: pytest tests/integration/test_experts_karma_partial.py -k log_story -x
    guidance_bundle:
      activity: BPE/BPE-06-Check_Definition_of_Done.md
      rules:
      - do-test-first
      - do-assert-log-story
      - do-not-mock-in-integration-tests
      - do-small-increments
      - do-follow-commit-convention
      - do-github-issues
      - pytest
  scenario_dependencies:
  - S32
  - S33
```

## Lessons Learned

- Existing partial-review coverage uses the opposite acceptance direction; it cannot certify the 500-versus600 award distinction.
- Cedar’s historical two-change PIP already contributes600; only a new independent proposal proves8700.
- Capturing callbacks is not evidence of actual commit timing; transaction-capable tests can prove real `on_commit` behavior without mocks.
- The existing admin message/email contains no Karma earnings amount. Preserving it avoids inventing product copy or misleading the administrator about the recipient.
- No files, tests, database state, issues or commits were changed.

## Structural application evidence

`docs/experts-replay/pin-evidence/S34.json` records positive scaffold selection and deliberate NotImplementedError. Existing callable ASTs were preserved. Browser collection is not interaction certification.

## Actual structural footprint

`docs/experts-replay/pin-evidence/S34.json`, `docs/features/steps/experts_karma_pip_steps.py`, `docs/plans/iterations/experts/S34-karma-pip-03.md`, `tests/integration/test_experts_karma_partial.py`, `tests/support/experts_data.py`

Skeleton: `f60a5ef9905b18832ecfc0d8038ac84298cac87d`; shared reconciliation: `39d598328d438d09723b6eb14574fbf92fab71c9`. Semantic and physical-file dependencies are recorded separately in the iteration manifest. Context-map line ranges record the workers’ inspection baseline; headers and the final scaffold remain authoritative.
