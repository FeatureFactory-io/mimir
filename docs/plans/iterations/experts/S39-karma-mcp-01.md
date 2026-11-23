# S39: KARMA-MCP-01 Credit eligible authenticated detail reads

This plan uses [the consolidated contract](../pin-convergence-20261123-experts.md). Its shared interfaces, ownership decisions and verification-layer mapping govern this scenario. Commands in the graph below are the canonical execution gates; implementation and test bodies remain unimplemented.

```yaml
scenario: S39
acceptance_id: KARMA-MCP-01
feature_file_path: docs/features/act-18-experts/karma-accrual.feature
feature_line: 68
primary_execution_layer: at
expanded_case_count: 9
dependencies:
- S03
- S30
- S36
system_dependencies: []
status: converged_plan_unapplied
source_report_sha256:
- ae4bbc99c0c7ae1f119a1a4323c2a80d9b51da710036b91a3ae729f557f91460
- 3b0776f1d04d7da3ca7c3411cb22a88f2db7b0907d43fc7fe548045f9b58d2d9
```

## A — Context map


| Verified source | Relevance |
|---|---|
| `docs/features/act-18-experts/karma-accrual.feature:88–106` | Exact nine eligible examples; Mike’s existing staff permission covers the PIP case. |
| `mcp_integration/facade/server.py:64–143` | All nine tools already registered by `_build_mcp`; retain this server. |
| `mcp_integration/facade/tools_http.py:69–101,1402–1411` | Existing authorized HTTP detail retrieval and return/error contracts. |
| `methodology/services/pip_service.py:513–535` | PIP reads require creator or staff; target-playbook access alone is insufficient. |
| `tests/integration/test_mcp_facade.py:49–205` | Real facade subprocess/HTTP patterns; its server currently selects a development DB, so reuse the protocol pattern with isolated pytest infrastructure. |

Read `AGENTS.md`, `CLAUDE.md`, guidance/ownership/GitHub-rule snapshots, Act18/Cedar, SAO delta, real REST permissions/viewsets, service getters, legacy wrappers and both existing entrypoints.

## B — Do not do


- No second MCP server, new registered tool, new authorization policy, provider, queue or agent machinery.
- No awarding in ordinary REST detail GETs, list calls or import paths.
- No facade ORM/business rules, caller-supplied actor/recipient/category/points/timestamp, or inferred author from response JSON.
- No staff promotion for Maria. PIP author credit goes to its target playbook author.
- No replacement of existing method bodies with raising stubs.
- No real DB/server startup, tests, mutations or commits during PIN.

## C — Applicable SAO headings


`FOB-Centric Architecture`; `MCP Interface (FastMCP)`; `REST API Specification → Authentication/API Design Principles`; `Security & Access Control`; `MCP Integration: Implementation Patterns → stdio Pollution Prevention`; `Experts & Karma delivery architecture → Awards, projections and transaction boundaries/Test strategy`.

SAO §17 is unaffected: no model calls or agent control plane.

Implementation contract:

1. Extend the **existing nine registered tools**, backwards compatibly, with optional `event_identity: str | None = None`; preserve current arguments and response shapes.
2. Validate or generate one UUID per intentional invocation. Retain it across receipt retries; supplied UUID permits whole-call retry.
3. Complete the existing authorized read and decode actual content first.
4. Facade sends token-authenticated `POST /api/consumption-receipts/` with `{entity_type, entity_id, event_identity, channel:"mcp_detail"}`.
5. Django derives actor from `request.user`, accepts only `mcp_detail|export` here, and delegates to S36’s shared `KarmaService.award_successful_consumption`.
6. S36 resolves current entity, permission, playbook/category and self-exclusions again; S30 persists the atomic pair through S03’s ledger. Preserve `event_channel`, immutable integer source snapshots, stable timestamp and UUID on retry.
7. Existing `manage.py mcp_server` wrappers use the same service after successful serialization; facade remains HTTP-only.
8. `get_playbook` history/version options still create one consumption event, never one per nested object.

Receipt retry ambiguity must retain the original identity: a lost response can mean the pair already committed. Never manufacture another UUID during that retry. Retrieval success denotes successful authorized fetch/decoding at the MCP boundary; it cannot prove the assistant ultimately displayed the payload.

Nine independent baseline cases:

| Tool | Consumer | Target author | Expected totals |
|---|---|---|---|
| `get_playbook` | Maria | Mike | 8205 / 12455 |
| `get_workflow` | Maria | Mike | 8205 / 12455 |
| `get_phase` | Maria | Mike | 8205 / 12455 |
| `get_activity` | Maria | Mike | 8205 / 12455 |
| `get_skill` | Maria | Mike | 8205 / 12455 |
| `get_rule` | Maria | Mike | 8205 / 12455 |
| `get_agent` | Maria | Mike | 8205 / 12455 |
| `get_artifact` | Maria | Mike | 8205 / 12455 |
| `get_pip` | Mike, already staff | Hana | 12455 / 5805; Maria remains 8200 |

PIP fixture: `HIST-MARIA-DESIGN-01`, target playbook `6106`; resolve its real imported PIP PK through the Cedar adapter. Other IDs likewise come from the real fixture, not fabricated ORM assumptions.

## D — Tests to create


All new test bodies remain raising stubs until GO.

| Test | Proof |
|---|---|
| `test_mcp_detail_with_authorized_fixture_returns_content_and_pair` — T1, nine parameters | `fastmcp.Client` against real `_build_mcp()` → real HTTP Django `live_server`, real token and transactional DB; actual content plus exact totals/channel/category and pair count. |
| `test_consumption_service_with_authorized_fixture_records_pair` — T2, nine parameters | Direct shared service and real DB; current permission resolution, source snapshots, atomic learner/author pair. |
| `test_mcp_detail_with_legacy_registration_returns_content_and_pair` — nine parameters | Real `initialize_mcp()` registration and user context; existing wrappers reach shared service and preserve content. |
| `test_mcp_detail_with_stdio_transport_returns_clean_jsonrpc` — T3, nine parameters | Real facade subprocess against real HTTP Django server; initialization, schema, tool call, actual content and pair; stdout contains only protocol JSON. |
| `test_detail_rest_get_with_authorized_token_does_not_award` — nine parameters | Bare authenticated REST GET remains award-free. |
| `test_consumption_receipt_with_invalid_request_rejects_without_awards` | Missing/bad token, invalid UUID/type/ID/channel, `gui_copy` on token endpoint, missing entity, denied private/PIP reads: no pair. No raw private body in response/log. |
| `test_consumption_receipt_with_retry_preserves_awards_and_timestamp` | Stable UUID retries retain exactly two rows and original timestamp; mismatched identity reuse rejected, later intentional UUID adds a distinct pair. |
| `test_mcp_detail_with_history_options_records_one_pair` | Current/history/version success remains compatible; nonexistent version never posts a successful receipt. |
| `test_mcp_detail_log_story_happy` | `caplog` + existing `assert_log_story`: authorized read → receipt → atomic result, including Design PIP case. |
| `test_mcp_detail_log_story_reject` | Invalid/denied retrieval and receipt rejection never emit success beats or leak credentials/private content. |

No HTTP/domain mocks. Use pytest-django `live_server` plus transactional DB for T1; facade subprocess has no DB and can use the same live HTTP server. Legacy subprocess coverage must use a separate temporary migrated SQLite DB following the isolation pattern in `test_mcp_e2e_all_tools.py`, never its ambient development DB.

AT: S39 owns the five new outline phrases below; baseline phrase remains S03-owned. Bind the actual detail endpoint and explicit receipt through the real Django test client; T1 independently certifies the facade/network bridge.

Checkpoint:

```text
pytest tests/integration/test_karma_mcp.py -x
pytest tests/integration/test_karma_mcp.py -k log_story -x
```

Named AT certification, after all nine bindings are implemented:

```text
DJANGO_SETTINGS_MODULE=mimir.settings.acceptance .venv/bin/python manage.py behave --simple --tags=@experts --name='KARMA-MCP-01' docs/features/act-18-experts/karma-accrual.feature
```

The full outline must execute nine cases. Zero/skipped cases are not completion evidence.

## E — Log story


| Where | Beat | Trigger | Must include |
|---|---|---|---|
| `_complete_mcp_detail` | entry | Authorized payload decoded | `tool`, `entity_type`, `entity_id`, `event_identity`, `channel=mcp_detail` |
| `ConsumptionReceiptView.post` | validation | Authenticated receipt accepted | `actor_id`, `entity_type`, `entity_id`, `event_identity`, `channel` |
| `KarmaService.award_successful_consumption` | branch | Revalidated eligibility | `actor_id`, `playbook_id`, `author_id`, `category`, eligibility reason |
| Same | exit | New pair or duplicate | `event_identity`, `created_count=2` or `duplicate`, retained event timestamp |
| Receipt/read boundary | branch/error | Denied/invalid operation | safe reason, object identifiers, no award success |

S36 owns shared-service log implementation; S39 asserts its beats through both MCP paths. No token, email, prompt or private payload logging.

## F — MCP surface


| Existing tool | Existing detail route | Award service |
|---|---|---|
| `get_playbook` | `/api/playbooks/{id}/` | Shared successful-consumption service |
| `get_workflow` | `/api/workflows/{id}/` | Same |
| `get_phase` | `/api/phases/{id}/` | Same |
| `get_activity` | `/api/activities/{id}/` | Same |
| `get_skill` | `/api/skills/{id}/` | Same |
| `get_rule` | `/api/rules/{id}/` | Same |
| `get_agent` | `/api/agents/{id}/` | Same |
| `get_artifact` | `/api/artifacts/{id}/` | Same |
| `get_pip` | `/api/pips/{id}/` | Same; existing creator/staff gate |

These reads gain a receipt write, with no HITL requirement. Auth injection remains configured facade token / legacy server context. Do not accept `user_id` as a tool argument.

S39 owns one DRF receipt endpoint and the common facade receipt helper. S42 calls that helper with `channel="export"` only after actual local writes.

## G — Agent proofs


Not applicable. No provider, ScriptedLLM, ToolExecutor, CAP or PRF change.

## H — Mockup graduation


Not applicable: protocol/service behavior only. No UI/template/browser journey is introduced. Existing Experts UI certifications remain with their owning scenarios.

## Parent convergence

Authoritative acceptance source: `docs/features/act-18-experts/karma-accrual.feature:68`; 9 expanded case(s), primary layer `at`. Dependencies: S03, S30, S36. The full scenario includes all composed journey/UAT obligations assigned in the consolidated contract. Shared Make/catalog registration belongs only to S03.

## Canonical feature execution graph

```yaml
feature_execution_graph:
  feature_ref: KARMA-MCP-01
  nodes:
  - id: S39-N1-receipt
    title: Token receipt validation and shared domain awards
    bpe: BPE-02
    depends_on: []
    external_dependencies:
    - S03
    - S30
    - S36
    footprint:
    - methodology/api/consumption_views.py
    - mimir/urls.py
    - tests/integration/test_karma_mcp.py
    tests:
    - test_consumption_service_with_authorized_fixture_records_pair
    - test_consumption_receipt_with_invalid_request_rejects_without_awards
    - test_consumption_receipt_with_retry_preserves_awards_and_timestamp
    - test_detail_rest_get_with_authorized_token_does_not_award
    gate:
      command: pytest tests/integration/test_karma_mcp.py -k 'consumption_service or consumption_receipt or detail_rest_get'
        -x
    guidance_bundle:
      activity: BPE/BPE-02-Implement_Backend.md
      rules:
      - do-skeletons-first
      - do-test-first
      - do-not-mock-in-integration-tests
  - id: S39-N2-mcp
    title: Wire existing facade and legacy detail tools with log proofs
    bpe: BPE-02
    depends_on:
    - S39-N1-receipt
    footprint:
    - mcp_integration/context.py
    - mcp_integration/facade/tools_http.py
    - mcp_integration/tools.py
    - methodology/services/phase_service.py
    - tests/integration/test_karma_mcp.py
    - tests/support/karma_mcp.py
    tests:
    - test_mcp_detail_with_authorized_fixture_returns_content_and_pair
    - test_mcp_detail_with_legacy_registration_returns_content_and_pair
    - test_mcp_detail_with_history_options_records_one_pair
    - test_mcp_detail_log_story_happy
    - test_mcp_detail_log_story_reject
    log_story_rows:
    - _complete_mcp_detail:entry
    - ConsumptionReceiptView.post:validation
    - KarmaService.award_successful_consumption:branch
    - KarmaService.award_successful_consumption:exit
    gate:
      command: pytest tests/integration/test_karma_mcp.py -k 'authorized_fixture or legacy_registration or history_options
        or log_story' -x
      log_story_command: pytest tests/integration/test_karma_mcp.py -k log_story -x
    guidance_bundle:
      activity: BPE/BPE-02-Implement_Backend.md
      rules:
      - do-test-first
      - do-assert-log-story
      - do-not-mock-in-integration-tests
  - id: S39-N3-at
    title: Bind all nine exact living-spec examples
    bpe: BPE-04
    depends_on:
    - S39-N2-mcp
    footprint:
    - docs/features/steps/karma_mcp_steps.py
    - tests/integration/test_karma_mcp.py
    gate:
      command: make test-experts-s39-at
    acceptance_command: DJANGO_SETTINGS_MODULE=mimir.settings.acceptance .venv/bin/python manage.py behave --simple
      --tags=@experts --name='KARMA-MCP-01' docs/features/act-18-experts/karma-accrual.feature
    required_examples: 9
    guidance_bundle:
      activity: BPE/BPE-04-Implement_Feature_Acceptance_Tests.md
      rules:
      - do-test-first
      - do-not-mock-in-integration-tests
  - id: S39-N4-protocol
    title: Certify real stdio facade transport
    bpe: BPE-04
    depends_on:
    - S39-N3-at
    footprint:
    - tests/integration/test_karma_mcp.py
    tests:
    - test_mcp_detail_with_stdio_transport_returns_clean_jsonrpc
    gate:
      command: pytest tests/integration/test_karma_mcp.py -k stdio_transport -x
    browser_journey: not_applicable
    guidance_bundle:
      activity: BPE/BPE-04-Implement_Feature_Acceptance_Tests.md
      rules:
      - do-test-first
      - do-not-mock-in-integration-tests
  - id: S39-N5-dod
    title: Complete behavior and observability gates
    bpe: BPE-06
    depends_on:
    - S39-N4-protocol
    footprint: []
    gate:
      command: make test-experts-s39
      log_story_command: pytest tests/integration/test_karma_mcp.py -k log_story -x
    guidance_bundle:
      activity: BPE/BPE-06-Check_Definition_of_Done.md
      rules:
      - do-test-first
      - do-not-mock-in-integration-tests
  scenario_dependencies:
  - S03
  - S30
  - S36
```

## Lessons Learned

1. Both existing MCP implementations remain active; testing only direct functions or only the HTTP facade misses a supported surface.
2. Existing PIP access is creator-or-staff, even when the target playbook is public. Mike’s existing staff flag supplies the eligible fixture without changing Maria.
3. A successful payload decode and explicit receipt separate consumption from ordinary GETs. Retry identity must survive uncertain receipt delivery.
4. Existing facade subprocess tests demonstrate useful protocol mechanics but select a development DB; S39 requires isolated real HTTP/DB proofs.
