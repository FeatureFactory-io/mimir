# S42: KARMA-EXPORT-01 Credit one eligible export call regardless of file count

This plan uses [the consolidated contract](../pin-convergence-20261123-experts.md). Its shared interfaces, ownership decisions and verification-layer mapping govern this scenario. Commands in the graph below are the canonical execution gates; implementation and test bodies remain unimplemented.

```yaml
scenario: S42
acceptance_id: KARMA-EXPORT-01
feature_file_path: docs/features/act-18-experts/karma-accrual.feature
feature_line: 113
primary_execution_layer: at
expanded_case_count: 1
dependencies:
- S03
- S30
- S36
- S39
system_dependencies: []
status: skeleton_applied_unimplemented
source_report_sha256:
- 4bbad290cf291971993aff13526842c6dba17e6bbd66461c386d173935df2afc
- e0854e62c9c888090c790ef580850422b5568f8c90fc1e0e2060516061901cc0
```

### A — Context map


| Verified reference | Significance |
|---|---|
| `docs/features/act-18-experts/karma-accrual.feature:133–138`; `test-data/experts/cedar-rfp-01.json:824–839` | Workflow 6202 must produce actual confined files and exactly two five-point awards; Cedar baseline totals are Maria 8200 and Mike 12450. |
| `mcp_integration/facade/tools_http.py:476–678` | Both real facade exports fetch authorized bundles, then write files locally. Workflow includes sibling rules and Cursor copies; playbook includes mirrors and ADE copies. Receipt belongs after completion of these operations. |
| `mcp_integration/facade/workspace_mount.py:167–245` | Existing Docker guard validates workspace/bind mount and requested top-level path. It does not validate every server-returned child destination. |
| `methodology/services/workflow_export_service.py:17–127`; `methodology/services/playbook_export_service.py:30–145` | Existing legacy filesystem implementations; preserve them and add shared-domain award dispatch only after successful file completion. Bundle generators remain non-awarding. |
| `mcp_integration/facade/server.py:64–92,164–192`; `mcp_integration/tools.py:1154–1264,3674–3709` | Facade `_build_mcp()` and legacy `initialize_mcp()` already register both export tools; no second MCP server or new public tool is needed. |

Additional verified warning: `tests/integration/test_mcp_facade.py` has a subprocess server helper explicitly selecting real `mimir.db`. Do not reuse that database lifecycle for Cedar. Use pytest-django’s isolated `live_server` and transaction-capable test database.

### B — Do not do


- Do not award when generating the REST export bundle: Django cannot observe the facade’s eventual local file writes.
- Do not call public `get_*` wrappers while exporting; their detail receipts would create nested consumption events.
- Do not award per file, activity, workflow inside a playbook, mirror or ADE copy.
- Do not accept actor/recipient/author/points/category from MCP tool arguments. Token/context identifies actor; S36 resolves eligibility and attribution.
- Do not implement Karma business rules or ORM access in the facade.
- Do not broaden access, alter existing released-playbook export permission, or write Cedar into the tracked seed/production database.
- Do not replace working export bodies with raising stubs during PIN.
- Do not claim filesystem rollback: existing exports can leave files behind after an intermediate failure.
- Do not add UI, agent orchestration, ToolExecutor, provider or queue work.

### C — Governing SAO sections


- **Experts & Karma delivery architecture — planned delta / Awards, projections and transaction boundaries:** one paired atomic award per successful authenticated invocation; export channel; independent invocations use independent identities.
- **MCP Integration: Implementation Patterns / Architecture Decision: Service Layer + MCP Tools:** shared Django business logic, thin transport adapters.
- **Critical Discovery: stdio Pollution Prevention:** added logs stay off stdout.
- **Security & Access Control / FOB** and **REST API Specification / Authentication:** existing authorization precedes export/receipt.
- **Request ID Logging:** safe identifiers and correlation context.

### D — Tests and exact assertions


Create `tests/integration/test_karma_exports.py`; use real Cedar adapter, DB, DRF token, HTTP connection, registered FastMCP server and actual `tmp_path` files. No HTTP/domain mocks.

| Planned test | Required assertions |
|---|---|
| `test_karma_export_facade_t1_with_multiple_files_awards_one_pair` | Parameterize workflow/playbook tool. `Client(transport=_build_mcp())` discovers and calls actual registered tool; shared facade client points at `live_server`; valid Maria token. Workflow 6202/playbook 6201 files contain actual exported content, count exceeds one, all resolved destinations belong to their authorized roots. Ledger delta is exactly two rows, five points each, `event_channel=export`, one shared UUID. Maria 8205, Mike 12455; Learning/Consumption attribution and Development snapshot correct. No `mcp_detail` awards. |
| `test_karma_export_service_t2_with_multiple_files_awards_one_pair` | Parameterize the two existing filesystem service methods. Real Maria and source objects; actual files. Same ledger/totals/channel assertions. No per-file or nested-workflow duplication. |
| `test_karma_export_with_mirrors_and_ade_files_awards_one_pair` | Real playbook export with additional target and actual ADE file sync; all requested copies exist, contents match, still exactly two new award rows. Preserve canonical flags and existing export return shape. |
| `test_karma_export_with_second_independent_call_creates_new_identity` | Two complete calls yield four rows, two UUIDs, totals 8210/12460. An export invocation is not globally deduplicated by content ID. |
| `test_karma_export_bundle_with_generation_only_creates_no_awards` | Actual authenticated POSTs to both existing bundle endpoints return content without creating files or ledger rows. |
| `test_karma_export_with_receipt_replay_preserves_single_pair` | Complete one actual export, then repeat its receipt through S39 endpoint using that UUID and unchanged payload. Exactly two rows remain, timestamps and payload unchanged. No second file export required. Broader retry ownership remains S45. |
| `test_karma_export_with_escaping_folder_or_symlink_rejects_before_write` | Parameterize workflow/playbook; actual traversal folder and precreated symlink escape. Reject before any file write or receipt; outside sentinel unchanged; ledger unchanged. This is S42’s confinement proof, not S46’s full failure matrix. |
| `test_karma_export_with_partial_file_failure_creates_no_receipt` | Produce deterministic real `OSError` by placing a directory at a later expected file destination. Earlier actual write may remain; invocation fails; no export award exists. No patched `Path.write_text`. S46 extends the matrix. |
| `test_karma_export_stdio_t3_with_success_returns_clean_jsonrpc` | Isolated facade subprocess with test HTTP server/token/workspace; initialize, tools/list, tools/call for both export tools; parse protocol-only stdout, actual files and exactly one award pair per call. Use isolated DB, not existing real-DB subprocess helper. |
| `test_karma_export_log_story_happy` | `caplog` + existing `assert_log_story`: entry → validated destinations → files complete → receipt complete/paired outcome; actor/entity/UUID/channel/counts present, no token/content. |
| `test_karma_export_log_story_reject` | Real path rejection and partial write failure: validation/error beat, receipt omitted, safe reason and completed-file count. No success/award-complete beat. |

The self-export exclusion belongs to S43, import exclusion to S44, full failed/unauthorized matrix to S46. S42 still routes through S36 so self-export cannot bypass eligibility.

Checkpoint, future implementation only:

```bash
pytest tests/integration/test_karma_exports.py -x
pytest tests/integration/test_karma_exports.py -k log_story -x
DJANGO_SETTINGS_MODULE=mimir.settings.acceptance python manage.py behave --simple --tags=@experts --name='^KARMA-EXPORT-01 ' docs/features/act-18-experts/karma-accrual.feature
```

Remove `@wip` only when the contract truly executes and passes. Later combined gate: `make test-at-experts`; zero selected tests is not success.

### E — Log story


| Where | Beat | Trigger | Must include |
|---|---|---|---|
| Facade export public method | entry | Invocation starts | tool, entity type/ID, operation UUID |
| Export destination validator | validation | Complete write plan checked | UUID, approved destination count; no content |
| Facade/service export | processing | Every requested write/sync completes | UUID, file count, `files_written=true` |
| Facade receipt dispatch / shared award service | exit | Receipt acknowledged/domain decision complete | UUID, `channel=export`, actor ID server-side, awarded/idempotent/ineligible outcome |
| Path validator/export writer | error | Invalid destination or filesystem failure | UUID, safe reason, completed-file count, `receipt_sent=false` |
| Receipt dispatch | error | Files completed but receipt remains unavailable | UUID, `files_written=true`, `receipt_status=failed`; no false rollback assertion |

Implement and prove these beats in the behavior commit. Avoid raw tokens, file bodies, private content and full sensitive paths in new log messages.

**Partial failure contract:** all requested canonical files, linked-rule writes, requested mirrors and requested ADE writes must complete before receipt. A preflight failure makes no writes. A later filesystem failure can leave earlier files; no receipt or award is created.

**Receipt transport failure contract:** retry only the receipt with its existing UUID. Never rerun the export as an automatic retry. On exhausted receipt failure, expose/log a distinct failure with files already written. An ambiguous remote commit is resolved by retrying that UUID through the idempotent S39/S36 path. No filesystem/remote-ledger atomicity is claimed.

### F — MCP surfaces


| Existing tool | Domain path | Write/HITL | Authentication |
|---|---|---|---|
| `export_workflow_to_local` | Existing bundle REST endpoint → actual facade files → S39 receipt → S36 shared consumption service | Local files + paired ledger; no additional HITL | Existing configured token |
| `export_playbook_to_local` | Same, including mirrors/ADE files | Same | Existing configured token |
| Legacy versions of both | Existing shared export services → S36 after all writes | Same | Existing `get_current_user()` context |

Reuse S39 exactly:

```python
_post_consumption_receipt(
    entity_type="workflow",  # or "playbook"
    entity_id=6202,
    event_identity=operation_uuid,
    channel="export",
)
```

Do not add `event_identity` or actor to public export tool schemas. Generate one UUID internally per invocation. S39 owns the sole DRF receipt endpoint and helper; S36 owns eligibility/atomic award persistence.

Legacy services generate one UUID per filesystem invocation and call S36 after completion. `user=None` preserves existing non-awarding service usage; authenticated legacy MCP already passes `user`. Playbook bundle generation uses the non-awarding workflow generator, so nested workflow files do not emit events. No modification to legacy `tools.py` is required under this design.

### G — Agent proofs


Not applicable. This changes explicit MCP exports and a domain receipt, not SAO §17’s bounded contribution-summary completion. No PRF row, ScriptedLLM fixture or agent frame should be invented.

### H — Graduation and implementation boundaries


No mockup graduates for this non-UI scenario. Real export files, ledger rows, actual registered clients and stdio are its observable evidence. Existing Experts prototypes remain design references.

Future footprint, subject to parent convergence:



The shared path module is a proposal, not an implemented API. `mimir/__init__.py` is empty; importing the module can remain standard-library-only. This avoids importing Django/domain services into the facade or duplicating confinement logic.

Each approved root is explicit: canonical root, conventional workflow sibling rules root, detected Cursor root, each requested additional root and requested ADE root. Retain existing workspace/bind guards for each root, validate *every resolved child*, reject absolute/parent traversal paths, and reject symlink escapes. Preflight the complete plan before the first write and revalidate the destination immediately before writing. This is ordinary local workspace confinement, not a guarantee against an adversarial concurrent filesystem replacement.

Slices after PIN-05 GO:

1. `docs(plan): hand off S42 export receipt contract` — documentation only, `Refs #N`.
2. `feat(exports): confine file destinations and credit completed exports` — red → green for both facade/legacy methods plus real T1/T2, confinement and log proofs, `Refs #N`.
3. `test(exports): certify registered export receipts and stdio` — T3, actual Behave binding/catalog graduation and final combined checkpoint, `Closes #N`.

Each slice needs its commit-linked issue update under the supplied GitHub rule. No worker posts one.

## Parent convergence

Authoritative acceptance source: `docs/features/act-18-experts/karma-accrual.feature:113`; 1 expanded case(s), primary layer `at`. Dependencies: S03, S30, S36, S39. The full scenario includes all composed journey/UAT obligations assigned in the consolidated contract. Shared Make/catalog registration belongs only to S03.

## Canonical feature execution graph

```yaml
feature_execution_graph:
  feature_ref: KARMA-EXPORT-01
  scenario: S42
  scenario_dependencies:
  - S03
  - S30
  - S36
  - S39
  nodes:
  - id: S42-N1-export-paths-and-domain
    title: Confine destinations and credit completed shared exports
    bpe: BPE-02
    depends_on: []
    footprint:
    - mcp_integration/facade/export_paths.py
    - methodology/services/playbook_export_service.py
    - methodology/services/workflow_export_service.py
    - tests/integration/test_karma_exports.py
    tests:
    - test_karma_export_service_t2_with_multiple_files_awards_one_pair
    log_story_rows:
    - shared_export:validation
    - shared_export:processing
    - shared_export:exit
    - shared_export:error
    gate:
      command: pytest tests/integration/test_karma_exports.py -k service_t2 -x
      log_story_command: pytest tests/integration/test_karma_exports.py -k log_story -x
    guidance_bundle:
      activity: BPE/BPE-02-Implement_Backend.md
      rules:
      - do-test-first
      - do-skeletons-first
      - do-not-mock-in-integration-tests
      - do-write-concise-methods
      - do-assert-log-story
    notes: 'Outer scenario prerequisites supply schema, persistence and shared consumption policy. Utility
      is pure stdlib and ships in the facade image.

      '
  - id: S42-N2-facade-receipts
    title: Record one receipt after every requested local file succeeds
    bpe: BPE-02
    depends_on:
    - S42-N1-export-paths-and-domain
    footprint:
    - mcp_integration/facade/tools_http.py
    - tests/integration/test_karma_exports.py
    tests:
    - test_karma_export_facade_t1_with_multiple_files_awards_one_pair
    - test_karma_export_with_mirrors_and_ade_files_awards_one_pair
    - test_karma_export_with_second_independent_call_creates_new_identity
    - test_karma_export_bundle_with_generation_only_creates_no_awards
    - test_karma_export_with_receipt_replay_preserves_single_pair
    - test_karma_export_with_escaping_folder_or_symlink_rejects_before_write
    - test_karma_export_with_partial_file_failure_creates_no_receipt
    - test_karma_export_log_story_happy
    - test_karma_export_log_story_reject
    log_story_rows:
    - facade_export:entry
    - facade_export:validation
    - facade_export:processing
    - export_receipt:exit
    - facade_export:error
    - export_receipt:error
    gate:
      command: pytest tests/integration/test_karma_exports.py -k 'not stdio' -x
      log_story_command: pytest tests/integration/test_karma_exports.py -k log_story -x
    guidance_bundle:
      activity: BPE/BPE-02-Implement_Backend.md
      rules:
      - do-test-first
      - do-not-mock-in-integration-tests
      - do-assert-log-story
    notes: 'Reuse S39 receipt endpoint/helper. Actual requested singular/plural ADE targets participate in
      preflight. Partial file failure sends no receipt; receipt retry reuses the invocation UUID without repeating
      file writes.

      '
  - id: S42-N3-acceptance-and-stdio
    title: Certify the exact export contract and protocol cleanliness
    bpe: BPE-04
    depends_on:
    - S42-N2-facade-receipts
    footprint:
    - docs/features/steps/experts_export_steps.py
    - tests/integration/test_karma_exports.py
    tests:
    - test_karma_export_stdio_t3_with_success_returns_clean_jsonrpc
    - KARMA-EXPORT-01
    gate:
      command: make test-experts-s42-at
      log_story_command: pytest tests/integration/test_karma_exports.py -k log_story -x
      acceptance_command: make test-at-karma-export
    guidance_bundle:
      activity: BPE/BPE-04-Implement_Feature_Acceptance_Tests.md
      rules:
      - do-test-first
      - do-not-mock-in-integration-tests
      - do-assert-log-story
    notes: 'Reuse S36''s exact shared total assertion binding. Scoped Make target runs manage.py behave --simple
      with acceptance settings, @experts and the exact KARMA-EXPORT-01 scenario name. Zero selected/skipped
      contracts do not pass.

      '
    mockup_graduation: not_applicable
    agent_proofs: []
  - id: S42-N4-definition-of-done
    title: Verify complete export behavior and minimal-image packaging
    bpe: BPE-06
    depends_on:
    - S42-N3-acceptance-and-stdio
    footprint: []
    tests:
    - test_karma_export_facade_t1_with_multiple_files_awards_one_pair
    - test_karma_export_service_t2_with_multiple_files_awards_one_pair
    - test_karma_export_stdio_t3_with_success_returns_clean_jsonrpc
    - test_karma_export_log_story_happy
    - test_karma_export_log_story_reject
    - KARMA-EXPORT-01
    gate:
      command: make test-experts-s42
      log_story_command: pytest tests/integration/test_karma_exports.py -k log_story -x
      acceptance_command: make test-at-karma-export
      package_build_command: docker build -f Dockerfile.mcp -t mimir-mcp:s42-proof .
      package_import_command: docker run --rm --entrypoint python mimir-mcp:s42-proof -m mcp_integration.facade.server
        --help
    guidance_bundle:
      activity: BPE/BPE-06-Check_Definition_of_Done.md
      rules:
      - do-test-first
      - do-not-mock-in-integration-tests
      - do-assert-log-story
    notes: 'All tests use the real isolated DB with explicit transactional pytest marker. Verify no new public
      export arguments, no nested detail receipts, one pair per complete invocation, confined files, and protocol-only
      stdout. Image build/import must actually pass; unavailable Docker is recorded as an unmet packaging gate,
      never claimed as verified.

      '
    mockup_graduation: not_applicable
    agent_proofs: []
```

## Lessons Learned

Existing export code already supplies the necessary real behavior, registration and authenticated bundles; adding another export endpoint would duplicate responsibility. Its top-level workspace guard does not establish confinement of every generated child, so confinement must be explicit in this slice. Filesystem completion and remote receipt persistence cannot be one transaction: partial writes award nothing, and receipt retries preserve identity without repeating the export. Existing facade subprocess tests’ real-database configuration is unsuitable for the isolated Cedar contract.

## Structural application evidence

`docs/experts-replay/pin-evidence/S42.json` records positive scaffold selection and deliberate NotImplementedError. Existing callable ASTs were preserved. Browser collection is not interaction certification.

## Actual structural footprint

`docs/experts-replay/pin-evidence/S42.json`, `docs/features/steps/experts_export_steps.py`, `docs/plans/iterations/experts/S42-karma-export-01.md`, `mcp_integration/facade/export_paths.py`, `mcp_integration/facade/tools_http.py`, `methodology/services/playbook_export_service.py`, `methodology/services/workflow_export_service.py`, `tests/integration/test_karma_exports.py`

Skeleton: `f16474cfae587db99d4845f2fa265dae24a597e6`; shared reconciliation: `39d598328d438d09723b6eb14574fbf92fab71c9`. Semantic and physical-file dependencies are recorded separately in the iteration manifest. Context-map line ranges record the workers’ inspection baseline; headers and the final scaffold remain authoritative.
