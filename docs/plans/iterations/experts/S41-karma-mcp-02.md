# S41: KARMA-MCP-02 Do not award collection listings

This plan uses [the consolidated contract](../pin-convergence-20261123-experts.md). Its shared interfaces, ownership decisions and verification-layer mapping govern this scenario. Commands in the graph below are the canonical execution gates; implementation and test bodies remain unimplemented.

```yaml
scenario: S41
acceptance_id: KARMA-MCP-02
feature_file_path: docs/features/act-18-experts/karma-accrual.feature
feature_line: 108
primary_execution_layer: at
expanded_case_count: 1
dependencies:
- S03
- S39
- S23
system_dependencies: []
status: skeleton_applied_unimplemented
source_report_sha256:
- 5fc937125a651e62c257c23fe2d89bb6675dd3a5e2b5f7e4fb9f85d51596ba7d
```

## A — Context map


| Verified file:lines | Finding |
|---|---|
| `/Users/denispetelin/GitHub/mimir-experts-replay/docs/features/act-18-experts/karma-accrual.feature:128–131` | Exact acceptance calls **list_activities**, retaining Maria 8200 and Mike 12450. |
| `/Users/denispetelin/GitHub/mimir-experts-replay/mcp_integration/facade/tools_http.py:177–199,275–297` | Collection wrappers GET collection routes directly; detail wrappers are separate. |
| `/Users/denispetelin/GitHub/mimir-experts-replay/mcp_integration/tools.py:473–500,764–813,2910–2944` | Legacy lists serialize existing ORM results; activity guidance excluded; PIP list legitimately marks notifications viewed. |
| `/Users/denispetelin/GitHub/mimir-experts-replay/methodology/api/serializers.py:48–95` | Facade workflow metadata includes minimal nested activities; activity list serializer excludes guidance. Preserve these schemas. |
| `/Users/denispetelin/GitHub/mimir-experts-replay/mcp_integration/facade/server.py:64–163,166–188` | Actual facade registration/startup exists. Legacy registration is `tools.py:3674–3716`, called by management command lines 69–73. |

Also read replay AGENTS/CLAUDE, orient, guidance/GitHub/ownership snapshots, Cedar JSON, user journey Act18, SAO delta/§17, collection services/viewsets, existing MCP integration/protocol tests and S39 raw report.

## B — Do not do


No production edits, new tools, receipts for lists, schema/seed changes, permission expansion, providers, agent machinery or UI. Never implement list enumeration by invoking registered detail MCP wrappers. Existing internal ORM permission getters remain legitimate.

Preserve list response fields, filters, ordering, authorized empty results and existing PIP notification-mark semantics. Do not demand complete database immutability: the invariant covers awards and summaries.

## C — Applicable architecture


SAO: **FOB-Centric Architecture**, **MCP Interface (FastMCP)**, **Security & Access Control**, **REST API Specification**, **MCP Integration: Implementation Patterns — stdio Pollution Prevention**, **Experts & Karma delivery architecture — Awards, projections and transaction boundaries / Test strategy**.

Lists award zero even when metadata contains descriptions or nested activity identifiers. Ordinary collection REST GETs also award zero.

Certification flow: restore independent Cedar → prepare Maria’s real token/context → snapshot global invariants → invoke actual registered list → compare authorized metadata → compare invariant snapshots.

S23 is a certification dependency for persisted `AgentInteraction` and summary-state inspection, without introducing an agent proof or triggering generation.

## D — Tests and exact assertions


Bounded matrix: `list_playbooks`, `list_workflows`, `list_activities`, `list_phases`, `list_skills`, `list_rules`, `list_agents`, `list_artifacts`, `list_pips`. These nine playbook-backed collections exist in both registrations. Account/team/configuration tools are outside this matrix.

Use playbook 6201/workflow 6202/activity 6203 and S39’s real supplementary entity fixtures. Maria lists her own historical PIPs with `scope="mine"`; no staff grant. Preserve all existing metadata for each entrypoint rather than demanding identical facade/legacy shapes.

| Proposed test | Assertions |
|---|---|
| `test_collection_with_registered_tool_preserves_metadata_and_state` — T1, 9 tools × 2 entrypoints | Real FastMCP Client; schema present; actual `call_tool`; exact authorized IDs/names/order/metadata; nonempty primary lists; facade→live HTTP→DB; legacy→actual `initialize_mcp()`→DB. |
| `test_collection_with_direct_service_preserves_awards` — T2, 9 tools | Native collection services return actual fixture objects; identical global award/summary snapshots. |
| `test_collection_with_plain_rest_preserves_awards` — 9 routes | Token-authenticated real Django-client GETs return ordinary authorized metadata without awards. |
| `test_collection_with_empty_or_denied_scope_preserves_awards` — 3 cases × 2 entrypoints | Legitimate empty filter, unavailable parent, existing private/PIP restriction: preserve existing error/empty semantics; no private payload; unchanged invariants. |
| `test_collection_with_stdio_entrypoint_preserves_protocol_and_state` — T3, 9 tools × 2 entrypoints | Actual facade/legacy subprocess initialize→tools/list→tools/call; clean JSON-RPC; actual metadata; unchanged isolated DB snapshots. |
| `test_collection_log_story_happy` — 2 entrypoints | Existing list entry log; legacy activity-return log; no detail-wrapper/receipt/award/summary entry beats; no credentials in captured listing records. |
| `test_collection_with_exact_acceptance_executes_one_contract` | Run only exact KARMA-MCP-02 using scoped real Behave runner; assert success, **one executed scenario and three executed steps**, no skips/undefined steps. |

Global snapshots compare **all** KarmaAward rows and fields, total row count, every recipient total/category/source projection, and specifically global `learning`/`consumption` rows. Comparing only Maria/Mike totals is insufficient.

Also compare every ExpertProfile’s `contribution_summary`, update/status/error/correlation fields and all AgentInteraction rows. No summary request, persistence, interaction or scheduling mutation is permitted. Preserve ordinary list notification tracking.

Facade client request hooks record only method/path: collection GETs are permitted; detail GETs and receipt POSTs are absent. Legacy proofs additionally reject registered detail entry logs and changes to activity access timestamps. No HTTP/service mocks or spies.

T2 uses verified native APIs: `get_workflows_for_playbook`, `get_activities_for_workflow`, `list_phases`, resource collection services and `PIPService.list_queryset_for_user`, retaining their permission preconditions. It never calls the consumption writer to “prove” lists.

## E — Existing log story


| Where | Beat | Trigger | Required fragments |
|---|---|---|---|
| Facade list wrapper | entry | collection invocation | `HTTP Tool: list_activities`, `workflow=6202`; analogous workflow row `playbook=6201` |
| Legacy list wrapper | entry | collection invocation | `MCP Tool: list_activities called`, `workflow_id=6202` |
| Legacy activity wrapper | exit | enumeration complete | `Returning`, actual count, `guidance excluded` |

Use `assert_log_story`; its beat labels support these existing messages. No production log additions are necessary. Rejection behavior is proved by real responses and invariant snapshots; no fabricated rejection log is required. Configure user context before the listing-only capture window.

## F — MCP surface


Existing nine registered collection tools; read-only, no HITL, no added actor arguments. Facade auth is its configured token; legacy auth is existing server context.

T1 covers `_build_mcp()` and `initialize_mcp()` through FastMCP Client, not direct wrapper calls. T3 covers both actual stdio entrypoints. Initialization already exists; no registration or server modification is planned.

## G — Agent proofs


Not applicable. Listing changes no CAP, PRF, agent workflow, model completion or ToolExecutor. Persisted summary invariance is a domain regression assertion.

## H — Mockup graduation


Not applicable: no visual behavior, template, browser interaction or journey change.

## Parent convergence

Authoritative acceptance source: `docs/features/act-18-experts/karma-accrual.feature:108`; 1 expanded case(s), primary layer `at`. Dependencies: S03, S39, S23. The full scenario includes all composed journey/UAT obligations assigned in the consolidated contract. Shared Make/catalog registration belongs only to S03.

## Canonical feature execution graph

```yaml
feature_execution_graph:
  feature_ref: KARMA-MCP-02
  nodes:
  - id: S41-N1-backend-certification
    bpe: BPE-02
    depends_on: []
    external_dependencies:
    - S03
    - S39
    - S23
    footprint:
    - tests/integration/test_karma_mcp_collections.py
    - tests/support/karma_mcp.py
    gate:
      command: pytest tests/integration/test_karma_mcp_collections.py -k 'registered_tool or direct_service
        or plain_rest or empty_or_denied or log_story' -x
      log_story_command: pytest tests/integration/test_karma_mcp_collections.py -k log_story -x
    guidance_bundle:
      activity: BPE/BPE-02-Implement_Backend.md
      rules:
      - do-test-first
      - do-not-mock-in-integration-tests
      - do-assert-log-story
    tests:
    - test_collection_with_registered_tool_preserves_metadata_and_state
    - test_collection_with_direct_service_preserves_awards
    - test_collection_with_plain_rest_preserves_awards
    - test_collection_with_empty_or_denied_scope_preserves_awards
    - test_collection_with_stdio_entrypoint_preserves_protocol_and_state
    - test_collection_log_story_happy
    - test_collection_with_exact_acceptance_executes_one_contract
    title: Prove native collection metadata and unchanged global state
  - id: S41-N2-acceptance
    bpe: BPE-04
    depends_on:
    - S41-N1-backend-certification
    footprint:
    - docs/features/steps/karma_mcp_steps.py
    - tests/integration/test_karma_mcp_collections.py
    gate:
      command: make test-experts-s41-at
    guidance_bundle:
      activity: BPE/BPE-04-Implement_Feature_Acceptance_Tests.md
      rules:
      - do-test-first
      - do-not-mock-in-integration-tests
      - pytest
    title: Run exact award-free collection acceptance
  - id: S41-N3-protocol
    bpe: BPE-04
    depends_on:
    - S41-N2-acceptance
    footprint:
    - tests/integration/test_karma_mcp_collections.py
    gate:
      command: pytest tests/integration/test_karma_mcp_collections.py -k stdio_entrypoint -x
    guidance_bundle:
      activity: BPE/BPE-04-Implement_Feature_Acceptance_Tests.md
      rules:
      - do-not-mock-in-integration-tests
      - pytest
    browser_journey: not_applicable
    title: Verify actual facade and legacy collection protocol
  - id: S41-N4-dod
    bpe: BPE-06
    depends_on:
    - S41-N1-backend-certification
    - S41-N2-acceptance
    - S41-N3-protocol
    footprint: []
    gate:
      command: make test-experts-s41
      log_story_command: pytest tests/integration/test_karma_mcp_collections.py -k log_story -x
    guidance_bundle:
      activity: BPE/BPE-06-Check_Definition_of_Done.md
      rules:
      - do-test-first
      - do-assert-log-story
      - do-github-issues
    success_requires:
    - all_parameterized_cases_pass
    - exact_AT_1_scenario_3_steps
    - both_stdio_surfaces
    - log_story_pass
    title: Certify the complete collection contract
  scenario_dependencies:
  - S03
  - S39
  - S23
```

## Lessons Learned

- The exact contract names `list_activities`; adding literal `list_workflows` regression coverage must preserve that acceptance identity.
- Workflow metadata legitimately nests activity identifiers; that does not justify detail-tool calls or consumption receipts.
- Legacy PIP listing changes notification-read state, so blanket database-immutability assertions would reject valid existing behavior.
- Existing subprocess tests provide protocol mechanics but need isolated databases; direct wrapper tests alone do not prove registration.

## Structural application evidence

`docs/experts-replay/pin-evidence/S41.json` records positive scaffold selection and deliberate NotImplementedError. Existing callable ASTs were preserved. Browser collection is not interaction certification.

## Actual structural footprint

`docs/experts-replay/pin-evidence/S41.json`, `docs/features/steps/karma_mcp_steps.py`, `docs/plans/iterations/experts/S41-karma-mcp-02.md`, `tests/integration/test_karma_mcp_collections.py`

Skeleton: `428d5fe9f04bc16989e78033dd23b2a0ee64b7ba`; shared reconciliation: `39d598328d438d09723b6eb14574fbf92fab71c9`. Semantic and physical-file dependencies are recorded separately in the iteration manifest. Context-map line ranges record the workers’ inspection baseline; headers and the final scaffold remain authoritative.


## Shared test-interface footprint reconciliation

N1 fills the four already-planned S41 collection interfaces in
`tests/support/karma_mcp.py`: `collection_case`, `collection_service_result`,
`collection_snapshot`, and `assert_collection_result`. The original N1 graph
omitted that shared test path. Bounded private collection helpers may support
these interfaces; actual native collection APIs, metadata, permission and state
oracles remain the contract. Existing implemented S39/detail/protocol helpers
and all S40 self-fetch stubs remain unchanged. N2/N3 consume these completed
interfaces; no duplicate local policy, production source or acceptance scope is
added. Root reconciles test/support ownership under the existing local GO.
