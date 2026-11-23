# S38: KARMA-COPY-03 Do not award self-copy

This plan uses [the consolidated contract](../pin-convergence-20261123-experts.md). Its shared interfaces, ownership decisions and verification-layer mapping govern this scenario. Commands in the graph below are the canonical execution gates; implementation and test bodies remain unimplemented.

```yaml
scenario: S38
acceptance_id: KARMA-COPY-03
feature_file_path: tests/e2e/experts-interactions.feature
feature_line: 53
primary_execution_layer: e2e
expanded_case_count: 1
dependencies:
- S03
- S30
- S36
- S37
system_dependencies: []
status: skeleton_applied_unimplemented
source_report_sha256:
- 9630969855b293691a38e3dbd31dbb63b8027731c0711532a43b4b6660362217
```

## A — Verified context map


Paths below are relative to `/Users/denispetelin/GitHub/mimir-experts-replay`.

| Verified reference | Relevance |
|---|---|
| `static/js/copy_prompt.js:79-98` | Existing real clipboard promise and delegated click handler; currently no receipt. S36 owns its implementation. |
| `methodology/services/copy_prompt_service.py:39-57` | Builds the actual activity prompt, including instruction, playbook/workflow names and complete guidance. |
| `methodology/services/activity_service.py:937-975` | Existing activity resolver enforces the owning playbook’s read permission. |
| `tests/e2e/conftest.py:101-117,141-168` | Existing function-scoped context/page/live-server interfaces; reuse `page`, `context`, `live_server_url`. |
| `test-data/experts/cedar-rfp-01.json:717-727,1104-1113` | EV03 self-copy leaves Mike at 12,450; self/guest copies create no awards and do not increase his 47 eligible GUI copies. |

Additional verified sources: `karma-accrual.feature:82-86`; `tests/uat/e2e-uat-flow.feature:846-854`; `tests/integration/test_copy_prompt.py:43-120`; `tests/e2e/e2e_helpers.py:12-29`; `tests/e2e/pytest.ini`; root `pytest.ini`; SAO planned delta; graph schema; current ownership/guidance snapshots; S36 raw report.

S37 confirmed separate files `tests/integration/test_karma_guest_copy.py` and `tests/e2e/test_karma_guest_copy.py`, and browser test `test_guest_copy_with_public_activity_copies_full_prompt_without_receipt_or_awards`. Normal guest copying sends no receipt; a forged anonymous receipt is separately rejected.

## B — Do-not-do list


- Do not implement or duplicate S36’s clipboard JavaScript, endpoint, target resolver, exclusions or persistence.
- Do not treat self-copy as a clipboard failure or authorization failure.
- Do not award either a learner or author row for self-copy, including two rows for the same person.
- Do not increment Mike’s eligible GUI-copy count from 47; Maria remains at baseline 8,200.
- Do not substitute textarea inspection, a stubbed clipboard or fake Behave state for actual browser clipboard proof.
- Do not remove the full clipboard clause from KARMA-COPY-03.
- Do not add Behave bindings claiming to inspect a clipboard.
- Do not combine backend caplog tests with the E2E configuration that disables logging.
- Do not alter global browser fixture lifecycles, middleware, permissions, migrations, seed data or MCP registration.
- Do not exercise clipboard-failure behavior here; S46 owns that adverse contract.
- Do not send email or create an in-app UAT evidence viewer.
- Do not claim UAT observations, screenshots, human usability or successful gates during PIN.

## C — Governing architecture and interfaces


SAO headings: **Services Layer**; **Security & Access Control / Guest read security**; **E2E Testing with Playwright**; **Request ID Logging**; **Experts & Karma delivery architecture / Awards, projections and transaction boundaries**, **Web delivery and notification reuse**, **Test strategy for this delta**.

Self-copy is a successful authorized content operation with an excluded award outcome. S36 supplies:

```text
KarmaService.award_successful_consumption(
    actor, entity_type, entity_id, event_identity, *, channel
) -> tuple[AwardOutcome, ...]

POST reverse("karma_copy_receipt") = /karma/copy-receipts/
JSON inputs: entity_type, entity_id, event_identity only
actor: request.user; channel: server-fixed gui_copy
```

Converge the successful exclusion response in S36 as HTTP 200 with an explicit safe envelope, proposed `{"status": "skipped", "reason": "self_consumption"}`. The service returns an empty award tuple. This is a shared S36 interface requirement, not S38 production ownership.

Use S03’s `load_cedar_baseline()` and `users_by_username["mchen"]`; actual actor username is `mchen`, not a newly created “Mike”. Activity 6203 belongs to workflow 6202/playbook 6201. Read prompt expectations through `CopyPromptService.build_activity_prompt(real_activity)`.

The browser reports completed clipboard success; the server revalidates authenticated actor/entity/access. The server cannot independently inspect clipboard contents.

## D — Tests and exact assertions


| Proposed test | Required assertion |
|---|---|
| `test_award_successful_consumption_with_self_activity_returns_no_awards` | Real S36 service returns `()`; complete ordered ledger snapshot unchanged, Mike 12,450, Maria 8,200, eligible GUI copies 47. |
| `test_copy_receipt_with_self_activity_returns_successful_exclusion` | Strict-CSRF authenticated client GETs real detail, retrieves actual token and POSTs actual receipt route; HTTP 200, explicit self exclusion; unchanged ledger/projections. |
| `test_copy_receipt_with_self_activity_without_csrf_returns_forbidden` | `Client(enforce_csrf_checks=True)` authenticated POST without token returns 403, creates no awards. It must not silently pass through an ordinary permissive client. |
| `test_copy_receipt_with_self_activity_log_story_happy` | Real self receipt emits the Section E beats under one request identity, including self exclusion and successful exit; no pair-persistence beat or sensitive bodies. |
| `test_copy_prompt_with_mike_copies_actual_prompt_without_awards` | Real login, clipboard permissions, actual button click, exact full clipboard text, observed actual receipt request/200 self-exclusion response, unchanged entire ledger and 12,450/8,200/47 projections. |
| `test_copy_uat_with_independent_baseline_lanes_matches_contract` | Three parametrized browser cases independently restore Cedar: Maria 8,205/Mike 12,455; guest Mike 12,450/no Bob account or awards/no receipt; Mike self 12,450/no awards. Every lane copies the actual full prompt. |

For browser tests: explicitly grant `["clipboard-read", "clipboard-write"]` to the actual `live_server_url` origin using existing `context`. Read `navigator.clipboard.readText()` after the real click. Do not replace `navigator.clipboard`, intercept requests with fabricated responses, or use browser `request.post()` as the copy action.

Capture the actual request with `page.expect_response` around the click; assert method, target identity, real response and self outcome. A completed receipt proves the server processed self-copy, avoiding a vacuous “no points because receipt never ran” pass.

Snapshot ledger row values and identities, not only row count or the final summed total. Existing user/profile counts also remain unchanged. Mike’s 47 comes from the live ledger projection, not JSON’s declared `copy_count`.

## E — Log story


S38 certifies S36-owned production logs; it adds no new logger or production method.

| Where | Beat | Trigger | Must include |
|---|---|---|---|
| `copy_success_receipt` | entry | Authenticated receipt | request ID, actor ID, `gui_copy` |
| `copy_success_receipt` | validation | Allowlisted payload | activity 6203, action identity, validated outcome |
| `KarmaService.award_successful_consumption` | validation | Authorized target resolved | actor ID, playbook snapshot 6201, channel |
| `KarmaService.award_successful_consumption` | branch | Actor owns target | `self_consumption`, zero awards |
| `copy_success_receipt` | exit | Successful excluded receipt | action identity, skipped outcome |

Use `tests/support/log_story.py::assert_log_story`, plus explicit ordering/correlation assertions because that helper alone does not enforce order. Assert absence of pair-persistence processing. Never log prompt text, clipboard contents, email, cookies, credentials or CSRF values.

Missing-CSRF rejection belongs to Django middleware; do not invent an application log beat for a view that must not execute.

## F — MCP tools


Not applicable. GUI certification changes no MCP tool, facade registration, client schema or authorization surface. S39/S42 own their MCP proofs.

## G — Agent proofs


Not applicable. No SAO §17 capability, model invocation, PRF or agent orchestration changes. No ScriptedLLM, ToolExecutor or agent-proof gate is introduced.

## H — Mockup graduation and UAT


No BPE-03 node: this scenario certifies the existing production Copy Prompt component as extended by S36. Preserve the shared button, complete prompt and existing clipboard-success feedback. No new UI or Karma-earned message is warranted for excluded self-copy.

S38 owns terminal **UAT-18-04**, consuming S37’s guest certification:

1. Independently restore Cedar; Maria copies actual activity 6203: clipboard correct, 8,205/12,455, Development attribution.
2. Independently restore Cedar; fresh anonymous context copies the same content: clipboard correct, Mike 12,450, no Bob account/awards.
3. Independently restore Cedar; Mike copies his own content: clipboard correct, Mike 12,450, Maria 8,200, GUI-copy count 47.

Record actual operator identity/type, timestamp, environment, commit, fixture hash, viewport, each baseline restoration, observed clipboard/result, screenshots or recording references, and discrepancies under the run’s UAT evidence directory. Automated execution is labelled scripted certification; it is not evidence that a human performed UAT. Existing UAT script remains authoritative. No observations are recorded by this plan.

## Parent convergence

Authoritative acceptance source: `tests/e2e/experts-interactions.feature:53`; 1 expanded case(s), primary layer `e2e`. Dependencies: S03, S30, S36, S37. The full scenario includes all composed journey/UAT obligations assigned in the consolidated contract. Shared Make/catalog registration belongs only to S03.
This entire acceptance contract is browser-certified. Server checks are complementary initial-HTML/receipt contracts; no clipboard/hover/expansion Behave substitution is allowed.

## Canonical feature execution graph

```yaml
feature_execution_graph:
  feature_ref: KARMA-COPY-03
  nodes:
  - id: N1-self-domain-proof
    title: Certify shared self-consumption exclusion
    bpe: BPE-02
    depends_on: []
    footprint:
    - tests/integration/test_karma_copy.py
    tests:
    - test_award_successful_consumption_with_self_activity_returns_no_awards
    - test_copy_receipt_with_self_activity_log_story_happy
    log_story_rows:
    - copy_success_receipt:entry
    - copy_success_receipt:validation
    - KarmaService.award_successful_consumption:validation
    - KarmaService.award_successful_consumption:branch
    - copy_success_receipt:exit
    gate:
      command: pytest tests/integration/test_karma_copy.py -k 'self_activity' -x
      log_story_command: pytest tests/integration/test_karma_copy.py::test_copy_receipt_with_self_activity_log_story_happy
        -x
    guidance_bundle:
      activity: BPE/BPE-02-Implement_Backend.md
      rules:
      - do-skeletons-first
      - do-test-first
      - do-not-mock-in-integration-tests
      - do-assert-log-story
      - do-docstring-format
  - id: N2-self-server-contract
    title: Certify strict-CSRF successful self receipt
    bpe: BPE-04
    depends_on:
    - N1-self-domain-proof
    footprint:
    - docs/ux/experts-test-assets.md
    - tests/integration/test_karma_copy.py
    tests:
    - test_copy_receipt_with_self_activity_returns_successful_exclusion
    - test_copy_receipt_with_self_activity_without_csrf_returns_forbidden
    gate:
      command: pytest tests/integration/test_karma_copy.py -k 'self_activity' -x
    guidance_bundle:
      activity: BPE/BPE-04-Implement_Feature_Acceptance_Tests.md
      rules:
      - do-test-first
      - do-not-mock-in-integration-tests
      - pytest
  - id: N3-self-clipboard-and-composed-lanes
    title: Actual clipboard contract and independently restored UAT lanes
    bpe: BPE-05
    depends_on:
    - N2-self-server-contract
    footprint:
    - tests/e2e/test_karma_copy.py
    tests:
    - test_copy_prompt_with_mike_copies_actual_prompt_without_awards
    - test_copy_uat_with_independent_baseline_lanes_matches_contract
    gate:
      command: make test-experts-s38-browser
    guidance_bundle:
      activity: BPE/BPE-05-Implement_Journey_Certification_Tests.md
      rules:
      - do-test-first
      - do-semantic-versioning-on-ui-elements
      - pytest
  - id: N4-self-copy-dod
    title: Conjunctive certification and observed UAT evidence review
    bpe: BPE-06
    depends_on:
    - N3-self-clipboard-and-composed-lanes
    footprint:
    - docs/ux/experts-test-assets.md
    tests:
    - tests/integration/test_karma_copy.py
    - tests/e2e/test_karma_copy.py
    - tests/e2e/test_karma_guest_copy.py
    log_story_rows:
    - KarmaService.award_successful_consumption:branch
    - copy_success_receipt:exit
    gate:
      command: make test-experts-s38
      log_story_command: pytest tests/integration/test_karma_copy.py::test_copy_receipt_with_self_activity_log_story_happy
        -x
    guidance_bundle:
      activity: BPE/BPE-06-Check_Definition_of_Done.md
      rules:
      - do-test-first
      - do-assert-log-story
      - do-not-mock-in-integration-tests
      - do-follow-commit-convention
  scenario_dependencies:
  - S03
  - S30
  - S36
  - S37
```

## Lessons Learned

- Unchanged totals alone cannot prove self-copy: observe the actual successful self receipt and inspect the full clipboard.
- The existing E2E settings disable logging, so backend log proofs need a separate process.
- Mike’s 47-copy fallback is an independent ledger projection that self-copy must preserve.
- UAT lanes require independent restores; running guest/self after Maria’s award without reset produces misleading baselines.
- Earlier S36 raw Behave clipboard wording is superseded by the explicit browser-layer mapping; preserve the complete acceptance contract.

## Structural application evidence

`docs/experts-replay/pin-evidence/S38.json` records positive scaffold selection and deliberate NotImplementedError. Existing callable ASTs were preserved. Browser collection is not interaction certification.
