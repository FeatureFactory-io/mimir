# S40: KARMA-MCP-03 Do not award self-fetch

This plan uses [the consolidated contract](../pin-convergence-20261123-experts.md). Its shared interfaces, ownership decisions and verification-layer mapping govern this scenario. Commands in the graph below are the canonical execution gates; implementation and test bodies remain unimplemented.

```yaml
scenario: S40
acceptance_id: KARMA-MCP-03
feature_file_path: docs/features/act-18-experts/karma-accrual.feature
feature_line: 88
primary_execution_layer: at
expanded_case_count: 10
dependencies:
- S39
system_dependencies: []
status: skeleton_applied_unimplemented
source_report_sha256:
- ccc316d25b939b61ac7a5e0414c150dc44cbe437b699801bde865e7a26057f8d
```

## A — Context map


Paths below are relative to `/Users/denispetelin/GitHub/mimir-experts-replay`.

| Verified source | Contract |
|---|---|
| `docs/features/act-18-experts/karma-accrual.feature:108-126` | Exactly ten independent successful self-fetch examples; PIP creator OR target author excludes awards. |
| `docs/architecture/SAO.md:3836-3881` | Shared service owns immutable events, authorization precedes eligibility, explicit channels, atomic paired awards. |
| `mcp_integration/facade/server.py:64-143` | Actual `_build_mcp()` registers all nine detail tools. Legacy registrations are in `mcp_integration/tools.py:3674-3768`. |
| `methodology/services/pip_service.py:513-532` | Existing PIP permission is creator-or-staff. Target authorship alone grants no permission. Both actual MCP wrappers delegate here. |
| `test-data/experts/cedar-rfp-01.json:990-1038,1068-1100` | Real historical PIP identifiers, target playbooks and unchanged totals for both distinct self-PIP cases. |

Also read replay `AGENTS.md`, `CLAUDE.md`, Orient roster, supplied guidance/ownership/GitHub rules, S36/S39/S45 raw reports, actual REST permissions, both entrypoints, protocol fixtures, AT lifecycle and execution-graph schema.

S40 certifies upstream behavior; S36 owns self-exclusions, S39 owns `/api/consumption-receipts/`, facade completion/receipt helpers and existing legacy wrapper wiring. S30 remains sole ledger writer. S45’s actor/channel/action-UUID identity convergence supersedes S36’s older entity-inclusive proposal.

## B — Do not do


- No production writer, service fork, receipt endpoint, registry, server, migration or seed change.
- No award on ordinary REST GETs, serialization, listing or fixture import.
- No actor/author/category/points/time accepted from tool arguments or receipt JSON.
- No special staff exemption from self-consumption: Mike’s existing staff status permits reading the PIP; target authorship still excludes awards.
- No target-author permission expansion, staff promotion for Maria, or weakened private/team/group/PIP checks.
- No HTTP/domain/ledger mocks, substituted tool functions or fabricated transport evidence.
- No GET denial presented as successful self-fetch.
- No zero/skipped/undefined cases presented as acceptance.
- No writes, tests, commits or issue updates during this planning pass.

## C — Architecture and exact examples


Applicable SAO headings: **MCP Interface (FastMCP)**; **REST API Specification → Authentication**; **Security & Access Control**; **MCP Integration: Implementation Patterns → stdio Pollution Prevention / Django ORM in Async MCP Tools**; **Experts & Karma delivery architecture → Awards, projections and transaction boundaries / Test strategy for this delta**.

Every row independently restores Cedar. Resolve auxiliary entity IDs from S03’s real ORM adapter and Mike’s playbook relationships; do not invent Phase/Skill/Rule/Agent/Artifact PKs.

| # | Consumer | Literal content | Tool | Total |
|---|---|---|---|---|
| 1 | Mike | Mike's Playbook | get_playbook | 12450 |
| 2 | Mike | Mike's Workflow | get_workflow | 12450 |
| 3 | Mike | Mike's Phase | get_phase | 12450 |
| 4 | Mike | Mike's Activity | get_activity | 12450 |
| 5 | Mike | Mike's Skill | get_skill | 12450 |
| 6 | Mike | Mike's Rule | get_rule | 12450 |
| 7 | Mike | Mike's Agent | get_agent | 12450 |
| 8 | Mike | Mike's Artifact | get_artifact | 12450 |
| 9 | Mike | Maria's historical PIP targeting Mike's playbook | get_pip | 12450 |
| 10 | Maria | Maria's historical PIP targeting Hana's playbook | get_pip | 8200 |

Row 9 resolves `HIST-MARIA-DEV-01`, target playbook 6201, creator Maria, target author Mike. Row 10 resolves `HIST-MARIA-DESIGN-01`, target 6106, creator Maria, target author Hana. Assert real imported PIP PKs and these relationships before calling tools. Mike remains fixture staff; Maria remains nonstaff. Hana stays 5800 and Maria stays 8200 where applicable.

Algorithm under certification: authorized successful content retrieval → shared `mcp_detail` receipt using server-derived actor and stable UUID → S36 resolves actual target → ordinary target-author or PIP creator/target-author exclusion → successful unchanged content, zero award rows.

## D — Tests and slices


Create `tests/integration/test_karma_mcp_self_fetch.py`; every ten-case parametrization uses the exact ordered table above.

| Test | Required assertions |
|---|---|
| `test_self_fetch_with_registered_facade_returns_content_without_awards` — T1 ×10 | `fastmcp.Client(_build_mcp())`, real configured token, real Django `live_server`, transactional DB. `list_tools()` exposes actual tool/schema; `call_tool()` succeeds and returns actual IDs/content. Full ledger snapshot and every user’s total remain identical. |
| `test_self_fetch_with_shared_service_returns_no_awards` — T2 ×10 | Direct real `KarmaService.award_successful_consumption(..., channel="mcp_detail")` returns empty outcomes; actual permission passes; unchanged complete ledger/totals, including counterpart author. |
| `test_self_fetch_with_registered_legacy_returns_content_without_awards` ×10 | `Client(initialize_mcp())`, actual `set_current_user`/`clear_current_user`, actual registration/list/schema/call, real DB and legacy wrappers. No decorated function substitution. |
| `test_self_fetch_with_facade_stdio_returns_clean_protocol_without_awards` — T3 ×10 | Existing `FacadeMCPClient` subprocess → actual facade module → real live HTTP/token/DB. Initialize, actual `tools/list`, actual `tools/call`, content success, zero ledger changes; stdout contains JSON-RPC only. |
| `test_self_fetch_with_bare_rest_get_does_not_award` ×10 | Real token-authenticated detail GET returns content and leaves ledger/totals unchanged. This is a negative award boundary, not MCP transport proof. |
| `test_self_fetch_with_forged_actor_receipt_rejects_without_awards` | Real receipt rejects forbidden actor/recipient/category/points fields; request actor cannot be changed. No ledger writes. |
| `test_self_fetch_with_target_author_without_pip_permission_rejects` | Hana’s public target-playbook authorship does not authorize reading Maria’s historical Design PIP; actual REST/MCP denial and unchanged ledger. Never promote Hana or Maria. |
| `test_self_fetch_log_story_happy` ×10 | Real shared service + `caplog`/`assert_log_story` proves entry, permission, correct exclusion reason, zero-result exit; no award-success beat. |
| `test_self_fetch_log_story_reject` | Real denied PIP read/receipt produces safe rejection, no award success or private payload/token disclosure. |
| `test_self_fetch_acceptance_with_exact_outline_executes_ten_rows` | Runs the exact named outline under acceptance settings; parses Behave JSON; exactly ten selected and passed, zero skipped/undefined/failed. |

Reuse S03 `load_cedar_baseline()->CedarDataset`, existing `tests/support/log_story.py`, actual `FacadeMCPClient` protocol helper and pytest-django `live_server`. Do not reuse `DjangoTestServer`: its current implementation selects the ambient development database (`tests/integration/test_mcp_facade.py:152-179`). S39’s separate isolated legacy subprocess proof remains its ownership; S40’s legacy registration proof is honestly in-process.

S40 owns only these distinct Behave phrases:

- `<consumer> has a valid MCP token and existing permission for <content>`
- `the consumer successfully uses <tool> on that content`
- `the consumer total remains <total> and no paired author award is created`

Reuse the existing S03 background binding. AT executes real Django-client authorized detail GET plus real token receipt POST, validating the actual response and zero ledger delta. Its HTTP boundary lane is conjunctive with T1/T3 real MCP lanes; it alone does not prove transport.

The pytest acceptance wrapper invokes `manage.py behave --simple --tags=@experts --name='^KARMA-MCP-03 Do not award self-fetch'` for this exact feature, with JSON output and `mimir.settings.acceptance`. Explicit selection preserves all ten despite feature-level WIP. Do not remove feature-wide WIP for unrelated incomplete contracts.

Checkpoint: `pytest tests/integration/test_karma_mcp_self_fetch.py -x`

Log checkpoint: `pytest tests/integration/test_karma_mcp_self_fetch.py -k log_story -x`

## E — Log story


S40 asserts existing upstream-owned beats; it adds no production logging implementation.

| Where | Beat | Trigger | Must include |
|---|---|---|---|
| `KarmaService.award_successful_consumption` | entry | Valid authenticated detail receipt | actor ID, entity kind/ID, stable identity, `channel=mcp_detail` |
| Same | validation | Existing entity permission passes | actor ID, target playbook ID, authorized result |
| Same | branch | Ordinary self-content or PIP self-case | correct actor/author/creator IDs; `self_author` or `self_creator` reason |
| Same | exit | Excluded consumption completes | `created_count=0`, exclusion reason, stable identity |
| Read/receipt boundary | error | Unauthorized PIP or forbidden actor input | safe denial/validation reason, zero awards, no private content |

When both PIP roles match, either documented precedence is acceptable only if the OR exclusion is preserved. The two Cedar PIP rows separately prove creator-only and target-author-only exclusion. No tokens, email, prompts or private payloads in asserted messages.

## F — MCP surface


No new tools. All nine existing `get_*` tools and their S39 backward-compatible optional event identity remain unchanged.

T1 verifies `_build_mcp()` registration and HTTP completion; T2 verifies the shared domain exclusion; T3 verifies the shipped facade stdio boundary. Legacy proof verifies real `initialize_mcp()` registration and actual wrappers independently. Tool schemas must expose no actor, recipient, category, points or timestamp override.

Actor comes from DRF `request.user` on the facade path and existing server context on legacy. Event channel is `mcp_detail`; identity remains immutable across receipt retries. Self-fetch succeeds with original authorized content and no pair.

## G — Agent proofs


N/A. No LLM, CAP, PRF, tools offered to a model, executor, planner or agent trace changes. `ScriptedLLM` and `assert_agent_story` would not prove this deterministic protocol/service contract.

## H — Mockup graduation


N/A. No production UI, templates, browser interaction or mockup graduation. This preserves the entire ten-row acceptance outline.

## Parent convergence

Authoritative acceptance source: `docs/features/act-18-experts/karma-accrual.feature:88`; 10 expanded case(s), primary layer `at`. Dependencies: S39. The full scenario includes all composed journey/UAT obligations assigned in the consolidated contract. Shared Make/catalog registration belongs only to S03.

## Canonical feature execution graph

```yaml
feature_execution_graph:
  feature_ref: KARMA-MCP-03
  nodes:
  - id: N1-service-certification
    title: Backend exclusion and permission certification
    bpe: BPE-02
    depends_on: []
    footprint:
    - tests/integration/test_karma_mcp_self_fetch.py
    - tests/support/experts_mcp_self.py
    tests:
    - test_self_fetch_with_shared_service_returns_no_awards
    - test_self_fetch_with_bare_rest_get_does_not_award
    - test_self_fetch_with_forged_actor_receipt_rejects_without_awards
    - test_self_fetch_with_target_author_without_pip_permission_rejects
    - test_self_fetch_log_story_happy
    - test_self_fetch_log_story_reject
    log_story_rows:
    - consumption:entry
    - consumption:validation
    - consumption:branch
    - consumption:exit
    - boundary:error
    gate:
      command: pytest tests/integration/test_karma_mcp_self_fetch.py -k 'shared_service or bare_rest or forged_actor
        or target_author or log_story' -x
      log_story_command: pytest tests/integration/test_karma_mcp_self_fetch.py -k log_story -x
    guidance_bundle:
      activity: BPE/BPE-02-Implement_Backend.md
      rules:
      - do-test-first
      - do-not-mock-in-integration-tests
      - do-assert-log-story
      - do-docstring-format
      - do-github-issues
  - id: N2-real-protocol-certification
    title: Registered facade, legacy and facade stdio certification
    bpe: BPE-02
    depends_on:
    - N1-service-certification
    footprint:
    - tests/integration/test_karma_mcp_self_fetch.py
    tests:
    - test_self_fetch_with_registered_facade_returns_content_without_awards
    - test_self_fetch_with_registered_legacy_returns_content_without_awards
    - test_self_fetch_with_facade_stdio_returns_clean_protocol_without_awards
    gate:
      command: pytest tests/integration/test_karma_mcp_self_fetch.py -k 'registered or stdio' -x
    guidance_bundle:
      activity: BPE/BPE-02-Implement_Backend.md
      rules:
      - do-test-first
      - do-not-mock-in-integration-tests
      - do-small-increments
      - do-github-issues
  - id: N3-exact-outline
    title: Ten-row real-boundary acceptance
    bpe: BPE-04
    depends_on:
    - N2-real-protocol-certification
    footprint:
    - docs/features/steps/experts_mcp_self_steps.py
    - tests/integration/test_karma_mcp_self_fetch.py
    gate:
      command: make test-experts-s40-at
    guidance_bundle:
      activity: BPE/BPE-04-Implement_Feature_Acceptance_Tests.md
      rules:
      - do-not-mock-in-integration-tests
      - do-test-first
      - do-github-issues
  - id: N4-definition-of-done
    title: Conjunctive service, protocol, acceptance and log rollup
    bpe: BPE-06
    depends_on:
    - N1-service-certification
    - N2-real-protocol-certification
    - N3-exact-outline
    footprint:
    - tests/integration/test_karma_mcp_self_fetch.py
    gate:
      command: make test-experts-s40
      log_story_command: pytest tests/integration/test_karma_mcp_self_fetch.py -k log_story -x
    guidance_bundle:
      activity: BPE/BPE-06-Check_Definition_of_Done.md
      rules:
      - do-assert-log-story
      - do-not-mock-in-integration-tests
      - do-github-issues
  scenario_dependencies:
  - S39
```

## Lessons Learned

Existing permission and self-consumption are separate decisions: creator-or-staff authorizes a PIP read; creator-or-target-author excludes its awards. The two PIP examples deliberately distinguish those roles. Existing facade protocol clients are reusable, but their development-server fixture is unsuitable for isolated certification. No new architectural decision or SAO change is proposed.

## Structural application evidence

`docs/experts-replay/pin-evidence/S40.json` records positive scaffold selection and deliberate NotImplementedError. Existing callable ASTs were preserved. Browser collection is not interaction certification.

## Actual structural footprint

`docs/experts-replay/pin-evidence/S40.json`, `docs/features/steps/experts_mcp_self_steps.py`, `docs/plans/iterations/experts/S40-karma-mcp-03.md`, `tests/integration/test_karma_mcp_self_fetch.py`, `tests/support/experts_mcp_self.py`

Skeleton: `a40a1d0a34cbce76db9404f465a514d84086d20a`; shared reconciliation: `39d598328d438d09723b6eb14574fbf92fab71c9`. Semantic and physical-file dependencies are recorded separately in the iteration manifest. Context-map line ranges record the workers’ inspection baseline; headers and the final scaffold remain authoritative.
