# S49: FOB-NAV-EXPERTS-02 Guest Experts navigation stays public

This plan uses [the consolidated contract](../pin-convergence-20261123-experts.md). Its shared interfaces, ownership decisions and verification-layer mapping govern this scenario. Commands in the graph below are the canonical execution gates; implementation and test bodies remain unimplemented.

```yaml
scenario: S49
acceptance_id: FOB-NAV-EXPERTS-02
feature_file_path: docs/features/act-0-auth/experts-navigation.feature
feature_line: 16
primary_execution_layer: at
expanded_case_count: 1
dependencies:
- S01
- S07
system_dependencies: []
status: converged_plan_unapplied
source_report_sha256:
- 59e77652fb381038762092493dd9a8d3840940a5042ff6584af12deba6d0d21d
```

## A — Context map


| Verified reference | Implementation consequence |
|---|---|
| `docs/features/act-0-auth/experts-navigation.feature:6-8,110-115` | The guest scenario currently inherits Maria’s unrelated authenticated dashboard Background; relocate the two Experts scenarios intact into their own Cedar-backed feature. |
| `methodology/views.py:55-62`; `mimir/urls.py:92-95` | `/` is an existing public shell entry; `/dashboard/` requires authentication. Start guest navigation at `/`. |
| `methodology/context_processors.py:94-125,128-137,183-191`; `templates/base.html:206-251` | Shared shell supplies all sidebar links to guests. S01 adds Experts and active handling; S49 certifies that delivery without production edits. |
| `templates/partials/guest_auth_banner.html:1-14`; `templates/base.html:161-200` | Reuse the real Sign In/Register banner and existing authenticated-account guard. |
| `docs/architecture/SAO.md:3883-3905,3912-3928`; `docs/ux/IA_guidelines.md:1167-1192`; `tests/e2e/conftest.py:101-117,141-168` | Preserve public projections, contact restrictions and stable hooks; use existing fresh browser and function-scoped server fixtures. |

Read AGENTS, CLAUDE, parent Dr Dobbs, all three `/tmp` instructions, orient roster, current feature/SAO/IA, Cedar oracle, actual routes/templates/context processor, catalogs, harness and S01/S07 reports. Read the four actual Edda node guidance files.

## B — Do not do


- No duplicate Experts route, list query, category-default resolver or navigation context helper.
- No S49 production changes; route/render defects return to S03, shell defects to S01, contact defects to S14/S15.
- No guest Bob account, token creation, Karma award, profile editing or private account controls.
- No email/mailto disclosure, message sending, authentication bypass or permission-policy expansion.
- No duplicate Bob, Cedar, Elena, generic open-path or generic URL bindings.
- No importing decorated Behave modules to delegate work; reuse undecorated support helpers.
- No `guest=1`, mock-authentication flags, copied temporary feature adapter or broad legacy feature scan.
- Do not change S03’s default Development category to satisfy the Design comparison.
- Do not claim a Django-client link follow proves an actual browser click.
- No model generation, MCP changes, new UI features or additional infrastructure.

## C — Applicable SAO sections


**UI Design Conventions; FOB Authorization / Guest read security; Experts & Karma delivery architecture — planned delta; Awards, projections and transaction boundaries; Web delivery and notification reuse; Test strategy for this delta; E2E Testing with Playwright.**

The scenario has four exact steps. Preserve their statements and ID during the parent-owned relocation:

```gherkin
  @wip @experts @guest
  Scenario: FOB-NAV-EXPERTS-02 Guest Experts navigation stays public
    Given Bob is an anonymous visitor
    When he follows Experts from the app sidebar
    Then he reaches "/experts/" without a login redirect
    And the guest banner explains sign-in and registration
```

The destination feature’s Background is `Given the CEDAR-RFP-01 baseline dataset`. S48 shares that destination. Remove only the two Experts additions from the old file; leave unrelated legacy prose and scenarios alone.

## D — Tests and assertions


| Test / contract | Exact required proof |
|---|---|
| `test_guest_navigation_with_sidebar_href_reaches_public_experts` | Real Cedar ORM data; anonymous GET `/` is 200; unique `nav-experts` belongs to Collaborate and has `/experts/`; follow its actual rendered href with `follow=False`; result is 200 with no Location/redirect chain; anonymous request remains anonymous; Experts is current; default category remains Development; real guest banner offers correct Sign In/Register destinations. |
| Same backend test | Reuse S07 private-account assertions; no own-profile controls, user menu, token controls or synthetic token values; user/token/ledger counts remain unchanged; no Bob account is created. |
| Scoped Behave `FOB-NAV-EXPERTS-02` | Exact relocated contract plus Cedar Background runs normally with zero undefined/ambiguous/skipped/failed steps. Its When follows a real HTML href using Django client; catalog explicitly labels this server verification. |
| `test_guest_navigation_with_real_sidebar_click_preserves_public_access` | Fresh anonymous `page`, actual public `/`, actual `nav-experts` click, final `/experts/`, successful navigation response and no auth redirect; visible guest explanation and both authentication actions; current Experts and default Development; no account/private controls. |
| Same browser test, composed regression | Actually click Design; exactly sreed/mrodriguez/pnair/dortiz/hkim in that order with 15,400/8,200/7,600/6,900/5,800; excluded sixth/other-category/zero contributors absent. Every visible Reach out is disabled; no contact mailto or Cedar email in public response. S15 remains owner of hover/focus behavior. |
| DoD rollup | Backend, exact Behave and actual browser gates all pass; zero-selection/skips cannot certify S49. |

Reuse S03 `load_cedar_baseline`, HTML helpers, default category behavior; S07 `assert_public_design_ranking`, `assert_guest_auth_banner`, `assert_no_private_account_controls`; S14/S15 contact delivery.

New S49 bindings only:

1. `he follows Experts from the app sidebar`
2. `he reaches "{path}" without a login redirect`
3. `the guest banner explains sign-in and registration`

Future commands, **not executed**:

```text
pytest tests/integration/test_experts_guest_navigation.py -x
make test-at-experts-contract EXPERTS_FEATURE=docs/features/act-0-auth/experts-navigation.feature EXPERTS_NAME='^FOB-NAV-EXPERTS-02 Guest Experts navigation stays public$' EXPERTS_TAGS=@experts
E2E_LIVE_SERVER_SCOPE=function pytest -c tests/e2e/pytest.ini -o addopts= -p no:playwright -p no:asyncio -p no:anyio tests/e2e/test_experts_guest_navigation.py -x
make test-s49-experts-navigation
```

Parent-owned shared Makefile work must provide the scoped contract target with `--simple`, acceptance settings and explicit tags; update aggregate Experts selection from legacy `navigation.feature` to `experts-navigation.feature`. Proposed `test-s49-experts-navigation` runs the three commands sequentially and fails if any fails.

## E — Log Story Script


Empty, justified: S49 adds only certification and bindings, no production action, decision or transition. Existing S01 shell and S03 public-view observability remain their owners’ obligations. No artificial production logging, S49 caplog test or `log_story_command`.

## F — MCP tools


Not applicable. Browser navigation exposes no new MCP surface and modifies no tool/client registration.

## G — Agent proofs


Not applicable. No summary generation, provider, orchestration or control-plane trace changes.

## H — Mockup graduation




S49 certifies the production shell and anonymously rendered list. Prototype `mock_authenticated`/`guest_query` never enter production.

## Parent convergence

Authoritative acceptance source: `docs/features/act-0-auth/experts-navigation.feature:16`; 1 expanded case(s), primary layer `at`. Dependencies: S01, S07. The full scenario includes all composed journey/UAT obligations assigned in the consolidated contract. Shared Make/catalog registration belongs only to S03.

## Canonical feature execution graph

```yaml
feature_execution_graph:
  feature_ref: FOB-NAV-EXPERTS-02
  scenario_id: S49
  external_dependencies:
  - S01
  - S03
  - S07
  - S15
  nodes:
  - id: S49-backend
    title: Certify guest rendered-link HTTP boundary
    bpe: BPE-02
    depends_on: []
    footprint:
    - tests/integration/test_experts_guest_navigation.py
    tests:
    - test_guest_navigation_with_sidebar_href_reaches_public_experts
    log_story_rows: []
    gate:
      command: pytest tests/integration/test_experts_guest_navigation.py -x
    guidance_bundle:
      activity: BPE/BPE-02-Implement_Backend.md
      rules:
      - do-skeletons-first
      - do-test-first
      - do-not-mock-in-integration-tests
      - do-docstring-format
      - pytest
  - id: S49-acceptance
    title: Bind exact relocated guest navigation contract
    bpe: BPE-04
    depends_on:
    - S49-backend
    footprint:
    - docs/features/act-0-auth/experts-navigation.feature
    - docs/features/steps/experts_guest_navigation_steps.py
    tests:
    - FOB-NAV-EXPERTS-02
    gate:
      command: make test-experts-s49-at
    guidance_bundle:
      activity: BPE/BPE-04-Implement_Feature_Acceptance_Tests.md
      rules:
      - do-test-first
      - do-not-mock-in-integration-tests
      - pytest
  - id: S49-browser
    title: Certify actual anonymous sidebar click and public state
    bpe: BPE-05
    depends_on:
    - S49-acceptance
    footprint:
    - tests/e2e/test_experts_guest_navigation.py
    mockup_source: templates/mockups/experts/list.html
    production_template: templates/experts/list.html
    graduate_strategy: reuse_owner_delivery
    tests:
    - test_guest_navigation_with_real_sidebar_click_preserves_public_access
    gate:
      command: make test-experts-s49-browser
    guidance_bundle:
      activity: BPE/BPE-05-Implement_Journey_Certification_Tests.md
      rules:
      - do-test-first
      - do-semantic-versioning-on-ui-elements
      - pytest
  - id: S49-dod
    title: Require all three certification layers
    bpe: BPE-06
    depends_on:
    - S49-browser
    footprint: []
    tests:
    - backend_contract
    - FOB-NAV-EXPERTS-02
    - actual_sidebar_click
    gate:
      command: make test-experts-s49
      prerequisite: parent supplies conjunctive three-command rollup
    guidance_bundle:
      activity: BPE/BPE-06-Check_Definition_of_Done.md
      rules:
      - do-test-first
      - do-not-mock-in-integration-tests
      - do-follow-commit-convention
      - do-github-issues
      - pytest
  scenario_dependencies:
  - S01
  - S07
```

## Lessons Learned

- The original guest scenario’s inherited authenticated Background would invalidate its own premise; relocation preserves the contract and isolates legacy parser defects.
- Public `/` already supplies a valid entry, avoiding a dashboard login redirect introduced by the test itself.
- S03 defaults to Development. Certify that landing first, then explicitly navigate to Design for the shared five-person comparison.
- Existing browser fixtures and S07 assertions suffice; a new lifecycle or duplicate step library would add contradictions.
