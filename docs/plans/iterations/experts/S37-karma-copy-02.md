# S37: KARMA-COPY-02 Let guests copy without creating an award

This plan uses [the consolidated contract](../pin-convergence-20261123-experts.md). Its shared interfaces, ownership decisions and verification-layer mapping govern this scenario. Commands in the graph below are the canonical execution gates; implementation and test bodies remain unimplemented.

```yaml
scenario: S37
acceptance_id: KARMA-COPY-02
feature_file_path: tests/e2e/experts-interactions.feature
feature_line: 45
primary_execution_layer: e2e
expanded_case_count: 1
dependencies:
- S03
- S07
- S36
system_dependencies: []
status: skeleton_applied_unimplemented
source_report_sha256:
- 701c21211322aeeac061597299338c602fbbf6a9eab97a35c0be0ca07e5372b1
```

## A — Context map


Paths below are relative to `/Users/denispetelin/GitHub/mimir-experts-replay`.

| Verified reference | Purpose |
|---|---|
| `static/js/copy_prompt.js:79-98` | Actual clipboard promise and delegated button handler. S36 owns receipt wiring and guest short-circuit here. |
| `methodology/services/copy_prompt_service.py:23-57` | Authoritative full activity prompt: instruction plus complete guidance. |
| `methodology/activity_views.py:374-416` | Existing anonymous authorized detail GET, guest context and server-built prompt. |
| `tests/e2e/conftest.py:101-117,141-168` | Existing fresh browser context/page and function-scoped server option; reuse their lifecycle. |
| `test-data/experts/cedar-rfp-01.json:704-714` | EV02: anonymous Bob copies activity6203; Mike remains12450; no account/award. |

Also verified: exact contract `karma-accrual.feature:75-80`; existing guest rendering coverage `tests/integration/test_copy_prompt.py:103-120`; button and hidden text `templates/partials/copy_prompt/button.html:1-18`; existing success message `templates/partials/copy_prompt/toast.html:2-12`.

Required result: a real anonymous browser copies Mike’s public released activity6203. Clipboard text exactly equals `CopyPromptService.build_activity_prompt(activity)`. No receipt request, account, profile or award is created; Mike remains12450.

## B — Do-not-do list


- No production modifications: S36 owns successful-copy receipt integration and guest exclusion; S03 owns schema/Cedar; S07 owns Bob’s common anonymous binding.
- Do not mock, replace or override `navigator.clipboard`; use real Chromium clipboard permissions.
- Do not substitute hidden textarea contents, a Django POST or fake Behave clipboard state for actual clipboard evidence.
- Do not create a Bob user, token, session login or Karma account to represent anonymity.
- Do not award Mike for guest consumption or increment eligible GUI-copy counts.
- Do not change prompt text, guest read authorization, existing success toast or authentication destinations.
- No migrations, seed changes, MCP changes, agent work, provider calls or new browser lifecycle.
- Keep the source acceptance contract intact; mapping interaction steps to Playwright preserves its full obligation.

## C — Applicable architecture


- SAO **Awards, projections and transaction boundaries**, `3836-3881`: anonymous consumption earns nothing; clipboard success is browser-owned; server validates reported receipts.
- SAO **Test strategy for this delta**, `3912-3928`: real Django-client server contracts and real Playwright interaction evidence; zero/skipped coverage is insufficient.
- SAO **Guest read security**, **Services Layer**, **E2E Testing with Playwright**, **Request ID Logging**.
- IA **6.2 Toast Notifications**, **9 Accessibility**, **11 Experts replay recipe and responsive coverage contract**.
- `docs/features/CATALOG.md:46-48` already assigns clipboard interaction to E2E.
- `docs/features/user_journey.md:3221` states the exact guest-copy result.

## D — Tests and precise assertions


| Proposed test | Required assertions |
|---|---|
| `test_guest_activity_with_initial_get_renders_full_prompt_without_awards` | Anonymous real Django GET200; enabled `copy-prompt-btn`; hidden activity6203 text equals full prompt; existing guest banner; no edit control; exact User/ExpertProfile identifiers and complete ledger rows unchanged; Mike12450. This is **server-contract AT**, never clipboard proof. |
| `test_guest_copy_receipt_with_anonymous_post_rejects_without_awards` | Valid-shaped direct anonymous POST to S36’s `karma_copy_receipt` rejects without HTML login redirect; proposed response401 with safe rejection JSON; full ledger/user/profile snapshots unchanged; Mike12450. Authentication rejection must be exercised rather than accidentally proving only missing CSRF. |
| `test_guest_copy_receipt_log_story_reject` | Same real anonymous rejection; shared `assert_log_story` captures S36-owned safe anonymous rejection branch, request ID and no-award outcome; no clipboard text, tokens, cookies or email in captured records. |
| `test_guest_copy_with_public_activity_copies_full_prompt_without_receipt_or_awards` | Fresh actual anonymous context; real click; `navigator.clipboard.readText()` exactly equals full service-built prompt; existing success toast says `Prompt copied to clipboard`; no false Karma-earned claim; observed network contains zero requests to receipt route throughout navigation/copy/settlement; Mike12450 and exact user/profile/ledger snapshots unchanged. |

Browser method:

1. Restore S03’s real Cedar dataset and calculate expected prompt before requesting the lazy Playwright page.
2. Reuse existing `page`, `context`, `live_server_url`; grant `["clipboard-read", "clipboard-write"]` explicitly for that live-server origin.
3. Start `page.on("request", ...)` observation before navigation. Record actual requests; never intercept, fulfill or suppress them.
4. Navigate via existing reversed activity route; click `get_by_test_id("copy-prompt-btn")`; await actual clipboard equality and visible success toast.
5. Observe normal completion/network settlement, assert zero receipt-path requests, then inspect real DB snapshots. Do not infer absent requests from absent logs.

Full `KARMA-COPY-02` maps to this Playwright test. The server tests separately certify initial HTML and direct forged-request rejection. Register no Behave clipboard/copy simulation and no duplicate Bob binding.

After PIN-04 issue/docs handoff and PIN-05 GO: implement certification tests against completed S36, record meaningful failures, and route any production defect to its owning scenario. Each node receives its own `Refs #N` commit and issue update; final closure uses `Closes #N`. No issue operations are performed by this worker.

## E — Log story


No new production logging is introduced. Certify S36’s existing planned rejection boundary:

| Where | Beat | Trigger | Must include |
|---|---|---|---|
| `copy_success_receipt` | branch | Direct anonymous receipt POST | request ID, safe unauthenticated reason, no-award outcome |

`test_guest_copy_receipt_log_story_reject` uses `tests/support/log_story.py::assert_log_story`. A normal successful guest copy has **no receipt request**, so no server receipt log is expected. Real network observation supplies that evidence.

## F — MCP tools


Not applicable. This is guest GUI certification; no tools, registration, facade/client changes or MCP proofs.

## G — Agent proofs


Not applicable. No agent capability, LLM workflow, ToolExecutor or SAO§17 PRF row changes.

## H — Mockup graduation and UAT


No graduation is needed in S37. Certify S36’s retained production Copy Prompt control/toast against the existing Act17 recipe; no new markup or UI messages.

Map `tests/uat/e2e-uat-flow.feature:850-851`, **UAT-18-04 A02**, to this guest lane: independent baseline restore, fresh anonymous context, actual clipboard, Mike12450, no Bob account/award. Record commit/environment, fixture hash, viewport, clipboard comparison result and observed network/DB evidence. Do not record full clipboard content in production logs. S38 owns the combined three-lane UAT run; S37 supplies A02 evidence. No UAT pass is claimed during planning.

## Parent convergence

Authoritative acceptance source: `tests/e2e/experts-interactions.feature:45`; 1 expanded case(s), primary layer `e2e`. Dependencies: S03, S07, S36. The full scenario includes all composed journey/UAT obligations assigned in the consolidated contract. Shared Make/catalog registration belongs only to S03.
This entire acceptance contract is browser-certified. Server checks are complementary initial-HTML/receipt contracts; no clipboard/hover/expansion Behave substitution is allowed.

## Canonical feature execution graph

```yaml
feature_execution_graph:
  feature_ref: KARMA-COPY-02
  nodes:
  - id: N1-guest-receipt-boundary
    title: Certify existing anonymous receipt rejection
    bpe: BPE-02
    depends_on: []
    footprint:
    - tests/integration/test_karma_guest_copy.py
    tests:
    - test_guest_copy_receipt_with_anonymous_post_rejects_without_awards
    - test_guest_copy_receipt_log_story_reject
    log_story_rows:
    - copy_success_receipt:branch
    gate:
      command: pytest tests/integration/test_karma_guest_copy.py -k receipt -x
      log_story_command: pytest tests/integration/test_karma_guest_copy.py -k log_story -x
    guidance_bundle:
      activity: BPE/BPE-02-Implement_Backend.md
      rules:
      - do-skeletons-first
      - do-test-first
      - do-not-mock-in-integration-tests
      - do-assert-log-story
  - id: N2-guest-server-contract
    title: Initial anonymous HTML and honest layer mapping
    bpe: BPE-04
    depends_on:
    - N1-guest-receipt-boundary
    footprint:
    - tests/integration/test_karma_guest_copy.py
    tests:
    - test_guest_activity_with_initial_get_renders_full_prompt_without_awards
    gate:
      command: pytest tests/integration/test_karma_guest_copy.py -x
    guidance_bundle:
      activity: BPE/BPE-04-Implement_Feature_Acceptance_Tests.md
      rules:
      - do-test-first
      - do-not-mock-in-integration-tests
  - id: N3-real-guest-clipboard
    title: Actual clipboard, observed network and unchanged domain
    bpe: BPE-05
    depends_on:
    - N2-guest-server-contract
    footprint:
    - tests/e2e/test_karma_guest_copy.py
    tests:
    - test_guest_copy_with_public_activity_copies_full_prompt_without_receipt_or_awards
    gate:
      command: make test-experts-s37-browser
    guidance_bundle:
      activity: BPE/BPE-05-Implement_Journey_Certification_Tests.md
      rules:
      - do-test-first
      - do-not-mock-in-integration-tests
      - do-semantic-versioning-on-ui-elements
  - id: N4-guest-definition-of-done
    title: Conjunctive server, log and real-browser rollup
    bpe: BPE-06
    depends_on:
    - N3-real-guest-clipboard
    footprint: []
    tests:
    - tests/integration/test_karma_guest_copy.py
    - tests/e2e/test_karma_guest_copy.py
    log_story_rows:
    - copy_success_receipt:branch
    gate:
      command: make test-experts-s37
      log_story_command: pytest tests/integration/test_karma_guest_copy.py -k log_story -x
    guidance_bundle:
      activity: BPE/BPE-06-Check_Definition_of_Done.md
      rules:
      - do-test-first
      - do-assert-log-story
      - do-not-mock-in-integration-tests
  scenario_dependencies:
  - S03
  - S07
  - S36
```

## Lessons Learned

The existing guest HTML test proves control availability only. Actual clipboard equality and zero observed receipt requests require browser execution. Bob is explicitly accountless in Cedar, so certify unchanged account/profile sets rather than inventing a guest user. S36’s older raw AT description must not turn its shared clipboard phrase into a markup assertion; this plan uses the parent’s corrected verification-layer ownership. All evidence remains pending implementation and execution.

## Structural application evidence

`docs/experts-replay/pin-evidence/S37.json` records positive scaffold selection and deliberate NotImplementedError. Existing callable ASTs were preserved. Browser collection is not interaction certification.
