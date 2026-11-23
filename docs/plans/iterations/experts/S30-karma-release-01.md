# S30: KARMA-RELEASE-01 Award the first released playbook once

This plan uses [the consolidated contract](../pin-convergence-20261123-experts.md). Its shared interfaces, ownership decisions and verification-layer mapping govern this scenario. Commands in the graph below are the canonical execution gates; implementation and test bodies remain unimplemented.

```yaml
scenario: S30
acceptance_id: KARMA-RELEASE-01
feature_file_path: docs/features/act-18-experts/karma-accrual.feature
feature_line: 8
primary_execution_layer: at
expanded_case_count: 1
dependencies:
- S03
system_dependencies: []
status: skeleton_applied_unimplemented
source_report_sha256:
- c43ab571d02477c71d1c50c056bd67e32d9232e363d8c9028ecb9a6eb559bb81
```

## A — Context map


| File | Verified lines | Purpose |
|---|---:|---|
| `docs/architecture/SAO.md` | 3836–3853 | Immutable ledger, category snapshot, database deduplication, first-release eligibility and transaction ownership. |
| `methodology/services/playbook_service.py` | 488–567 | Existing atomic release operation validates owner, notes, status and workflow; saves the next major version and release history; returns `Playbook`. |
| `methodology/playbook_views.py` | 573–603 | Existing authenticated POST endpoint and Django success/error message flow. |
| `test-data/experts/cedar-rfp-01.json` | 634–655, 775–790 | Nora’s empty ledger, Product draft 6302, EV07’s 0→5,000 and Product order. |
| `tests/integration/test_playbook_release.py` | 68–121 | Existing working release/version tests, including required description and later-major release. |

Additional verified reuse:

- `templates/base.html` already renders Django messages using `data-testid="alert-message"`; its existing escaping and dismiss control suffice.
- `templates/playbooks/detail.html` already supplies `release-modal`, `release-description-input` and `release-confirm`.
- `PlaybookVersion` records source, timestamp, actor and unique `(playbook, version_number)`.
- `_playbook_release_snapshot` already constructs before/after history payloads.
- `tests/support/log_story.py:assert_log_story` is implemented.
- Existing E2E fixtures provide a real live server and browser; `tests/e2e/e2e_helpers.py:login` is implemented.
- `NotificationService` and `accounts.services.email_service.EmailService` are real implementations. This scenario needs neither: “she sees” is an ordinary success message, not new mail or bell infrastructure.
- Experts ledger, Cedar adapter and ranking behavior remain unimplemented at this baseline. S03 owns those prerequisites; their existence must be checked at S30 handoff.

### Shared prerequisite/interface contract with S03

S03 owns:

- `methodology/models/karma_award.py`, its registration and migration.
- `ExpertProfile` and any summary fields required elsewhere.
- The real historical Cedar ORM adapter in `tests/support/experts_data.py`.
- Ledger projections and `/experts/?category=product`, including production templates.
- Schema/fixture immutability tests and seed migration handling.

S30 owns live award persistence through `KarmaService`, release integration and the award message. No S30 dependency on S01 is necessary: assert Product ranking through its direct URL.

Required ledger shape, subject to the orchestrator’s shared-name reconciliation:

| Field | Required contract |
|---|---|
| `recipient_id` | Persisted user identity. |
| `source_kind` | Recognized `release`, `major`, `minor`, `consumption`, `learning`. |
| `points` | Positive integer; Boolean values are not accepted as integers. |
| `category` | Canonical category snapshot, e.g. `product`. |
| `event_identity` | Stable identity, independent of request retry. |
| `playbook_id_snapshot` | Immutable playbook identity retained for attribution/deduplication. |
| `change_id_snapshot` | Optional immutable accepted-change identity. |
| `occurred_at` | Event timestamp, not a mutable display timestamp. |

Require database uniqueness for `(event_identity, recipient)` and **first-release uniqueness for the playbook independently of recipient**. The latter prevents a later author change creating another first-release award. Snapshot identifiers must survive content deletion according to S03’s chosen immutable reference representation.

Canonical first-release identity: **`first_release:<playbook_pk>`**, including historical imported release awards. Category, version, author, request ID and release notes must not become identity components.

Historical import must:

1. Construct persisted history/ledger directly without calling live release/PIP services.
2. Map historical release rows to their actual playbook identities.
3. Preserve all Cedar totals exactly and leave Nora’s ledger empty.
4. Populate release history without triggering fresh awards.
5. Avoid manufacturing accepted changes from already aggregated historical totals twice.

The live path also guards against old released records with no ledger: pre-release status/version/history establish that publication already occurred. Missing historical points are not permission to backfill them during a later release.

## B — Do-not-do list


- Do not award on GET, draft creation, historical import or workflow creation.
- Do not add a model signal; historical fixture creation must remain inert.
- Do not award outside the successful release transaction or in `on_commit`.
- Do not introduce another version increment, snapshot mechanism or release route.
- Do not change existing owner checks, released-content permissions or the legacy `release_playbook(...) -> Playbook` contract.
- Do not use version/request identity for first-release deduplication.
- Do not silently accept an existing event with a different immutable payload.
- Do not rewrite category attribution when the playbook category changes.
- Do not generate or refresh a contribution summary for this award.
- Do not add email, broker, queue, notification service, MCP tool or ToolExecutor.
- Do not duplicate S03’s schema, adapter, ranking query or templates.
- Do not treat uncollected, skipped or raising skeleton tests as implemented behavior.

## C — Applicable SAO sections


- **Design Principles → 1. FOB-Centric Architecture**
- **Design Principles → 2. Hybrid MCP Access: Draft CRUD + Released PIP Workflow**
- **Design Principles → 4. Version Management**
- **MCP Interface (FastMCP) → Services Layer**
- **Experts & Karma delivery architecture → Awards, projections and transaction boundaries**
- **Experts & Karma delivery architecture → Web delivery and notification reuse**
- **Experts & Karma delivery architecture → Test strategy for this delta**
- **17. AI Agent Architecture → Components, pattern and serving decisions**, for the explicit boundary: the summarizer cannot award points.

### Intended behavior and transaction sequence

1. Resolve correlation ID from `X-Request-ID`, or generate one.
2. Validate release description and lock the target through the existing domain service.
3. Preserve owner/status/workflow checks.
4. Inspect the **pre-release** state: draft version below 1.0, no previous release history and no existing first-release marker establishes first publication.
5. Reuse the existing version computation and before/after snapshot machinery.
6. Create the release history and, when eligible, persist one Product `release` award worth 5,000.
7. Return an immutable release outcome after the atomic operation exits.
8. The HTTP view displays the exact award message only for a newly created award:
   **`You earned 5,000 Karma for releasing Accessible Workshop Starter`**
9. Request Product ranking afresh. It must show Alex 5,400 followed by Nora 5,000.

The existing `release_playbook` entrypoint later delegates to the outcome-based operation and returns `outcome.playbook`. Append the new skeletons now; do not replace the working entrypoint with a raising stub.

SQLite does not provide PostgreSQL-style row locks. Database uniqueness remains the award deduplication guarantee; no claim of stronger concurrency behavior should be made from `select_for_update()` alone.

## D — Tests to create


| Test | What it proves |
|---|---|
| `test_award_first_release_with_v1_release_creates_5000_category_snapshot` | Real release receipt produces one author award with canonical identity, amount, source and category. |
| `test_award_first_release_with_same_receipt_returns_existing_award` | Replaying the receipt creates no additional award. This replays the award receipt, not the release command, whose existing semantics publish another major. |
| `test_persist_awards_with_invalid_input_rejects_without_writes` | Invalid amount, source, category, identifiers and conflicting duplicate recipients fail before partial persistence. |
| `test_persist_awards_with_reused_identity_and_changed_payload_rejects` | Identity collision cannot silently rewrite attribution or amount. |
| `test_release_with_outer_transaction_rollback_removes_version_and_award` | Both writes participate in the caller’s transaction; no award escapes through `on_commit`. |
| `test_release_with_preexisting_history_and_no_ledger_does_not_backfill` | Existing released legacy content receives no retroactive first-release award. |
| `test_release_with_rejected_precondition_preserves_draft_and_empty_ledger` | Wrong owner, blank notes, missing workflow and invalid status produce no award/version. |
| `test_release_with_legacy_entrypoint_preserves_playbook_return_contract` | Existing callers continue receiving `Playbook` and existing release/version checks remain valid. |
| `test_karma_release_01_with_baseline_displays_award_and_product_ranking` | Full real-client contract: Nora 0→5,000, Product attribution, version 1.0, exact message and Alex/Nora order. |
| `test_release_with_nonfirst_outcome_omits_earned_message` | Existing release success remains visible without incorrectly claiming a new award. |
| `test_karma_release_log_story_happy` | Entry, validation, processing and exit beats share identifiers; no private content is logged. |
| `test_karma_release_log_story_reject` | Rejected release logs the reason and writes no award. |
| `test_karma_release_log_story_duplicate` | Existing event branch identifies deduplication and zero additional points. |
| `test_karma_release_01_with_browser_shows_award_and_product_order` | Actual release modal, exact visible success message and rendered Product order work through the browser. |

Reuse S03’s historical-import and immutable-ledger tests; do not implement duplicate schema tests in S30.

Behavior checkpoint, also the terminal graph gate:

```bash
pytest tests/unit/test_karma_release_service.py tests/integration/test_experts_release_acceptance.py tests/integration/test_experts_release_log_story.py tests/integration/test_playbook_release.py -x
```

Log checkpoint:

```bash
pytest tests/integration/test_experts_release_log_story.py -x
```

Browser checkpoint:

```bash
pytest tests/e2e/test_experts_release.py -x
```

Living-spec certification additionally executes the exact named scenario through the established acceptance settings/runner. Do not use a zero-selection `make test-at-experts` result to certify S30. Preserve `@wip` until the real binding is demonstrated; reconcile feature-level versus scenario-level tags across the whole iteration before enabling contracts.

## E — Log Story Script


Use INFO unless stated otherwise. Names below are stable `where` fragments. Logs contain identifiers and reasons, never title, release notes, email, prompt text or credentials.

| Where | Beat | Trigger | Must include |
|---|---|---|---|
| `PlaybookService.release_playbook_with_award` | entry | release requested | `actor_id=`, `playbook_id=`, `correlation_id=` |
| Same | validation | checks pass | `owner_valid=true`, `workflow_present=true`, `first_publication=true` |
| Same | processing | release and award staged | `version=1.0`, `award_points=5000`, `transaction=pending` |
| Same | branch | preexisting release | `reason=previously_released`, `award_points=0` |
| Same | error | validation/permission rejects | `reason=`, `playbook_id=`, `correlation_id=` |
| `KarmaService.persist_awards` | entry | eligible award batch | `award_count=1`, `correlation_id=` |
| `KarmaService.award_first_release` | config | release policy selected | `source_kind=release`, `points=5000` |
| Same | branch | duplicate event | `event_identity=first_release:6302`, `created=false`, `additional_points=0` |
| Same | exit | award staged | `recipient_id=`, `category=product`, `created=true`, `points=5000` |
| `_release_with_karma_message` | exit | successful HTTP operation | `playbook_id=6302`, `earned_message=true`, `correlation_id=` |

Tests use `assert_log_story` with `caplog` and assert all declared fragments at their declared level. Service logs describe staged writes, avoiding a false durability claim before the surrounding transaction commits.

## F — MCP tools to expose


**Not applicable.** This scenario exercises the existing web-only release action and shared domain service. It adds or modifies no MCP registration/client/facade surface. No registration proofs or second server are required.

## G — Agent proofs


**Not applicable.** No provider invocation, summary refresh, agent orchestration, tool execution or interaction trace is introduced. SAO §17 expressly excludes awards from the summarizer. PRF-EXPERTS-01/02/03 and PRF-OBS-01 remain owned by the summary scenarios.

## H — Mockup graduation


| Surface | Source | Production target | Strategy |
|---|---|---|---|
| Release confirmation/message | Existing production modal and shell message renderer | Existing `templates/playbooks/detail.html` and `templates/base.html`, unchanged | Reuse |
| Product leaderboard after release | `templates/mockups/experts/list.html` | `templates/experts/list.html`, owned by S03 | S03’s rewire |

S30 changes the message supplied to the existing production renderer. It needs no new production template or filled template skeleton. Preserve DEBUG-only mockup routes.

## Parent convergence

Authoritative acceptance source: `docs/features/act-18-experts/karma-accrual.feature:8`; 1 expanded case(s), primary layer `at`. Dependencies: S03. The full scenario includes all composed journey/UAT obligations assigned in the consolidated contract. Shared Make/catalog registration belongs only to S03.

## Canonical feature execution graph

```yaml
feature_execution_graph:
  feature_ref: KARMA-RELEASE-01
  nodes:
  - id: N1-release-award-domain
    title: Persist first-release awards within the existing release transaction
    bpe: BPE-02
    depends_on: []
    footprint:
    - methodology/services/karma_service.py
    - methodology/services/playbook_service.py
    - tests/integration/test_experts_release_log_story.py
    - tests/support/experts_release.py
    - tests/unit/test_karma_release_service.py
    tests:
    - test_award_first_release_with_v1_release_creates_5000_category_snapshot
    - test_award_first_release_with_same_receipt_returns_existing_award
    - test_persist_awards_with_invalid_input_rejects_without_writes
    - test_persist_awards_with_reused_identity_and_changed_payload_rejects
    - test_release_with_outer_transaction_rollback_removes_version_and_award
    - test_release_with_preexisting_history_and_no_ledger_does_not_backfill
    - test_release_with_rejected_precondition_preserves_draft_and_empty_ledger
    - test_release_with_legacy_entrypoint_preserves_playbook_return_contract
    - test_karma_release_log_story_happy
    - test_karma_release_log_story_reject
    - test_karma_release_log_story_duplicate
    log_story_rows:
    - PlaybookService.release_playbook_with_award:entry
    - PlaybookService.release_playbook_with_award:validation
    - PlaybookService.release_playbook_with_award:processing
    - PlaybookService.release_playbook_with_award:branch
    - PlaybookService.release_playbook_with_award:error
    - KarmaService.persist_awards:entry
    - KarmaService.award_first_release:config
    - KarmaService.award_first_release:branch
    - KarmaService.award_first_release:exit
    gate:
      command: pytest tests/unit/test_karma_release_service.py tests/integration/test_experts_release_log_story.py
        tests/integration/test_playbook_release.py -x
      log_story_command: pytest tests/integration/test_experts_release_log_story.py -x
    guidance_bundle:
      activity: BPE/BPE-02-Implement_Backend.md
      rules:
      - do-skeletons-first
      - do-test-first
      - do-not-mock-in-integration-tests
      - do-informative-logging
      - do-assert-log-story
      - do-write-concise-methods
      - do-docstring-format
  - id: N2-release-message
    title: Display the newly created award through existing Django messages
    bpe: BPE-03
    depends_on:
    - N1-release-award-domain
    footprint:
    - methodology/playbook_views.py
    - tests/integration/test_experts_release_acceptance.py
    - tests/integration/test_experts_release_log_story.py
    production_template: templates/base.html
    graduate_strategy: partial
    tests:
    - test_karma_release_01_with_baseline_displays_award_and_product_ranking
    - test_release_with_nonfirst_outcome_omits_earned_message
    - test_karma_release_log_story_happy
    log_story_rows:
    - _release_with_karma_message:exit
    gate:
      command: pytest tests/integration/test_experts_release_acceptance.py tests/integration/test_playbook_release.py
        -x
      log_story_command: pytest tests/integration/test_experts_release_log_story.py -x
    guidance_bundle:
      activity: BPE/BPE-03-Implement_Frontend.md
      rules:
      - do-test-first
      - do-assert-log-story
      - do-semantic-versioning-on-ui-elements
  - id: N3-release-acceptance
    title: Bind the independent Cedar first-release contract
    bpe: BPE-04
    depends_on:
    - N2-release-message
    footprint:
    - docs/features/steps/experts_karma_release_steps.py
    - tests/integration/test_experts_release_acceptance.py
    tests:
    - test_karma_release_01_with_baseline_displays_award_and_product_ranking
    gate:
      command: make test-experts-s30-at
    guidance_bundle:
      activity: BPE/BPE-04-Implement_Feature_Acceptance_Tests.md
      rules:
      - do-test-first
      - do-not-mock-in-integration-tests
  - id: N4-release-browser
    title: Certify the actual release message and refreshed Product ranking
    bpe: BPE-05
    depends_on:
    - N3-release-acceptance
    footprint:
    - tests/e2e/test_experts_release.py
    tests:
    - test_karma_release_01_with_browser_shows_award_and_product_order
    gate:
      command: make test-experts-s30-browser
    guidance_bundle:
      activity: BPE/BPE-05-Implement_Journey_Certification_Tests.md
      rules:
      - do-test-first
      - do-semantic-versioning-on-ui-elements
  - id: N5-release-dod
    title: Verify the complete release award contract and regression boundary
    bpe: BPE-06
    depends_on:
    - N4-release-browser
    footprint:
    - tests/integration/test_experts_release_acceptance.py
    - tests/integration/test_experts_release_log_story.py
    - tests/unit/test_karma_release_service.py
    log_story_rows:
    - PlaybookService.release_playbook_with_award:entry
    - KarmaService.award_first_release:exit
    - _release_with_karma_message:exit
    gate:
      command: make test-experts-s30
      log_story_command: pytest tests/integration/test_experts_release_log_story.py -x
    guidance_bundle:
      activity: BPE/BPE-06-Check_Definition_of_Done.md
      rules:
      - do-test-first
      - do-assert-log-story
      - do-not-mock-in-integration-tests
  scenario_dependencies:
  - S03
```

## Lessons Learned

- Existing release behavior deliberately publishes the next major even for an already released playbook. Replaying the release command and retrying an award write are different operations; tests must distinguish them.
- A generic release success message already has a production renderer. Adding a new notification mechanism would duplicate working UI infrastructure.
- Ledger uniqueness per recipient is insufficient for a once-per-playbook release award after ownership changes; the shared schema needs the additional invariant.
- Existing released seed data may have no award ledger. Eligibility must inspect historical publication state rather than treating ledger absence as proof of a first release.
- The current feature-level `@wip` tag prevents scenario-by-scenario inclusion through the standard filtered target. The orchestrator should reconcile tags and record a named living-spec execution before claiming acceptance.
- Planning checks were read-only. No files were written, no checkpoints executed, no test passes claimed, and no implementation or external action performed.

## Structural application evidence

`docs/experts-replay/pin-evidence/S30.json` records positive scaffold selection and deliberate NotImplementedError. Existing callable ASTs were preserved. Browser collection is not interaction certification.
