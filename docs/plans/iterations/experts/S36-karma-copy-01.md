# S36: KARMA-COPY-01 Credit a successful authenticated copy to both parties

This plan uses [the consolidated contract](../pin-convergence-20261123-experts.md). Its shared interfaces, ownership decisions and verification-layer mapping govern this scenario. Commands in the graph below are the canonical execution gates; implementation and test bodies remain unimplemented.

```yaml
scenario: S36
acceptance_id: KARMA-COPY-01
feature_file_path: tests/e2e/experts-interactions.feature
feature_line: 37
primary_execution_layer: e2e
expanded_case_count: 1
dependencies:
- S03
- S30
system_dependencies: []
status: converged_plan_unapplied
source_report_sha256:
- 2334fe9d42fd2e2d4e7312bd6a4ce7575a15fa7ca402f28a3eb44457d0a18493
```

## A — Context map


All paths are relative to `/Users/denispetelin/GitHub/mimir-experts-replay`.

| Verified reference | Relevance |
|---|---|
| `static/js/copy_prompt.js:79-98` | Real delegated click handler; clipboard success currently only shows a toast/checkmark. This promise-success branch is the receipt integration point. |
| `methodology/services/activity_service.py:937-974` | `get_activity_for_user` resolves the activity and delegates read authorization to `PlaybookService.get_playbook`. |
| `templates/partials/copy_prompt/button.html:1-18` | Shared detail/embed button has stable selectors and hidden actual prompt, but lacks explicit entity metadata. |
| `tests/integration/test_copy_prompt.py:43-120` | Existing real Django-client tests cover detail, list, embed and guest rendering; preserve them. |
| `test-data/experts/cedar-rfp-01.json:686-703` | EV01 specifies Maria 8200→8205, Mike 12450→12455, Development, activity 6203. |

Additional inspected sources include actual list/detail templates, `CopyPromptService`, `mimir/urls.py`, API viewsets, `Playbook.can_view`, `PIPService.get_pip`, E2E fixtures, AT lifecycle, IA §11 and the feature graph schema.

**Required behavior:** Maria copies the server-built prompt of activity 6203. Only after `navigator.clipboard.writeText` resolves does JavaScript report that completed action. The server authenticates Maria from her session, reloads and authorizes the referenced entity, derives Mike and Development, and atomically persists one five-point learner award and one five-point author award.

The server validates a reported successful action and entity authorization. It cannot independently inspect the browser clipboard.

## B — Do-not-do list


- Do not award on GET/render, prompt construction, click initiation, rejected clipboard promises or unavailable clipboard APIs.
- Do not accept actor, author, category, points, source kind or occurrence time from the browser.
- Do not introduce a second clipboard implementation or change existing prompt text.
- Do not make award delivery failure turn a completed clipboard write into a clipboard failure.
- Do not create accounts or awards for guests; do not award self-consumption.
- Do not weaken existing private/team/group/PIP access checks. PIP reads remain creator-or-staff through `PIPService.get_pip`.
- Do not add MCP business logic to the facade. S39/S42 reuse this service after their own successful operation.
- Do not duplicate S03 schema/Cedar/projection work or S30 persistence/release ownership.
- Do not add protective playbook/change foreign keys, migrations, seed mutations, queues, LLM calls or version increments in S36.
- Do not replace working bodies with raising placeholders during PIN. Append uncalled helpers and inert template comments only.
- Do not treat a Django-client receipt test as proof that a browser clipboard changed.

## C — Applicable architecture and contracts


- SAO **Experts & Karma delivery architecture — Awards, projections and transaction boundaries**, particularly `3836-3875`.
- SAO **Web delivery and notification reuse** and **Test strategy for this delta**, `3883-3914`.
- SAO **Services Layer**, **Guest read security**, **Request ID Logging**, **E2E Testing with Playwright**.
- IA **6.2 Toast Notifications**, **9 Accessibility**, **11 Experts replay recipe and responsive coverage contract**.
- Act 18 `KARMA-COPY-01`; neighboring exclusions `KARMA-COPY-02/03`, `KARMA-EVENT-01/02`.
- S03 supplies immutable ledger snapshots and recognized source kinds. S30 supplies:
  `persist_awards(tuple[AwardSpec, ...], ...) -> tuple[AwardOutcome, ...]`.

Shared consumption contract proposed here:

```text
KarmaService.award_successful_consumption(
    actor,
    entity_type,
    entity_id,
    event_identity: UUID,
    *,
    channel: Literal["gui_copy", "mcp_detail", "export"],
) -> tuple[AwardOutcome, ...]
```

The channel is selected by trusted server callers. GUI JSON contains only `entity_type`, `entity_id`, `event_identity`; unknown fields are rejected.

Canonical stored identity is scoped to channel, authenticated actor, entity kind/id and action UUID. A write retry retains the same UUID and scope. A later deliberate copy creates a fresh UUID. S30 uniqueness and atomic persistence arbitrate retries; do not read/check/write outside their transaction.

The target resolver supports existing playbook-backed detail entities using their real authorized service methods. Activity uses `workflow.playbook`; other ordinary entities use their existing playbook relationship. PIP resolution uses `PIPService.get_pip` and retains its creator ID for self-consumption exclusion. S39/S42 select only contract-eligible operations.

## D — Tests and implementation slices


All tests use real database objects and S03’s `load_cedar_baseline()`. No integration service mocks.

| Test | Assertion |
|---|---|
| `test_award_successful_consumption_with_other_author_creates_atomic_pair` | Maria/Mike gain five each, correct source kinds, Development and integer playbook snapshot 6201. |
| `test_copy_receipt_with_authenticated_authorized_activity_credits_both` | Real authenticated CSRF-valid POST reaches service and returns an award receipt. |
| `test_copy_receipt_with_render_only_creates_no_awards` | Detail/list/embed GETs preserve baseline ledger counts. |
| `test_copy_receipt_with_forbidden_fields_rejects_request` | Actor/author/category/points/source overrides and malformed UUID/entity fields produce no awards. |
| `test_copy_receipt_with_unauthorized_entity_creates_no_awards` | An inaccessible entity is rejected through existing access checks. |
| `test_copy_receipt_with_missing_csrf_rejects_request` | `Client(enforce_csrf_checks=True)` rejects a session POST without CSRF. |
| `test_copy_receipt_log_story_happy` | Entry→validation→pair persistence→exit with event, actor/entity IDs and result. |
| `test_copy_receipt_log_story_reject` | Validation/access rejection branch, unchanged ledger, no sensitive content in logs. |
| `test_copy_prompt_with_maria_copies_actual_prompt_and_credits_pair` | Real Chromium clipboard receives the full actual activity prompt; live receipt completes; ledger proves 8205/12455. |
| `test_copy_prompt_with_list_and_embed_surfaces_reports_same_entity` | Existing row and embed selectors identify activity 6203 and perform real clipboard writes. |

Browser tests use the verified `page`, `context`, `live_server_url`, existing `login` helper and S03 `CEDAR_PASSWORD`. Grant real clipboard read/write permissions for the live-server origin. Read `navigator.clipboard.readText()` after the actual click. Compute the expected text from `CopyPromptService.build_activity_prompt` on the real fixture before entering Playwright’s asynchronous context; do not stub `navigator.clipboard`.

S37/S38 add guest/self browser certification. S45 certifies retry/independent-event behavior; S46 certifies failed clipboard/export paths and adverse atomicity. Their later ownership does not permit S36 to implement an unsafe happy-only service.

AT bindings use real GET/receipt POST boundaries. The Gherkin clipboard clause checks the server-built expected prompt in this lane; actual clipboard satisfaction is independently required by the browser gate.

**Slices after PIN-04/05 GO:**

1. Shared service helpers and real receipt endpoint, behavior/log tests together.
2. Existing clipboard-success branch and explicit template metadata, rendering tests.
3. Living-spec bindings and real-browser certification.
4. Definition of Done and evidence review.

Each implementation slice uses `Refs #N` and its issue update; final slice uses `Closes #N`. Issue handoff and initial docs commit precede behavior implementation. This worker neither creates nor updates issues.

## E — Log story


| Where | Beat | Trigger | Must include |
|---|---|---|---|
| `copy_success_receipt` | entry | Authenticated POST | request ID, actor ID, operation `gui_copy` |
| `copy_success_receipt` | validation | Valid allowlisted payload | entity kind/id, UUID, `validated` |
| `KarmaService.award_successful_consumption` | validation | Authorized target | actor ID, playbook snapshot, channel |
| `KarmaService.award_successful_consumption` | processing | Persist pair | event identity, recipient IDs, points=5, outcome status |
| `copy_success_receipt` | exit | Completed receipt | event identity, applied/replayed/skipped outcome |
| `copy_success_receipt` | branch | Malformed, unauthenticated or denied request | safe reason code, request ID, no award |
| `KarmaService.award_successful_consumption` | branch | Guest/self exclusion | safe exclusion reason, channel, no award |

Use `caplog` and `tests/support/log_story.py::assert_log_story`. Never log clipboard text, request bodies, email addresses, cookies or CSRF tokens.

## F — MCP tools


No MCP registration or API viewset changes in S36. Shared domain helpers are consumed later by S39/S42, which own their actual facade/client/registration proofs. The GUI endpoint is an ordinary Django session endpoint, not an MCP tool.

## G — Agent proofs


Not applicable. This slice adds no LLM capability, agent workflow, tool executor or PRF row. Do not add ScriptedLLM or new agent infrastructure.

## H — Mockup graduation


Strategy: **partial**. Preserve the existing Act 17 Copy Prompt production components and toast behavior. Use `templates/mockups/copy-prompt/activity_detail.html` only as the visual reference. Add explicit receipt metadata and CSRF context to production shared buttons; wire JavaScript after actual clipboard success. No new Experts page or award toast is specified by this scenario.

The clipboard success toast remains independent of receipt delivery. Retry receipt failures with the same action ID and payload, with bounded retries. Do not repeat the clipboard write during a receipt retry. A new click has a new action UUID.

## Parent convergence

Authoritative acceptance source: `tests/e2e/experts-interactions.feature:37`; 1 expanded case(s), primary layer `e2e`. Dependencies: S03, S30. The full scenario includes all composed journey/UAT obligations assigned in the consolidated contract. Shared Make/catalog registration belongs only to S03.
This entire acceptance contract is browser-certified. Server checks are complementary initial-HTML/receipt contracts; no clipboard/hover/expansion Behave substitution is allowed.

## Canonical feature execution graph

```yaml
feature_execution_graph:
  feature_ref: KARMA-COPY-01
  nodes:
  - id: N1-consumption-receipt
    title: Shared consumption service and authenticated receipt
    bpe: BPE-02
    depends_on: []
    footprint:
    - methodology/karma_views.py
    - methodology/services/karma_service.py
    - mimir/urls.py
    - tests/integration/test_karma_copy.py
    tests:
    - test_award_successful_consumption_with_other_author_creates_atomic_pair
    - test_copy_receipt_with_authenticated_authorized_activity_credits_both
    - test_copy_receipt_with_render_only_creates_no_awards
    - test_copy_receipt_with_forbidden_fields_rejects_request
    - test_copy_receipt_with_unauthorized_entity_creates_no_awards
    - test_copy_receipt_with_missing_csrf_rejects_request
    - test_copy_receipt_log_story_happy
    - test_copy_receipt_log_story_reject
    log_story_rows:
    - copy_success_receipt:entry
    - copy_success_receipt:validation
    - KarmaService.award_successful_consumption:validation
    - KarmaService.award_successful_consumption:processing
    - copy_success_receipt:exit
    - copy_success_receipt:branch
    - KarmaService.award_successful_consumption:branch
    gate:
      command: pytest tests/integration/test_karma_copy.py -x
      log_story_command: pytest tests/integration/test_karma_copy.py -k log_story -x
    guidance_bundle:
      activity: BPE/BPE-02-Implement_Backend.md
      rules:
      - do-skeletons-first
      - do-test-first
      - do-not-mock-in-integration-tests
      - do-assert-log-story
      - do-write-concise-methods
  - id: N2-clipboard-integration
    title: Report only actual clipboard success
    bpe: BPE-03
    depends_on:
    - N1-consumption-receipt
    footprint:
    - static/js/copy_prompt.js
    - templates/activities/_embed.html
    - templates/activities/detail.html
    - templates/agents/detail.html
    - templates/artifacts/detail.html
    - templates/partials/copy_prompt/button.html
    - templates/partials/copy_prompt/row_button.html
    - templates/pips/detail.html
    - templates/rules/detail.html
    - templates/skills/detail.html
    mockup_source: templates/mockups/copy-prompt/activity_detail.html
    production_template: templates/partials/copy_prompt/button.html
    graduate_strategy: partial
    tests:
    - tests/integration/test_copy_prompt.py
    - tests/integration/test_karma_copy.py
    gate:
      command: pytest tests/integration/test_copy_prompt.py tests/integration/test_karma_copy.py -x
    guidance_bundle:
      activity: BPE/BPE-03-Implement_Frontend.md
      rules:
      - do-test-first
      - do-semantic-versioning-on-ui-elements
  - id: N3-copy-acceptance
    title: Real Django-client acceptance boundary
    bpe: BPE-04
    depends_on:
    - N2-clipboard-integration
    footprint:
    - docs/features/steps/experts_copy_steps.py
    tests:
    - KARMA-COPY-01
    gate:
      command: make test-experts-s36-server
    guidance_bundle:
      activity: BPE/BPE-04-Implement_Feature_Acceptance_Tests.md
      rules:
      - do-test-first
      - do-not-mock-in-integration-tests
    notes: 'Parent must reconcile the proposed named make target before application. It must execute only KARMA-COPY-01
      using acceptance settings and --simple, not a broad historical feature scan. AT proves receipt/payload/domain;
      it does not independently inspect a browser clipboard.

      '
  - id: N4-real-clipboard
    title: Actual browser clipboard and paired award certification
    bpe: BPE-05
    depends_on:
    - N3-copy-acceptance
    footprint:
    - tests/e2e/test_karma_copy.py
    tests:
    - test_copy_prompt_with_maria_copies_actual_prompt_and_credits_pair
    - test_copy_prompt_with_list_and_embed_surfaces_reports_same_entity
    gate:
      command: make test-experts-s36-browser
    guidance_bundle:
      activity: BPE/BPE-05-Implement_Journey_Certification_Tests.md
      rules:
      - do-test-first
      - do-semantic-versioning-on-ui-elements
  - id: N5-copy-definition-of-done
    title: Receipt, logs, legacy rendering and actual clipboard rollup
    bpe: BPE-06
    depends_on:
    - N4-real-clipboard
    footprint: []
    tests:
    - tests/integration/test_copy_prompt.py
    - tests/integration/test_karma_copy.py
    - tests/e2e/test_karma_copy.py
    log_story_rows:
    - copy_success_receipt:entry
    - copy_success_receipt:validation
    - KarmaService.award_successful_consumption:processing
    - copy_success_receipt:exit
    - copy_success_receipt:branch
    gate:
      command: make test-experts-s36
      log_story_command: pytest tests/integration/test_karma_copy.py -k log_story -x
    guidance_bundle:
      activity: BPE/BPE-06-Check_Definition_of_Done.md
      rules:
      - do-test-first
      - do-assert-log-story
      - do-not-mock-in-integration-tests
  scenario_dependencies:
  - S03
  - S30
```

## Lessons Learned

- Existing clipboard code provides a precise success boundary; adding an award to rendering or generic click handling would violate the contract.
- Shared detail-button metadata is absent even though row metadata exists. Listing all seven real detail/embed callers avoids hiding later production footprint expansion.
- Clipboard success and receipt delivery are distinct outcomes. A copied prompt must remain copied and visibly successful while only its receipt is retried.
- The living-spec clipboard wording spans two test lanes. Django-client AT proves the reported action boundary and actual prompt payload; Playwright must independently prove clipboard contents.
- Event identity scope and shared source-kind/category names require one parent reconciliation with S03/S30. No new schema, seed importer or parallel award persistence should be invented.
