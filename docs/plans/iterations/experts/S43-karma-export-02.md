# S43: KARMA-EXPORT-02 Do not award self-export

This plan uses [the consolidated contract](../pin-convergence-20261123-experts.md). Its shared interfaces, ownership decisions and verification-layer mapping govern this scenario. Commands in the graph below are the canonical execution gates; implementation and test bodies remain unimplemented.

```yaml
scenario: S43
acceptance_id: KARMA-EXPORT-02
feature_file_path: docs/features/act-18-experts/karma-accrual.feature
feature_line: 120
primary_execution_layer: at
expanded_case_count: 1
dependencies:
- S42
system_dependencies: []
status: converged_plan_unapplied
source_report_sha256:
- 40cdb4ef4bc3b986d72a874ed8a1e55ead7b438837368c27fd86b9481e3b5a22
```

## A — Context map


| Verified source | Implementation significance |
|---|---|
| `docs/features/act-18-experts/karma-accrual.feature:140–143`; `test-data/experts/cedar-rfp-01.json:835–845` | Exact contract: Mike successfully exports his own workflow 6202; total remains 12450. |
| `mcp_integration/facade/tools_http.py:476–674`; `mcp_integration/facade/server.py:64–94,166–188` | Existing registered facade tools perform actual workflow/playbook writes, rule copies, mirrors and ADE outputs before returning. |
| `mcp_integration/tools.py:1154–1264,3674–3709`; `mcp_integration/context.py:15–43` | Existing legacy registration injects its real server user into both filesystem services. Exercise this context, not a fabricated actor argument. |
| `methodology/services/workflow_export_service.py:18–127,195–211`; `methodology/services/playbook_export_service.py:30–142,289–332` | Real filesystem exporters and output formats; workflow metadata contains a dynamic export timestamp. |
| `docs/architecture/SAO.md:3863–3895`; `test-data/experts/cedar-rfp-01.json:420–479,1104–1113` | Shared self-exclusion; Mike owns playbook 6201/workflow 6202/activity 6203. GUI copies remain 47, a subset of 470 author-consumption events. |

Read replay AGENTS/CLAUDE, orient roster, live PIN/BPE/rule snapshots, ownership convergence, both S42 reports and S39 receipt contract. Existing registrations and writer bodies were inspected; no execution was performed.

## B — Do not do


- Do not create a second award writer, receipt helper, MCP server or self-export policy. S36 owns self-exclusion; S30 persistence; S39 `_post_consumption_receipt`; S42 complete-export wiring.
- Do not suppress export or omit its receipt because actor equals author. Finish the real export, then let the shared domain service return its self-consumption outcome.
- Do not pass a failed, unauthorized, empty or partially written export off as proof of successful self-exclusion.
- Do not check only Mike’s total: another recipient or category could change while that total stays constant.
- Do not award nested detail reads, generated files, rule copies, mirrors or ADE outputs.
- Do not mock HTTP, filesystem, tools, services, DB, tokens or time. `tmp_path` and `TemporaryDirectory` provide real isolated filesystem storage.
- Do not modify production code, permissions, seed, migrations, browser/UI, agent orchestration or export signatures in S43.
- Do not relocate S42’s standard-library guard from `mcp_integration/facade/export_paths.py`; `Dockerfile.mcp:21–23` copies only the facade package.

## C — Applicable SAO sections


**Experts & Karma delivery architecture → Awards, projections and transaction boundaries; Test strategy**; **MCP Interface (FastMCP)**; **MCP Integration: Implementation Patterns → Service Layer + MCP Tools; stdio Pollution Prevention**; **Security & Access Control**; **REST API Specification → Authentication**; **Request ID Logging**.

S43 certifies S42/S36 behavior. Any defect requiring a production change returns to its owning scenario and footprint rather than acquiring a competing S43 implementation.

## D — Tests to create and exact assertions


Append tests to S42’s `tests/integration/test_karma_exports.py`, preserving its module-level `pytestmark = pytest.mark.django_db(transaction=True)`. Each parameter independently restores the real S03 Cedar baseline.

All successful-export tests must first prove:

1. The source is Mike’s actual public released workflow 6202 or playbook 6201, using the Cedar adapter and real ORM relationships.
2. The real call succeeds with its established result shape and `status="exported"`; no tool error or exception is accepted.
3. Every expected file exists within authorized roots. Compare the complete relative-file set and every file’s bytes/content, including workflow metadata and activity 6203’s actual guidance.
4. Playbook cases include canonical metadata, workflows, rules, agents, skills and artifacts present in the actual bundle, plus requested mirrors and ADE outputs. Verify `.md`/`.mdc` formats, canonical stored rule flags, requested apply-on frontmatter and returned inline Claude/Copilot content. Assert nonempty relevant fixture collections; vacuous loops are insufficient.
5. Only after output verification, compare the complete global ledger snapshot, all user totals, category/source projections and original event identities/timestamps. There are no new rows, updates or deletes; no export or nested `mcp_detail` awards. Mike remains 12450, Development 12450, and eligible GUI-copy count remains 47.

| Planned test | Additional proof |
|---|---|
| `test_self_export_facade_t1_with_owned_content_writes_files_without_awards` | Parameterize both registered export tools. Real `Client(transport=_build_mcp())`, configured real HTTP client, `live_server` and Mike’s DRF token; discover schema and call tools. Playbook case requests a mirror and Cursor/Devin ADE writes, including singular/plural argument merging. |
| `test_self_export_legacy_t1_with_owned_content_writes_files_without_awards` | Both tools through actual `initialize_mcp()` registration and real `set_current_user(Mike)` context; clear context afterward. Never invoke only an undecorated wrapper and call that registration proof. |
| `test_self_export_service_t2_with_owned_content_writes_files_without_awards` | Both real filesystem service methods with Mike as authenticated user. No nested-workflow award duplication in whole-playbook export. |
| `test_self_export_log_story_happy` | Both transport paths; `caplog` plus `assert_log_story` prove successful files → shared eligibility branch `self_consumption` → zero-created exit. No error/failure path substitutes. |
| `test_self_export_stdio_t3_with_owned_content_returns_clean_jsonrpc` | Parameterize facade/legacy entrypoint × workflow/playbook. Actual initialize, tools/list, tools/call, real files and unchanged DB; stdout parses exclusively as protocol JSON. |

For facade T1, attach a real httpx response event hook to capture the actual successful bundle response without replacing transport or responses. Compare written bytes with that captured payload. This avoids regenerating timestamped content and assuming the minute did not change. For direct/legacy/subprocess paths, independently validate the documented timestamp against invocation bounds, reconstruct only that timestamp field in expected metadata, then compare the entire byte sequence. Never broadly strip metadata or skip files.

T3 facade uses the real isolated HTTP server. Legacy subprocess uses a separate migrated temporary SQLite DB populated through the real Cedar adapter, following the isolation pattern at `tests/integration/test_mcp_e2e_all_tools.py:41–76`; never use ambient `mimir.db`.

AT owns exactly these new phrases:

- `Given Mike has a valid MCP token`
- `When he exports his own workflow 6202`
- `Then his total remains 12450`

Reuse S03’s baseline binding. The When executes the real filesystem workflow service with authenticated Mike and actual temporary files; the Then verifies successful complete output before global unchanged-state assertions. AT proves the domain/filesystem contract; T1/T3 separately prove actual MCP registration and transport.

Future commands, not run:

```text
pytest tests/integration/test_karma_exports.py -k self_export -x
pytest tests/integration/test_karma_exports.py -k self_export_log_story -x
make test-at-karma-self-export
```

The Make target runs the existing acceptance runner with acceptance settings, `--simple --tags=@experts --name='^KARMA-EXPORT-02 Do not award self-export$'` and the exact feature path. Explicit CLI selection overrides the feature/config WIP exclusion. Require one executed scenario, three passed steps, no undefined/skipped steps; zero selection fails completion.

## E — Log story


No new S43 production logs. Assert the logs supplied by S42/S36 through real successful exports.

| Where | Beat | Trigger | Must include |
|---|---|---|---|
| Existing facade/shared export completion | processing | All requested outputs completed | operation identity, entity kind/ID, positive completed-file count, `files_written=true` |
| `KarmaService.award_successful_consumption` | branch | Authenticated actor resolves to author | actor/playbook/author IDs, `channel=export`, `reason=self_consumption` |
| Same/shared receipt completion | exit | Successful self-export receipt resolved | same identity, `created_count=0`, ineligible/self outcome |

Prove ordering and identity continuity; no award-created or export-failure beat. New expected log fields exclude tokens, email, content and sensitive absolute paths. No reject-path log test is declared because this contract is a successful export with an eligibility branch; failed-export certification belongs to S46.

## F — MCP tools


| Existing tool | Existing route/domain path | Write/HITL/auth |
|---|---|---|
| `export_workflow_to_local` | Workflow bundle → complete real files → S39 receipt → S36 | Filesystem/receipt write; no HITL; configured token or legacy server context |
| `export_playbook_to_local` | Playbook bundle → complete canonical/mirror/ADE output → same shared policy | Same |

No new registration or initialization is required. T1 covers each actual registration; T2 shared filesystem/domain integration; T3 both real stdio entrypoints.

## G — Agent proofs


Not applicable. No LLM call, CAP, PRF, ScriptedLLM or ToolExecutor change; `agent_proofs: []`. MCP protocol proofs are not agent proofs.

## H — Mockup graduation


Not applicable. This is protocol/filesystem/domain certification; no browser, template or mockup transition. S43 adds no journey/UAT contract.

## Parent convergence

Authoritative acceptance source: `docs/features/act-18-experts/karma-accrual.feature:120`; 1 expanded case(s), primary layer `at`. Dependencies: S42. The full scenario includes all composed journey/UAT obligations assigned in the consolidated contract. Shared Make/catalog registration belongs only to S03.

## Canonical feature execution graph

```yaml
feature_execution_graph:
  feature_ref: KARMA-EXPORT-02
  scenario: S43
  scenario_dependencies:
  - S42
  nodes:
  - id: S43-N1-shared-certification
    title: Certify successful self-export through services and registrations
    bpe: BPE-02
    depends_on: []
    footprint:
    - tests/integration/test_karma_exports.py
    - tests/support/experts_exports.py
    tests:
    - test_self_export_facade_t1_with_owned_content_writes_files_without_awards
    - test_self_export_legacy_t1_with_owned_content_writes_files_without_awards
    - test_self_export_service_t2_with_owned_content_writes_files_without_awards
    - test_self_export_log_story_happy
    log_story_rows:
    - export_completion:processing
    - successful_consumption:branch
    - successful_consumption:exit
    gate:
      command: pytest tests/integration/test_karma_exports.py -k 'self_export and not stdio' -x
      log_story_command: pytest tests/integration/test_karma_exports.py -k self_export_log_story -x
    guidance_bundle:
      activity: BPE/BPE-02-Implement_Backend.md
      rules:
      - do-test-first
      - do-skeletons-first
      - do-not-mock-in-integration-tests
      - do-assert-log-story
      - do-write-concise-methods
    notes: Certification only; no new production writer.
  - id: S43-N2-acceptance
    title: Execute exact self-export living specification
    bpe: BPE-04
    depends_on:
    - S43-N1-shared-certification
    footprint:
    - docs/features/steps/experts_export_steps.py
    tests:
    - KARMA-EXPORT-02
    gate:
      command: make test-experts-s43-at
    guidance_bundle:
      activity: BPE/BPE-04-Implement_Feature_Acceptance_Tests.md
      rules:
      - do-test-first
      - do-not-mock-in-integration-tests
      - pytest
    notes: Exactly one executed scenario/three passed steps; no zero/skipped success.
  - id: S43-N3-protocol
    title: Certify both real stdio entrypoints
    bpe: BPE-04
    depends_on:
    - S43-N2-acceptance
    footprint:
    - tests/integration/test_karma_exports.py
    tests:
    - test_self_export_stdio_t3_with_owned_content_returns_clean_jsonrpc
    gate:
      command: pytest tests/integration/test_karma_exports.py -k 'self_export and stdio' -x
    guidance_bundle:
      activity: BPE/BPE-04-Implement_Feature_Acceptance_Tests.md
      rules:
      - do-test-first
      - do-not-mock-in-integration-tests
      - pytest
    notes: Four real combinations; isolated legacy DB and facade HTTP; complete files before ledger assertions.
  - id: S43-N4-definition-of-done
    title: Require conjunctive successful-export certification
    bpe: BPE-06
    depends_on:
    - S43-N3-protocol
    footprint: []
    tests:
    - KARMA-EXPORT-02
    - self_export_t1_t2_t3_and_log_story
    gate:
      command: make test-experts-s43
      log_story_command: pytest tests/integration/test_karma_exports.py -k self_export_log_story -x
      acceptance_command: make test-at-karma-self-export
    guidance_bundle:
      activity: BPE/BPE-06-Check_Definition_of_Done.md
      rules:
      - do-test-first
      - do-not-mock-in-integration-tests
      - do-assert-log-story
      - pytest
    notes: All gates must pass; S42 complete-output/packaging gates remain prerequisites. No agent/browser gate.
    mockup_graduation: not_applicable
    agent_proofs: []
```

## Lessons Learned

A zero-award assertion is incomplete without first proving actual successful output. Whole-ledger equality catches accidental awards to other recipients. Timestamped metadata requires an explicit byte-verification strategy; repeated bundle generation is not a reliable byte oracle. S42’s complete-output receipt boundary and S36’s shared exclusion keep this scenario certification-only.
