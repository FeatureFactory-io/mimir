# S12: EXPERTS-PROFILE-03 Display four source rows that reconcile

This plan uses [the consolidated contract](../pin-convergence-20261123-experts.md). Its shared interfaces, ownership decisions and verification-layer mapping govern this scenario. Commands in the graph below are the canonical execution gates; implementation and test bodies remain unimplemented.

```yaml
scenario: S12
acceptance_id: EXPERTS-PROFILE-03
feature_file_path: docs/features/act-18-experts/experts-profile.feature
feature_line: 15
primary_execution_layer: at
expanded_case_count: 1
dependencies:
- S03
- S10
system_dependencies: []
status: converged_plan_unapplied
source_report_sha256:
- 158ae8dbbb7a4abcf21a1943422beca69e4898229cccf5aecc5f3fdd71c4b3e5
```

## A — Context map


| Verified source | Evidence |
|---|---|
| `docs/features/act-18-experts/experts-profile.feature:26-30` | Exact contract: authenticated Maria opens her own profile; four source amounts reconcile to 8200. |
| `accounts/views.py:285-319` | Actual authenticated view creates/reuses an account token and renders existing account/PIP/playbook/team context; currently contains no Karma projection. |
| `test-data/experts/cedar-rfp-01.json:139-193` | Maria’s historical ledger includes Design and Development; released 5000, PIP 1600, consumption 1200, learning 400, total 8200. |
| `templates/mockups/experts/_breakdown.html:1-5` | Source table has four body rows and total footer; category breakdown is separate and must not be included in source arithmetic. |
| `tests/e2e/conftest.py:101-168` | Real `page` and `live_server_url` fixtures exist; function-scoped server is selected through `E2E_LIVE_SERVER_SCOPE=function`. |

Also inspected actual production profile template and profile integration tests, exact acceptance lifecycle/steps, Behave configuration, Makefile targets, full Cedar dataset, Experts architecture delta, IA §11 and execution graph schema. Proposed `experts_data.py`, `experts_html.py`, ledger and projection modules do not yet exist in this snapshot; their completed interfaces are prerequisites owned by S03.

## B — Do not do


- Do not create another ledger, source aggregation, cached numeric field, fixture loader, HTML parser or profile UI.
- Do not derive displayed points from JSON oracle totals or stored summary prose.
- Do not filter Maria’s source breakdown to Design: PIP includes Design 600 plus Development 1000.
- Do not treat a profile GET as an award event, invoke historical award hooks or regenerate prose.
- Do not move account/token controls to public Experts pages or alter existing authentication.
- Do not certify mockup responses, mocked services, zero collection, skipped scenarios or prototype screenshots as production behavior.
- Do not expand S12 into summary generation, consumption eligibility, MCP registration or UI graduation.

## C — Architecture and implementation sequence


Applicable SAO headings: **Awards, projections and transaction boundaries**, **Web delivery and notification reuse**, **Test strategy for this delta**. IA §11 and user journey **Screen: FOB-PROFILE-VIEW-1** govern presentation.

S03 owns persisted awards, historical Cedar ORM import, source/category projection and shared HTML utilities. S10 owns consumption of that projection by `accounts.profile_view`, the actual profile template, shared breakdown inclusion and profile behavior. S12 adds certification against those completed paths.

Use `load_cedar_baseline() -> CedarDataset`, `users_by_username["mrodriguez"]`, real `KarmaAward` queries, Django client HTTP and actual Playwright navigation. The JSON oracle is an expected-value source, never the application’s numeric data source.

Order after PIN-04 issue/docs handoff and PIN-05 GO:

1. BPE-02: implement ORM/HTTP reconciliation and freshness tests plus reusable HTML assertion; any resulting production defect returns to its owning S03/S10 contract.
2. BPE-04: bind S12’s two exact Then phrases and add scoped acceptance target.
3. BPE-05: certify actual profile source values and readability at all seven IA viewports.
4. BPE-06: run rollup, review evidence and inherited account regressions.

Each node is a separate Angular commit with `Refs #N`, followed by the required issue update containing SHA and next node. Final certification uses `Closes #N`. Parent owns publication/approval coordination.

## D — Tests and exact assertions


| Test/binding | Assertions |
|---|---|
| `test_profile_sources_with_cedar_ledger_reconcile` | Load real Cedar ORM; independently aggregate Maria’s persisted award kinds, merging major/minor into PIP. Assert 5000/1600/1200/400 and 8200. Authenticate real client, GET `reverse("profile")`, assert 200 and production template. Inspect source table body: exactly four ordered labels Released/PIP/Consumption/Learning and matching integers. Their sum equals footer and `profile-karma-total` 8200, displayed as `8,200`. Separate category section is not counted. |
| `test_profile_sources_with_new_learning_award_refresh_values` | After baseline, insert one valid historical test-only learning award of 5 through S03’s real schema with unique `event_identity`. GET actual profile again: only Learning becomes 405, source sum/footer/card become 8205. Stored summary is unchanged. Subsequent GET leaves the award identities, counts and points unchanged. No mock or live consumption hook. |
| `source_rows_show` | Inspect actual `context.response` HTML through shared utility; match exact four body rows against supplied 5000/1600/1200/400; compare to actual ORM aggregates for `context.cedar_dataset` Maria. |
| `source_sum_matches_total` | Sum parsed source body cells; require equality with supplied 8200, actual ORM sum, table footer and actual profile total. |
| `test_profile_sources_with_required_viewports_remain_reconciled` | Seven parameter cases: 1280×800, 1920×1080, 1512×982, 768×1024, 1024×768, 390×844, 360×800. Real browser login and `/auth/user/profile/`; scope named table and body rows, scroll normally, check all values/labels visible, total reconciled and no page-level horizontal overflow. Capture table/profile screenshot for review. |

Reuse S10’s Maria authentication and “she opens her own profile” bindings. Reuse S03’s baseline binding. Do not register duplicates.

Future Makefile contracts:

- `test-at-experts-profile03` runs  
  `DJANGO_SETTINGS_MODULE=mimir.settings.acceptance $(PYTHON) manage.py behave --simple --tags=@experts --name='^EXPERTS-PROFILE-03 Display four source rows that reconcile$' docs/features/act-18-experts/experts-profile.feature`
- `test-experts-profile03-browser` runs  
  `E2E_LIVE_SERVER_SCOPE=function $(PYTEST) -c tests/e2e/pytest.ini -o addopts= -p no:playwright -p no:asyncio -p no:anyio tests/e2e/test_experts_profile_sources.py -x`
- `test-experts-profile03` runs integration file, `tests/integration/test_profile_page.py`, exact AT target and browser target sequentially, stopping on failure.

AT must report exactly one executed/passed scenario and no undefined/skipped selected steps. Browser must execute all seven cases. Existing aggregate Experts target excludes `@wip` and cannot substitute for the explicit S12 target.

## E — Log story


No new production log-story rows: S12 adds test certification only, with no controller, service or state-transition behavior. Existing profile logging and S03/S10 projection logging remain their owners’ obligations. Do not fabricate test-only production log beats or defer an owning scenario’s log proof to S12.

Accordingly omit `log_tests` and `checkpoint.log_story_command`.

## F — MCP tools


Not applicable. This contract exercises the authenticated HTML profile; no facade, API tool, client schema or registration changes.

## G — Agent proofs


Not applicable. This contract reads persisted numeric awards and stored prose without invoking an LLM. SAO §17 summary PRFs remain owned by summary-generation scenarios. No ScriptedLLM, tool registry or new agent trace is needed here.

## H — Mockup graduation and ownership


Reference: `templates/mockups/experts/own_profile.html` and `_breakdown.html`.

S10 owns partial graduation into `templates/accounts/profile.html`; S03 owns shared production breakdown/projection contracts. S12 adds no BPE-03 node and no template/CSS/handler writes. Browser evidence must come from the production profile route. Verify source table semantics, separate category section, exact numeric reconciliation and seven-viewport readability. Any discovered UI defect is reconciled with S10 rather than silently enlarging S12.

## Parent convergence

Authoritative acceptance source: `docs/features/act-18-experts/experts-profile.feature:15`; 1 expanded case(s), primary layer `at`. Dependencies: S03, S10. The full scenario includes all composed journey/UAT obligations assigned in the consolidated contract. Shared Make/catalog registration belongs only to S03.

## Canonical feature execution graph

```yaml
feature_execution_graph:
  feature_ref: EXPERTS-PROFILE-03
  nodes:
  - id: N1-ledger-http-proof
    title: Certify real ledger and profile reconciliation
    bpe: BPE-02
    depends_on: []
    footprint:
    - tests/integration/test_experts_profile_sources.py
    - tests/support/experts_html.py
    tests:
    - test_profile_sources_with_cedar_ledger_reconcile
    - test_profile_sources_with_new_learning_award_refresh_values
    gate:
      command: pytest tests/integration/test_experts_profile_sources.py -x
    guidance_bundle:
      activity: BPE/BPE-02-Implement_Backend.md
      rules:
      - do-skeletons-first
      - do-test-first
      - do-not-mock-in-integration-tests
      - do-docstring-format
      - pytest
  - id: N2-exact-acceptance
    title: Execute the exact living acceptance contract
    bpe: BPE-04
    depends_on:
    - N1-ledger-http-proof
    footprint:
    - docs/features/steps/experts_profile_steps.py
    gate:
      command: make test-experts-s12-at
    guidance_bundle:
      activity: BPE/BPE-04-Implement_Feature_Acceptance_Tests.md
      rules:
      - do-test-first
      - do-not-mock-in-integration-tests
      - pytest
  - id: N3-production-browser
    title: Certify four readable source rows in the browser
    bpe: BPE-05
    depends_on:
    - N2-exact-acceptance
    footprint:
    - tests/e2e/test_experts_profile_sources.py
    gate:
      command: make test-experts-s12-browser
    guidance_bundle:
      activity: BPE/BPE-05-Implement_Journey_Certification_Tests.md
      rules:
      - do-test-first
      - do-not-mock-in-integration-tests
      - do-semantic-versioning-on-ui-elements
      - pytest
  - id: N4-definition-of-done
    title: Certify reconciliation and inherited profile behavior
    bpe: BPE-06
    depends_on:
    - N3-production-browser
    footprint: []
    gate:
      command: make test-experts-s12
    guidance_bundle:
      activity: BPE/BPE-06-Check_Definition_of_Done.md
      rules:
      - do-test-first
      - do-not-mock-in-integration-tests
      - do-follow-commit-convention
      - pytest
  scenario_dependencies:
  - S03
  - S10
```

## Lessons Learned

The fixture’s Design subtotal 7200 differs from Maria’s overall 8200: source PIP must include Development’s 1000. Parsing every numeric cell across both source and category sections would double-count totals, so certification must scope source `tbody` separately from its footer and category section. Existing global pytest defaults ignore E2E, and default Behave tags exclude this contract; both need explicit scoped gates. No files changed, commands executed as tests, or behavior certified during planning.
