# S46: KARMA-EVENT-02 Do not award failed or unauthorized consumption

This plan uses [the consolidated contract](../pin-convergence-20261123-experts.md). Its shared interfaces, ownership decisions and verification-layer mapping govern this scenario. Commands in the graph below are the canonical execution gates; implementation and test bodies remain unimplemented.

```yaml
scenario: S46
acceptance_id: KARMA-EVENT-02
feature_file_path: docs/features/act-18-experts/karma-accrual.feature
feature_line: 137
primary_execution_layer: at
expanded_case_count: 1
dependencies:
- S36
- S39
- S42
- S45
system_dependencies: []
status: skeleton_applied_unimplemented
source_report_sha256:
- 5bc070a56d050637c066e2a792901af48113ac05f039d45656d2378f7234c357
```

## A — Context map


Paths below are relative to `/Users/denispetelin/GitHub/mimir-experts-replay`.

| Verified reference | Why it matters |
|---|---|
| `static/js/copy_prompt.js:79-98`; `tests/integration/test_copy_prompt.py:43-120` | Actual clipboard promise resolves into success and rejects into `showCopyError`; existing real rendering coverage supplies stable selectors. |
| `methodology/services/playbook_service.py:145-179`; `methodology/services/pip_service.py:513-532` | Actual authorization boundaries. Private playbooks remain unavailable; PIPs require creator or existing staff access. |
| `methodology/api/viewsets.py:74-86,699-709,772-790`; `methodology/api/viewsets_resources.py:379-390` | Real filtered detail/export endpoints and PIP 403/404 responses; export bundle generation checks access before local writes. |
| `mcp_integration/facade/tools_http.py:503-531,609-659`; `methodology/services/workflow_export_service.py:17-100` | Actual filesystem writes can fail after earlier writes. S42 must dispatch consumption receipts only after every requested output succeeds. |
| `tests/e2e/conftest.py:100-117,144-168`; `tests/support/log_story.py:9-42` | Existing function-context browser/page fixtures, function-server option, and real caplog assertion helper. |

Also inspected: orient roster, exact feature, Cedar JSON, user journey’s Karma matrix, SAO delta, facade client/server, legacy registration, permission tests, S36/S39/S42/S45 raw reports, ownership convergence, actual Edda BPE activity files and graph schema.

Existing permission regression: `tests/integration/test_mcp_playbook_tools.py:155-169` proves a real non-owner private released playbook raises masked `ValueError("…not found")` through legacy MCP. Preserve that masking rather than requiring identical exception classes across transports.

## B — Do not do


- No new award writer, event schema, migration, seed import, queue, provider, endpoint or MCP server.
- S30 persists awards; S36 owns eligibility/GUI receipts; S39 owns authenticated MCP receipts; S42 owns export completion; S45 owns identity/retry atomicity.
- No awards on denied/missing reads, clipboard rejection, path rejection or incomplete exports.
- Do not widen PIP, private, team or group access.
- Do not trust client actor/author/category/points/source/time/channel overrides or a valid-looking UUID.
- Do not claim success from unchanged totals alone: compare the entire global ledger.
- No service/HTTP mocks, fabricated responses, `navigator.clipboard` overrides, `chmod` failure assumptions or writes to ambient development databases.
- Do not conflate failed file export with completed files followed by failed/ambiguous receipt delivery.
- Do not treat server-contract AT as actual clipboard certification.
- Preserve working bodies during PIN. S46 proposes test/support skeletons only; production defects remain with their owning scenarios.

## C — Architecture and algorithm


Applicable SAO headings: **Experts & Karma delivery architecture / Awards, projections and transaction boundaries**, **Test strategy for this delta**, **Security & Access Control / Guest read security**, **MCP Integration: Implementation Patterns**, **Critical Discovery: stdio Pollution Prevention**, **Request ID Logging**, **E2E Testing with Playwright**.

Each independently restored case:

1. Load S03’s real Cedar adapter; construct any necessary test-local private child entities through real ORM relations.
2. Snapshot every concrete field of every `KarmaAward`, ordered by primary key.
3. Execute an actual failing or unauthorized operation through the supported boundary.
4. Assert its real denial/failure and absence of private content.
5. Compare the complete global ledger, including identities, recipients, snapshots, points and timestamps. Additionally reconcile Maria/Mike baseline totals where applicable.

For rejected receipt replay, first create one legitimate eligible event, snapshot the resulting global ledger, then submit the adversarial request. Its rejection must preserve that existing event exactly.

### Real filesystem failures

Use `tmp_path` under the authorized workspace and actual authorized bundles.

- Immediate failure: create a regular file where a required parent directory must be. Actual `mkdir`/write raises `NotADirectoryError` or the existing safe export exception.
- Partial failure: for playbook export, precreate `<export_root>/rules` as a **regular file**. The actual top-level playbook Markdown can be written first; the later rule-directory operation fails. Assert earlier file contents match the genuine bundle and no consumption event exists.
- Include mirror/ADE failure destinations when requested outputs exist in the real fixture.
- Traversal/symlink cases exercise S42’s actual confinement guard. Outside sentinels remain unchanged.
- Preflight may reject a known impossible destination before writing. Record that honestly; retain a separate genuine runtime filesystem failure case. Never force a “partial files” assertion when preflight prevented writes.

### Post-export receipt failure

A distinct test completes real files, then receives actual authentication failure on receipt: temporarily connect a test-only `request_finished` receiver immediately around the dedicated facade invocation. Its first real request is the successful bundle request; the receiver deletes the actor’s real DRF token before the later receipt request. No HTTP response is replaced.

Assert bundle success, actual completed outputs, real receipt 401, `files_written=true`, and recoverable operation UUID. Restore authentication and retry **only** that receipt UUID; exactly one pair is eventually persisted, without rewriting files. This is completed export with receipt failure, not failed export. An ambiguous receipt outcome never licenses claiming globally unchanged awards.

### Real clipboard denial

Use existing Chromium context/page fixtures. The installed official Playwright protocol at `/Users/denispetelin/GitHub/mimir/.venv/lib/python3.14/site-packages/playwright/driver/package/types/protocol.d.ts:2000-2014` documents `Browser.grantPermissions` as granting the specified permissions and rejecting all others, scoped by `browserContextId`.

Obtain the actual page context ID via `Target.getTargetInfo`, then use `Browser.grantPermissions` with `permissions=[]`, the live-server origin and that context ID. Verify native `navigator.permissions.query({name:"clipboard-write"})` reports denied; click the real Copy Prompt control. Observe the real `NotAllowedError`/error toast, no success state, no GUI receipt request and unchanged ledger after bounded UI settling.

This protocol control is deprecated but present in the installed schema. Its actual rejection must be demonstrated during BPE. If Chromium still permits the write or cannot expose a genuine denial, fail/flag the certification limitation; do not substitute JavaScript overrides, skip the test or claim coverage.

## D — Tests to create


Create `tests/integration/karma_event/test_failures.py`, with module-level `pytestmark = pytest.mark.django_db(transaction=True)`.

| Exact test | Required assertions |
|---|---|
| `test_consumption_with_denied_or_missing_target_preserves_global_ledger` | T2: parameterize nine entity kinds × private-denied/missing; real S36 resolver/service and ORM. Denial precedes persistence; no content leak; complete ledger unchanged. PIP uses noncreator nonstaff actor. |
| `test_mcp_detail_with_denied_or_missing_target_preserves_global_ledger` | T1: nine registered detail tools × private-denied/missing × facade/legacy. Actual FastMCP client discovery/call; real token/live HTTP or existing user context. Actual error envelope, no secret content, unchanged global ledger. |
| `test_mcp_detail_with_invalid_token_preserves_global_ledger` | Actual facade configured with absent/invalid real credentials; tools still discoverable, detail execution fails authentication, no award. |
| `test_receipt_with_forged_fields_or_revoked_access_preserves_global_ledger` | Real session CSRF-valid GUI POST and token MCP receipt POST. Valid UUID cannot bypass unknown attribution fields, actor substitution, missing entity, private entity or access revoked after earlier read. Include known eligible UUID replay under another actor/channel/target. Rejected attempts preserve every row. |
| `test_export_with_real_filesystem_failure_preserves_global_ledger` | Both facade exports and both real legacy filesystem services; actual file-as-parent failure, confinement rejection and requested late-output failure cases. No receipt/award after incomplete export, including cases leaving real partial files. |
| `test_export_with_receipt_authentication_failure_preserves_completed_files` | Real token revocation after bundle; completed actual files, `files_written=true`, recoverable UUID; later receipt-only retry gives exactly one pair and preserves file contents/mtime. |
| `test_mcp_stdio_with_denied_read_or_failed_export_returns_safe_error` | T3: real facade subprocess against isolated `live_server`, initialize/tools-list/tools-call; private denied read and real file-as-parent export failure; clean JSON-RPC stdout, no leaked private body/token, global ledger unchanged. |
| `test_consumption_failure_log_story_reject` | Real private/missing/forged receipt paths plus filesystem failure; `assert_log_story`, safe distinct reasons, no award-success for rejected invocation, no private body/email/token/prompt. |
| `test_consumption_receipt_failure_log_story_recovery` | Actual completed-files/receipt-authentication-failure/replay story; same UUID, `files_written=true`, receipt retry only, eventual exact pair. |

Create `tests/e2e/test_karma_failures.py`:

| Exact test | Required assertions |
|---|---|
| `test_copy_prompt_with_native_clipboard_denial_creates_no_receipt_or_awards` | Real authenticated Maria, activity 6203, genuine browser permission denial and click. Error feedback, no success state, zero receipt requests, complete global ledger unchanged. |

Backend caplog and browser tests run separately. Use existing E2E settings and function server:

```bash
E2E_LIVE_SERVER_SCOPE=function pytest -c tests/e2e/pytest.ini -o addopts= -p no:playwright -p no:asyncio -p no:anyio tests/e2e/test_karma_failures.py -x
```

AT owns one exact When and Then binding. The When runs genuine **server** private-read/receipt rejection and filesystem-service failure cases. It does not execute or pretend to execute clipboard interaction. Catalog records KARMA-EVENT-02 satisfaction as server AT **and** browser denial certification.

`make test-at-karma-failure-server` runs exactly:

```bash
DJANGO_SETTINGS_MODULE=mimir.settings.acceptance $(PYTHON) manage.py behave --simple --tags=@experts --name='^KARMA-EVENT-02 ' docs/features/act-18-experts/karma-accrual.feature
```

Require one executed scenario, zero undefined/skipped selected steps and real assertions. Explicit `@experts` selection overrides WIP for this named server contract; aggregate Experts remains incomplete until its real contracts pass.

## E — Log story


S46 asserts owner-provided logs; it introduces no competing production logger.

| Where | Beat | Trigger | Must include |
|---|---|---|---|
| S36/S39 receipt boundary | entry | Receipt submitted | request/correlation ID, authenticated actor ID, channel |
| Shared target resolver | branch | Private/missing entity | safe denial/not-found reason, entity kind/ID, no award |
| Receipt parser | validation | Forged fields/identity mismatch | rejected reason, UUID when valid, no caller attribution accepted |
| S42 export boundary | error | Path/filesystem operation fails | operation UUID, safe failure reason, completed-file count, `receipt_sent=false` |
| S42 receipt dispatch | error | Files complete; receipt denied | same UUID, `files_written=true`, receipt failed |
| S39/S45 receipt retry | exit | Authentication restored; retry succeeds | original UUID, created/replayed outcome, correct pair count |

Global-ledger assertions prove persistence; logs alone do not. For rejected operations, assert absence of successful receipt/award beats correlated to that invocation. Do not log secret tokens, private content, clipboard text or email addresses.

## F — MCP exposure and proofs


No new tool/schema/registration. Certify these existing tools:

- Detail: `get_playbook`, `get_workflow`, `get_phase`, `get_activity`, `get_skill`, `get_rule`, `get_agent`, `get_artifact`, `get_pip`.
- Export: `export_workflow_to_local`, `export_playbook_to_local`.

Verified facade registration: `mcp_integration/facade/server.py:64-100`; startup calls `_build_mcp()` before stdio/SSE in `166-188`. HTTP client configuration/authentication/error mapping is `mcp_integration/facade/client.py:17-86`.

Verified legacy initialization: `mcp_integration/tools.py:3674-3720`; management startup invokes `initialize_mcp()` at `mcp_integration/management/commands/mcp_server.py:67-74`, then stdio at `117`.

T1/T2/T3 are explicit Section D tests. Legacy async ORM fixture/assertion work uses real `sync_to_async`; do not introduce `DJANGO_ALLOW_ASYNC_UNSAFE` into backend tests. Reuse S39-owned real MCP support without importing decorated Behave modules.

Existing `test_mcp_facade.py` subprocess backend selects ambient `mimir.db`; do not reuse that backend lifecycle.

## G — Agent proofs


Not applicable. No SAO §17 agent behavior, LLM completion, ScriptedLLM fixture, ToolExecutor or PRF row is affected.

## H — Mockup graduation


No new UI graduation. Preserve S36’s production Copy Prompt controls and existing error feedback. Browser evidence certifies actual failure behavior; server initial HTML and receipt arithmetic are separately identified contracts. No BPE-03 node.

## Parent convergence

Authoritative acceptance source: `docs/features/act-18-experts/karma-accrual.feature:137`; 1 expanded case(s), primary layer `at`. Dependencies: S36, S39, S42, S45. The full scenario includes all composed journey/UAT obligations assigned in the consolidated contract. Shared Make/catalog registration belongs only to S03.

## Canonical feature execution graph

```yaml
feature_execution_graph:
  feature_ref: KARMA-EVENT-02
  nodes:
  - id: N1-boundaries
    title: Certify real denial, export failures and recovery
    bpe: BPE-02
    depends_on: []
    footprint:
    - tests/integration/karma_event/test_failures.py
    - tests/support/karma_failures.py
    tests:
    - tests/integration/karma_event/test_failures.py
    log_story_rows:
    - receipt:entry
    - resolver:branch
    - parser:validation
    - export:error
    - receipt:error
    - retry:exit
    gate:
      command: pytest tests/integration/karma_event/test_failures.py -x
      log_story_command: pytest tests/integration/karma_event/test_failures.py -k log_story -x
    guidance_bundle:
      activity: BPE/BPE-02-Implement_Backend.md
      rules:
      - do-skeletons-first
      - do-test-first
      - do-not-mock-in-integration-tests
      - do-assert-log-story
      - pytest
  - id: N2-server-at
    title: Bind exact server contract without simulated clipboard
    bpe: BPE-04
    depends_on:
    - N1-boundaries
    footprint:
    - docs/features/steps/experts_karma_failure_steps.py
    gate:
      command: make test-experts-s46-at
    guidance_bundle:
      activity: BPE/BPE-04-Implement_Feature_Acceptance_Tests.md
      rules:
      - do-test-first
      - do-not-mock-in-integration-tests
      - pytest
  - id: N3-native-clipboard
    title: Certify native clipboard denial in real Chromium
    bpe: BPE-05
    depends_on:
    - N2-server-at
    footprint:
    - tests/e2e/test_karma_failures.py
    gate:
      command: make test-experts-s46-browser
    guidance_bundle:
      activity: BPE/BPE-05-Implement_Journey_Certification_Tests.md
      rules:
      - do-test-first
      - do-not-mock-in-integration-tests
      - do-semantic-versioning-on-ui-elements
      - pytest
  - id: N4-dod
    title: Require all failure and recovery evidence
    bpe: BPE-06
    depends_on:
    - N3-native-clipboard
    footprint: []
    log_story_rows:
    - receipt:entry
    - resolver:branch
    - parser:validation
    - export:error
    - receipt:error
    - retry:exit
    gate:
      command: make test-experts-s46
      log_story_command: pytest tests/integration/karma_event/test_failures.py -k log_story -x
    guidance_bundle:
      activity: BPE/BPE-06-Check_Definition_of_Done.md
      rules:
      - do-test-first
      - do-assert-log-story
      - do-not-mock-in-integration-tests
      - do-follow-commit-convention
      - pytest
  scenario_dependencies:
  - S36
  - S39
  - S42
  - S45
```

## Lessons Learned

PIN-04 publishes the concrete A–H contract, graph, skeleton footprint/SHA and docs handoff; PIN-05 owns human GO. Later slices: backend/log certification → server AT → genuine browser denial → conjunctive DoD. Each implementation slice references its issue and receives the required commit-linked update; final green slice closes it. No main merge/release authority is implied.

1. Private denial commonly uses 404 masking; assert real protected behavior without forcing one exception class across transports.
2. UUID validity is identity syntax, never authorization or proof of clipboard success.
3. Full-ledger equality catches compensating, misattributed or mutated awards that total-only assertions miss.
4. Filesystem failure can leave useful partial files while correctly earning zero awards.
5. Completed files plus failed receipt are recoverable delivery state; retrying the export itself risks creating another intentional event.
6. Native clipboard denial is an execution obligation, not a conclusion established by protocol documentation.

## Structural application evidence

`docs/experts-replay/pin-evidence/S46.json` records positive scaffold selection and deliberate NotImplementedError. Existing callable ASTs were preserved. Browser collection is not interaction certification.

## Actual structural footprint

`docs/experts-replay/pin-evidence/S46.json`, `docs/features/steps/experts_karma_failure_steps.py`, `docs/plans/iterations/experts/S46-karma-event-02.md`, `tests/e2e/test_karma_failures.py`, `tests/integration/karma_event/test_failures.py`, `tests/support/karma_failures.py`

Skeleton: `d0c0bd1a4586a4753c3a003cde0d8816d3dec411`; shared reconciliation: `39d598328d438d09723b6eb14574fbf92fab71c9`. Semantic and physical-file dependencies are recorded separately in the iteration manifest. Context-map line ranges record the workers’ inspection baseline; headers and the final scaffold remain authoritative.
