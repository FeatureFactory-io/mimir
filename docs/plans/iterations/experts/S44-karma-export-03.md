# S44: KARMA-EXPORT-03 Do not award import

This plan uses [the consolidated contract](../pin-convergence-20261123-experts.md). Its shared interfaces, ownership decisions and verification-layer mapping govern this scenario. Commands in the graph below are the canonical execution gates; implementation and test bodies remain unimplemented.

```yaml
scenario: S44
acceptance_id: KARMA-EXPORT-03
feature_file_path: docs/features/act-18-experts/karma-accrual.feature
feature_line: 125
primary_execution_layer: at
expanded_case_count: 1
dependencies:
- S03
- S23
- S39
- S41
- S42
system_dependencies: []
status: converged_plan_unapplied
source_report_sha256:
- a5c3f04b1bad5c695489d64f8825d5ae81f2261f2c71094f375c96b16bf9266d
```

## A — Verified context map


| File:lines | Implementor context |
|---|---|
| `docs/features/act-18-experts/karma-accrual.feature:145–148`; `test-data/experts/cedar-rfp-01.json:847–859` | Successful Maria import leaves Maria 8200 and Mike 12450; independently restore Cedar. |
| `mcp_integration/facade/tools_http.py:677–703`; `mcp_integration/facade/server.py:64–95` | Actual registered facade import validates local-server/workspace support, then POSTs the source path to the existing REST endpoint. |
| `methodology/api/viewsets.py:792–818`; `methodology/services/workflow_import_service.py:17–73,150–203` | Import generates a real change protocol against an existing workflow. The API does not apply changes, even if `auto_apply` was forwarded. |
| `mcp_integration/tools.py:1267–1310,3674–3712` | Existing legacy registration calls the same import service and additionally applies draft changes when `auto_apply=True`. |
| `tests/integration/test_workflow_export_import_mcp.py:177–213,255–280`; `tests/integration/test_mcp_facade.py:162–179` | Existing real-file service examples are reusable references; existing facade server helper deliberately selects the development DB and must not supply this certification’s lifecycle. |

Also verified: API import overrides object permissions to `[IsAuthenticated]`, but `self.get_object()` still uses the accessible-playbook queryset (`viewsets.py:697–708,792–801`). The legacy wrapper obtains user context but does not pass an actor into import service. Preserve these existing behaviors; S44 does not certify stronger ownership enforcement than exists.

## B — Do not do


- Do not turn successful import into an authorization rejection to prove zero awards.
- Do not add an import receipt, consumption event, runtime service, new public tool, permission change or import-semantics fix.
- Do not claim facade import applied activities: its current API is protocol generation.
- Do not call Maria’s awarding export of Mike’s content during setup.
- Do not accept actor, recipient, points or category as import arguments.
- Do not release the target draft, accept a PIP, regenerate summaries or replay historical hooks.
- Do not replace existing working bodies with raising stubs.
- Do not use ambient development/production databases, HTTP mocks or patched domain services.

## C — Applicable SAO headings


- **Experts & Karma delivery architecture — planned delta / Awards, projections and transaction boundaries:** import awards nothing; historical import does not invoke fresh hooks.
- **Test strategy for this delta:** isolated real DB; positive executed acceptance count.
- **MCP Integration: Implementation Patterns / Architecture Decision: Service Layer + MCP Tools:** retain both existing transport paths and shared service.
- **Critical Discovery: stdio Pollution Prevention:** protocol stdout stays clean.
- **Security & Access Control / FOB:** preserve actual access boundaries.
- **17. AI Agent Architecture — Experts contribution summary:** import is not the normal PIP submission/resubmission summary trigger.

## D — Certification design and exact assertions


Prepare real files under `tmp_path`. Restore Cedar using S03’s `load_cedar_baseline()`. Create a Maria-owned **draft** playbook/workflow through existing `PlaybookService`/`WorkflowService`.

Prepare exported source through the existing filesystem exporter **as Mike exporting his own workflow 6202**. Assert setup creates no awards before capturing the operation baseline. Add one valid, ID-free activity Markdown file using actual exported Cedar guidance and an explicit new activity name. This is fixture preparation, not a product import or release. Existing import ignores foreign activity IDs that are absent from its target workflow, so the ID-free addition ensures a real positive diff.

Use the source directory’s abbreviation for the new draft workflow: current import can otherwise change abbreviation even in protocol-only mode. Do not silently claim import is entirely DB-read-only.

Capture **all** ledger rows, all ExpertProfile rows, and all AgentInteraction rows after setup. S23 dependency supplies interaction persistence for the no-generation assertion. Compare complete ordered row snapshots after the import, including original event timestamps and profile summary metadata. Independently aggregate Maria/Mike points from the actual ledger.

| Planned test | Exact assertions |
|---|---|
| `test_import_service_t2_with_exported_files_generates_protocol_without_awards` | Real `WorkflowImportService.import_workflow_from_markdown`; correct target workflow; `status=changes_detected`; positive `changes_count`; new activity identified in actual `_Upload_Protocol.md`; target remains draft; default import does not apply the new activity; all captured Experts state unchanged; totals 8200/12450. |
| `test_import_facade_t1_with_owned_draft_returns_protocol_without_awards` | `Client(transport=_build_mcp())` discovers and calls the actual registered import tool. Configure actual facade client with Maria’s real token and isolated `live_server`; real HTTP request and files. Same positive protocol and global invariants. No public `get_*` calls during preparation that could earn detail points. Close/reset actual client configuration afterward. |
| `test_import_legacy_registration_with_owned_draft_preserves_zero_awards` | Real `initialize_mcp()` registration through FastMCP Client, Maria context set/cleared using existing context API. Parameterize `auto_apply=False/True`: false produces protocol without application; true returns `auto_applied=True` and real applied new activity/guidance. Both preserve draft status and global Experts snapshots. |
| `test_import_facade_with_auto_apply_flag_preserves_existing_protocol_only_semantics` | Actual facade call with true flag still returns protocol-only response; no fabricated `auto_applied` claim, no added activity and no award. Explicit compatibility assertion, not endorsement of API parity. |
| `test_import_stdio_t3_with_success_returns_clean_jsonrpc_without_awards` | Actual facade subprocess pointed exclusively at isolated live HTTP backend/token/source directory. Initialize, tools/list, tools/call; registered schema and successful protocol result; real protocol file; every stdout protocol message parses as JSON-RPC; global snapshots/totals unchanged. No development-server fixture. |
| `test_import_with_missing_source_rejects_without_awards` | Existing real workspace/import rejection; no protocol, no new target activity, no ledger/profile/interaction change. Secondary negative proof; never substitutes for successful import. |
| `test_import_log_story_happy` | Actual captured existing facade/service import logs identify selected workflow and positive detected changes/protocol completion; no token or actual guidance body. |
| `test_import_acceptance_with_exact_contract_runs_one_scenario` | Run scoped Make target; assert successful exit, exactly one executed `KARMA-EXPORT-03` scenario and no failed/undefined/skipped selected scenario. Parse actual captured summary/report, never accept exit zero alone. |

Future checkpoints:

```bash
pytest --ds=mimir.settings.acceptance tests/integration/test_karma_imports.py -x
pytest --ds=mimir.settings.acceptance tests/integration/test_karma_imports.py -k log_story -x
make test-at-karma-import
```

The Make target runs the existing acceptance runner with `--simple --tags=@experts --name='^KARMA-EXPORT-03 '` and exactly `docs/features/act-18-experts/karma-accrual.feature`. Explicit selection overrides feature-level WIP exclusion for this contract. Do not remove WIP or claim aggregate completion merely because this one passes.

## E — Existing log story to certify


No production logging changes proposed. Assert existing INFO messages through `tests/support/log_story.py::assert_log_story`, mapping semantic beats to actual existing message fragments.

| Where substring | Beat | Trigger | Required fragments |
|---|---|---|---|
| `HTTP Tool: import_workflow_from_local` | entry | Facade invocation | `workflow=<actual target ID>` |
| `Importing workflow` | entry | Shared service invoked | Actual target ID |
| `Detected changes:` | processing | Real files parsed | `total`, positive expected change count |
| `Generated upload protocol at` | exit | Protocol write completed | `_Upload_Protocol.md` |

Capture only the import window, excluding setup exports. Existing code has no structured rejection beat for the missing-source case, so do not invent one or introduce production logging solely for certification. The negative test asserts failure and absence of protocol-success evidence.

## F — MCP surfaces


| Existing tool/surface | Service | Writes / HITL | Identity |
|---|---|---|---|
| Facade `import_workflow_from_local` | Existing REST import → `WorkflowImportService` | Protocol file; existing abbreviation behavior; no new HITL | Existing configured DRF token |
| Legacy same name | Same import service; existing optional `WorkflowProtocolService.apply_upload_protocol` | Protocol; draft application only when requested; no new HITL | Existing server user context |

No new registration or schema. Verify both current registrations. T1 real facade/HTTP and legacy Client, T2 real service/DB/files, T3 real facade subprocess apply.

## G — Agent proofs


Not applicable: deterministic import does not change an agent capability or invoke summary generation. `agent_proofs: []`; no ScriptedLLM or new PRF. Persisted summary/interaction equality proves the negative domain consequence without inventing an agent run.

## H — Mockup graduation


Not applicable. No UI, production template, browser interaction or mockup graduation.

## Parent convergence

Authoritative acceptance source: `docs/features/act-18-experts/karma-accrual.feature:125`; 1 expanded case(s), primary layer `at`. Dependencies: S03, S23, S39, S41, S42. The full scenario includes all composed journey/UAT obligations assigned in the consolidated contract. Shared Make/catalog registration belongs only to S03.

## Canonical feature execution graph

```yaml
feature_execution_graph:
  feature_ref: KARMA-EXPORT-03
  scenario: S44
  scenario_dependencies:
  - S03
  - S23
  - S39
  - S41
  - S42
  nodes:
  - id: S44-N1-positive-import-certification
    title: Certify actual service and both registered import paths
    bpe: BPE-02
    depends_on: []
    footprint:
    - tests/integration/test_karma_imports.py
    - tests/support/experts_imports.py
    tests:
    - test_import_service_t2_with_exported_files_generates_protocol_without_awards
    - test_import_facade_t1_with_owned_draft_returns_protocol_without_awards
    - test_import_legacy_registration_with_owned_draft_preserves_zero_awards
    - test_import_facade_with_auto_apply_flag_preserves_existing_protocol_only_semantics
    - test_import_with_missing_source_rejects_without_awards
    - test_import_log_story_happy
    gate:
      command: pytest --ds=mimir.settings.acceptance tests/integration/test_karma_imports.py -k 'not stdio and not
        acceptance' -x
      log_story_command: pytest --ds=mimir.settings.acceptance tests/integration/test_karma_imports.py -k log_story
        -x
    guidance_bundle:
      activity: BPE/BPE-02-Implement_Backend.md
      rules:
      - do-skeletons-first
      - do-test-first
      - do-not-mock-in-integration-tests
      - do-assert-log-story
    notes: Certification only; no production import modifications.
  - id: S44-N2-exact-acceptance
    title: Bind the import When and prove one exact acceptance execution
    bpe: BPE-04
    depends_on:
    - S44-N1-positive-import-certification
    footprint:
    - docs/features/steps/experts_import_steps.py
    - tests/integration/test_karma_imports.py
    tests:
    - test_import_acceptance_with_exact_contract_runs_one_scenario
    - KARMA-EXPORT-03
    gate:
      command: make test-experts-s44-at
      acceptance_command: make test-at-karma-import
    guidance_bundle:
      activity: BPE/BPE-04-Implement_Feature_Acceptance_Tests.md
      rules:
      - do-test-first
      - do-not-mock-in-integration-tests
    notes: Reuse S39 Given and S41 Then; require exactly one passed contract.
  - id: S44-N3-protocol
    title: Certify actual stdio facade import
    bpe: BPE-04
    depends_on:
    - S44-N2-exact-acceptance
    footprint:
    - tests/integration/test_karma_imports.py
    tests:
    - test_import_stdio_t3_with_success_returns_clean_jsonrpc_without_awards
    gate:
      command: pytest --ds=mimir.settings.acceptance tests/integration/test_karma_imports.py -k stdio -x
    guidance_bundle:
      activity: BPE/BPE-04-Implement_Feature_Acceptance_Tests.md
      rules:
      - do-test-first
      - do-not-mock-in-integration-tests
    notes: Protocol certification substitutes no browser claim; no UI involved.
  - id: S44-N4-dod
    title: Require every import certification and observability gate
    bpe: BPE-06
    depends_on:
    - S44-N3-protocol
    footprint: []
    gate:
      command: make test-experts-s44
      log_story_command: pytest --ds=mimir.settings.acceptance tests/integration/test_karma_imports.py -k log_story
        -x
      acceptance_command: make test-at-karma-import
    guidance_bundle:
      activity: BPE/BPE-06-Check_Definition_of_Done.md
      rules:
      - do-test-first
      - do-not-mock-in-integration-tests
      - do-assert-log-story
    notes: Conjunctive T1/T2/legacy/T3/log/positive-count AT; no skipped completion.
    agent_proofs: []
    mockup_graduation: not_applicable
```

## Lessons Learned

PIN-04/05 owns concrete issue/handoff publication and GO. Later certification slices commit with `Refs #N`, paired approved issue updates, and final green certification with `Closes #N`. No time estimate, merge or release authority.

1. Import means existing-target protocol generation; it does not inherently create a new playbook. Create the authorized draft through existing APIs during setup and prove actual protocol contents.
2. Self-export setup prevents accidental +5/+5 contamination. Capture the operation baseline only after checking setup preserved Cedar totals.
3. Facade and legacy `auto_apply` behavior differs today. Record that accurately; S44 requires no new runtime behavior.
4. Current service can update workflow abbreviation during import. Matching the prepared directory and target abbreviation avoids unrelated mutation without hiding it.
5. Global immutable snapshots are stronger than Maria-only totals: they detect accidental Mike/unrelated awards, timestamp changes and summary regeneration.
6. If future proofs expose a production regression, report its concrete evidence to the parent before adding production files or changing import semantics.
