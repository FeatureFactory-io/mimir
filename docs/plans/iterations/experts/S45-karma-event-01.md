# S45: KARMA-EVENT-01 Do not double-apply an event on write retry

This plan uses [the consolidated contract](../pin-convergence-20261123-experts.md). Its shared interfaces, ownership decisions and verification-layer mapping govern this scenario. Commands in the graph below are the canonical execution gates; implementation and test bodies remain unimplemented.

```yaml
scenario: S45
acceptance_id: KARMA-EVENT-01
feature_file_path: docs/features/act-18-experts/karma-accrual.feature
feature_line: 130
primary_execution_layer: at
expanded_case_count: 1
dependencies:
- S30
- S36
system_dependencies: []
status: converged_plan_unapplied
source_report_sha256:
- e9d1054470f8ddacf4942b39247d62080b22cf0553ddb86c40b813f10f728001
```

## A — Context map


Paths are relative to `/Users/denispetelin/GitHub/mimir-experts-replay`.

| Reference | Verified behavior or governing contract |
|---|---|
| `docs/architecture/SAO.md:3836-3879` | Immutable attribution, paired atomic writes, explicit channels, original timestamps, first-release uniqueness, shared domain ownership. |
| `methodology/services/playbook_service.py:488-567` | Existing release transaction increments the version, records `PlaybookVersion`, returns `Playbook`; retrying award recording must not repeat publication. |
| `methodology/services/pip_admin_service.py:24-114` | Existing finalization locks proposal, applies accepted changes, bumps once, records terminal state, and schedules email after commit. |
| `static/js/copy_prompt.js:79-98` | Existing clipboard-success branch; S36 owns action UUID allocation and receipt retry integration. |
| `mcp_integration/facade/server.py:68-100` | Existing registered detail and export tools; S39/S42 own successful-operation receipt wiring and actual transport proofs. |

Additional inspected sources: exact Karma feature, Orient roster, current parent guidance/ownership notes, `CLAUDE.md`, Act18 journey/IA, `pip_service.py`, `pip_apply_service.py`, `PipChange`, actual MCP legacy/detail wrappers, test settings/lifecycles, Makefile, log-story helper, graph schema and BPE-02/04/06 guidance.

Current baseline has no implemented `karma_service.py` or `karma_award.py`. The delivered S03/S30/S32/S36 reports describe future interfaces; their presence must be verified at implementation handoff.

### Parent convergence contract

The parent accepted these changes to the shared designs:

1. **S03 schema:** add nullable immutable `entity_type_snapshot` and `entity_id_snapshot`; historical entries may lack them. Keep integer playbook/change snapshots and recipient CASCADE.
2. **S03 uniqueness:** keep `(event_identity, recipient)` and independent first-release uniqueness per playbook snapshot. Add a conditional unique **live anchor** on `event_identity` for `source_kind ∈ {release, major, minor, learning}` and `event_channel != historical`.
3. **S30 persistence:** its existing `persist_awards` remains the sole writer. Add whole-event preflight and race reconciliation, never a second award service.
4. **S36 identity:** replace its proposed entity-inclusive identity with `consumption:<channel>:<authenticated_actor_pk>:<action_uuid>`. Entity kind/ID belong in immutable payload snapshots.
5. **S32 identity:** retain `accepted_change:<actual_change_pk>`, channel `accepted_change`, original decision timestamp. Retry award recording, not `finalize_pip` itself.

Every validated live event has exactly one anchor: release/major/minor singleton, or learning anchor plus consumption author row. Therefore changed recipients cannot evade a concurrent identity collision.

The live-anchor condition intentionally excludes historical activity. First-release uniqueness still covers historical release rows. Whole-event lookup never filters out historical rows: replaying `first_release:<pk>` must discover the imported singleton.

## B — Do-not-do list


- Do not include entity kind, entity ID, author, category or timestamp in consumption identity.
- Do not accept caller-owned recipient, points, source, category or timestamp through receipts.
- Do not treat uniqueness per recipient as proof of whole-event equality.
- Do not “repair” a partial pair by filling its missing row; reject inconsistent persisted events.
- Do not regenerate an event timestamp on successful replay, rewrite historical attribution or compare fresh request time with stored event time.
- Do not replay publication, accepted mutations, version increments or decision email to test award-write retries.
- Do not retry database busy errors inside a broken transaction/savepoint.
- Do not swallow unrelated constraint, connection or programming errors.
- Do not rely on `select_for_update` as a SQLite serialization mechanism.
- Do not add an event table, queue, database engine, tool registry, executor or award writer.
- Do not widen permissions or use Karma as read authorization.
- Do not replace existing working methods with raising stubs during PIN.
- Do not claim PostgreSQL race verification from SQLite tests or claim skipped/empty gates as completion.

## C — Architecture, algorithm and boundaries


Applicable SAO headings: **Awards, projections and transaction boundaries**, **Services Layer**, **Hybrid MCP Access**, **Guest read security**, **Request ID Logging**, **Test strategy for this delta**. SAO §17 adds no requirement here: this scenario neither invokes nor modifies an agent capability.

### Logical payload

Compare the **complete unordered recipient set and each recipient’s immutable payload**:

```text
recipient_id, source_kind, points, category, event_channel,
playbook_id_snapshot, change_id_snapshot,
entity_type_snapshot, entity_id_snapshot
```

All rows must share event identity and original aware occurrence time. Pair rows must be exactly one learning and one consumption award, distinct recipients, five points each, matching target/category/channel/time. Singleton shapes are exactly release, major or minor with their recognized channels and validated amounts.

`occurred_at` is validated but excluded from the logical retry comparison. If an existing event matches, return existing rows and their stored original time; perform no update.

A changed entity, playbook, accepted-change ID, recipient, author, category, points, source, channel or pair shape conflicts. Duplicate recipient inputs and inconsistent times within one proposed pair fail before writes.

Trusted accepted-change replay may reconstruct the original persisted decision snapshot through S32’s `_recorded_accepted_change_spec`. That is distinct from accepting an altered specification: a directly supplied changed category/recipient conflicts. Reconstructing a stored receipt must still verify the fixed accepted-change and playbook identity.

For consumption, authorization and current entity resolution remain S36-owned. Reusing its UUID after target author/category reassignment is a conflict, rather than an additional award or silent replacement.

### Transaction and race protocol

Pseudocode for the converged **existing S30 writer**:

```text
validate complete batch and partition by event identity
remember whether caller already owns a transaction
attempt:
    begin atomic batch
    preflight every existing event as a whole, before inserting anything
    for each missing event in deterministic identity order:
        within nested atomic savepoint, insert using existing row writer
        if another writer won:
            leave failed savepoint first
            reload entire event, then compare complete logical payload
    return created/existing outcomes, in original specification order
on recognized SQLite busy/locked:
    if caller owns transaction: propagate; owning boundary must roll back
    otherwise retry whole batch only after rollback, with bounded attempts
on unrelated database failure:
    propagate
```

If the existing per-row helper returns an existing row during insertion, abort that insertion savepoint using an internal race signal, then reconcile the entire event. Never append the remaining recipient to an event that another transaction already owns.

PostgreSQL: the unique anchor arbitrates concurrent first inserts, including changed-recipient singleton races. Catch recognized unique violations outside the failed savepoint, inspect constraint diagnostics, reread the winner under the configured default READ COMMITTED isolation and compare. Do not promise compatibility with arbitrary isolation settings.

SQLite: real uniqueness still arbitrates committed identity ownership, but concurrent read-to-write upgrades may raise `SQLITE_BUSY`, `SQLITE_LOCKED` or their extended forms. Retry only those recognized transient categories after the entire owned transaction has rolled back. Bound attempts with a named constant; never retry unrelated `OperationalError`.

A caller-owned release/PIP transaction receives the transient failure and rolls back all domain/ledger writes. A receipt boundary may return a safe retryable response; its existing client retries the same UUID. Neither path reports a successful award before persistence succeeds.

## D — Tests to create


All tests use real Cedar ORM data, real transactions and current services. `transaction=True` is mandatory for race/rollback cases. No patched service, fake ledger or mocked database.

Proposed suite: `tests/integration/karma_event/test_retry.py`.

| Test | Required assertions |
|---|---|
| `test_record_event_with_repeated_write_preserves_original_event` | Parameterize accepted major/minor and three consumption channels. First call creates exactly one singleton or pair; repeat preserves PKs, full row payload, exact time, category totals and total ledger count. Accepted case invokes real finalization once, then retries only recorded award receipt. |
| `test_consumption_with_new_uuid_creates_new_complete_pair` | Same actor/entity/channel with UUID A and B yields four rows, distinct identities, exactly +10 per recipient; retry each produces no extra row. |
| `test_persist_awards_with_changed_payload_rejects_entire_batch` | Parameterize every logical field, recipient substitution/removal/addition, same UUID different entity kind or ID, author/category reassignment, incomplete/reversed-source pair, duplicate recipients and mismatched pair times. Real conflicting call raises safe validation error; existing rows remain byte-for-byte equivalent in projected field values. Fresh request time alone is accepted replay. |
| `test_event_with_outer_rollback_preserves_atomicity` | Real outer `atomic` executes successful pair or accepted recording, then raises; award rows vanish. Accepted case additionally rolls back mutation/version/decision and emits no committed decision email. Existing unrelated Cedar rows stay unchanged. |
| `test_event_with_partial_existing_pair_rejects_without_repair` | Construct an intentionally inconsistent real ledger event directly; recording rejects missing author/extra recipient or mismatched stored times without adding/updating rows. |
| `test_event_with_concurrent_writers_preserves_one_complete_event` | Real separate thread connections and bounded synchronization. Parameterize identical replay, changed consumption target, changed author recipient, and accepted singleton changed recipient. Exactly one whole event commits; identical loser returns existing, altered loser conflicts after any permitted busy retry. Never 1/3 rows for a pair or two accepted singleton recipients. |
| `test_event_with_database_constraints_rejects_changed_recipient` | Direct real ORM inserts bypass service: anchor rejects same live identity with another recipient; first-release constraint rejects another identity/author for same playbook; account deletion semantics remain CASCADE. Use savepoints so assertion queries remain valid. |
| `test_first_release_with_historical_marker_preserves_singleton` | Imported canonical historical first-release prevents a second award; author replacement cannot create another first-release singleton. Same original receipt does not cause publication/version changes. |
| `test_copy_receipt_with_retry_and_changed_target_enforces_identity` | Real authenticated CSRF-valid Django requests: original+retry yield pair; same UUID another authorized target conflicts; new UUID succeeds; no client-controlled attribution fields are accepted. |
| `test_karma_event_log_story_happy` | Entry → validated whole event → created/replayed branch → exit; duplicate has created_count=0 and original timestamp retained. Use `assert_log_story`. |
| `test_karma_event_log_story_reject` | Payload conflict, partial event and transient contention have distinct safe reasons; no success for rejected attempt, no raw private content/token/email/prompt in captured records. |

Existing S30 release, S32 PIP and S36 copy tests remain required regression gates.

### Feasible real concurrency fixture

Use nested `tests/integration/karma_event/conftest.py` to override the documented pytest-django `django_db_modify_db_settings` fixture **before test DB creation**. On SQLite only, set `DATABASES["default"]["TEST"]["NAME"]` to a unique temporary file. Preserve ENGINE and timeout. File-backed SQLite avoids shared-memory-specific table-lock behavior obscuring the deployed engine’s locking semantics.

Each worker calls `close_old_connections()`, loads its own actor/target instances, opens its own connection, then executes the actual service. Record underlying connection identities and assert they differ. Coordinate starts with `threading.Barrier`; propagate every future exception and enforce finite timeouts. Close connections in `finally`.

For deterministic “winner uncommitted” coverage, worker A records through the actual writer inside its own outer transaction and signals completion before commit. Worker B starts its real recording while A remains uncommitted. Release A’s commit using a bounded event. SQLite B can receive a legitimate transient lock error; its next call occurs only after rollback and reuses the same specs/UUID. PostgreSQL B waits on the unique anchor and reconciles afterward. SQL observation through Django’s real execution wrapper may record that B attempted its query; it must always delegate SQL and cannot fabricate query results.

The test must assert outcomes and persistent whole-event invariants after both workers finish. “Two futures ran” alone is insufficient.

Run this suite against local SQLite and the existing PostgreSQL CI database. Record vendor and executed cases in evidence. PostgreSQL absence is an explicit unverified lane, not a passing skip.

## E — Log story


| Where | Beat | Trigger | Must include |
|---|---|---|---|
| `KarmaService.persist_awards` | entry | Batch received | correlation ID, event count, row count |
| `KarmaService._assert_matching_event` | validation | Existing event compared | event identity, recipient count, `payload_match=true` |
| `KarmaService._persist_event_atomic` | processing | Complete new event staged | identity, channel, recipients, `created_count`, `commit_state=staged` |
| `KarmaService._persist_event_atomic` | branch | Identical replay/race | `reason=replayed`, created_count=0 |
| `KarmaService._assert_matching_event` | branch | Immutable mismatch/partial event | safe reason `event_payload_conflict` or `event_shape_conflict`, identity |
| `KarmaService.persist_awards` | branch | Recognized SQLite contention | vendor, attempt, transaction owner, `reason=database_busy` |
| `KarmaService.persist_awards` | exit | Entire batch returned | created_count, existing_count, correlation ID |
| `KarmaService.persist_awards` | error | Unrecoverable/exhausted failure | safe reason, vendor, rollback ownership; no award-success claim |

Staged logs are not commit proof. Real rollback assertions provide that proof. No contents, cookies, CSRF, mail addresses or tokens in logs.

## F — MCP surface


No new tool or registration change in S45. S39/S42 own facade/legacy UUID receipt wiring, shared `_post_consumption_receipt`, T1/T2/T3 proofs and export completion.

S45 exercises their common service persistence contract; channel parameterization does not substitute for registered MCP client tests. Their existing proofs must show retained UUID across receipt transport retries.

## G — Agent proofs


Not applicable. No LLM call, PRF row, factory or agent loop is introduced or changed.

## H — Mockup graduation and UI


Not applicable: this is a persistence and receipt replay contract. S36 owns actual clipboard UI behavior and browser certification. S45 uses real Django-client receipt requests; it does not simulate a clipboard click or claim new UI evidence. Omit BPE-03/05 nodes because no additional UI behavior is introduced.

## Parent convergence

Authoritative acceptance source: `docs/features/act-18-experts/karma-accrual.feature:130`; 1 expanded case(s), primary layer `at`. Dependencies: S30, S36. The full scenario includes all composed journey/UAT obligations assigned in the consolidated contract. Shared Make/catalog registration belongs only to S03.

## Canonical feature execution graph

```yaml
feature_execution_graph:
  feature_ref: KARMA-EVENT-01
  nodes:
  - id: S45-N1-event-validation
    title: Validate and compare complete immutable events
    bpe: BPE-02
    depends_on: []
    footprint:
    - methodology/services/karma_service.py
    - tests/integration/karma_event/conftest.py
    - tests/integration/karma_event/test_retry.py
    tests:
    - test_record_event_with_repeated_write_preserves_original_event
    - test_persist_awards_with_changed_payload_rejects_entire_batch
    - test_event_with_partial_existing_pair_rejects_without_repair
    - test_karma_event_log_story_happy
    - test_karma_event_log_story_reject
    log_story_rows:
    - KarmaService.persist_awards:entry
    - KarmaService._assert_matching_event:validation
    - KarmaService._assert_matching_event:branch
    - KarmaService.persist_awards:exit
    gate:
      command: pytest tests/integration/karma_event/test_retry.py -k 'repeated_write or changed_payload or partial_existing
        or log_story' -x
      log_story_command: pytest tests/integration/karma_event/test_retry.py -k log_story -x
    guidance_bundle:
      activity: BPE/BPE-02-Implement_Backend.md
      rules:
      - do-skeletons-first
      - do-test-first
      - do-not-mock-in-integration-tests
      - do-assert-log-story
      - do-write-concise-methods
      - do-docstring-format
  - id: S45-N2-atomic-races
    title: Prove unique anchors and real concurrent transaction behavior
    bpe: BPE-02
    depends_on:
    - S45-N1-event-validation
    footprint:
    - methodology/services/karma_service.py
    - tests/integration/karma_event/conftest.py
    - tests/integration/karma_event/test_retry.py
    tests:
    - test_event_with_outer_rollback_preserves_atomicity
    - test_event_with_concurrent_writers_preserves_one_complete_event
    - test_event_with_database_constraints_rejects_changed_recipient
    - test_first_release_with_historical_marker_preserves_singleton
    - test_karma_event_log_story_happy
    - test_karma_event_log_story_reject
    log_story_rows:
    - KarmaService._persist_event_atomic:processing
    - KarmaService._persist_event_atomic:branch
    - KarmaService.persist_awards:branch
    - KarmaService.persist_awards:error
    gate:
      command: pytest tests/integration/karma_event/test_retry.py -k 'outer_rollback or concurrent_writers or database_constraints
        or historical_marker or log_story' -x
      log_story_command: pytest tests/integration/karma_event/test_retry.py -k log_story -x
    guidance_bundle:
      activity: BPE/BPE-02-Implement_Backend.md
      rules:
      - do-test-first
      - do-not-mock-in-integration-tests
      - do-assert-log-story
      - do-informative-logging
      - pytest
  - id: S45-N3-acceptance
    title: Bind exact retry contract and real receipt boundary
    bpe: BPE-04
    depends_on:
    - S45-N2-atomic-races
    footprint:
    - docs/features/steps/karma_event_steps.py
    - tests/integration/karma_event/test_retry.py
    tests:
    - test_consumption_with_new_uuid_creates_new_complete_pair
    - test_copy_receipt_with_retry_and_changed_target_enforces_identity
    gate:
      command: make test-experts-s45-at
    acceptance_command: DJANGO_SETTINGS_MODULE=mimir.settings.acceptance .venv/bin/python manage.py behave --simple
      --tags=@experts --name='KARMA-EVENT-01' docs/features/act-18-experts/karma-accrual.feature
    required_acceptance_scenarios: 1
    guidance_bundle:
      activity: BPE/BPE-04-Implement_Feature_Acceptance_Tests.md
      rules:
      - do-test-first
      - do-not-mock-in-integration-tests
      - pytest
  - id: S45-N4-definition-of-done
    title: Verify complete retry contract and record backend evidence
    bpe: BPE-06
    depends_on:
    - S45-N3-acceptance
    footprint:
    - docs/architecture/SAO.md
    gate:
      command: make test-experts-s45
      log_story_command: pytest tests/integration/karma_event/test_retry.py -k log_story -x
    additional_required_gates:
    - make test-at-harness
    - make test-at-experts
    - make lint
    guidance_bundle:
      activity: BPE/BPE-06-Check_Definition_of_Done.md
      rules:
      - do-test-first
      - do-assert-log-story
      - do-small-increments
      - do-github-issues
      - do-follow-commit-convention
  scenario_dependencies:
  - S30
  - S36
```

## Lessons Learned

1. Entity-inclusive retry keys silently convert conflicting receipts into new awards. Target snapshots and action identity must be separate.
2. Per-recipient uniqueness cannot prevent another recipient winning a concurrent singleton event; a unique logical anchor closes that gap without introducing another table.
3. PostgreSQL savepoint recovery and SQLite lock recovery occur at different transaction boundaries. An inner savepoint cannot rescue an outer transaction’s stale SQLite snapshot.
4. Retrying award recording differs from retrying a release or PIP finalization command. The latter can repeat version transitions or legitimately reject terminal state.
5. Imported historical first-release rows must participate in live replay lookup even though their channel is historical.
6. The accepted unique-anchor design and entity snapshots need a concise SAO addition and S03 convergence before implementation, rather than a late migration owned by S45.

No files, tests, database state, issues or commits were changed.
