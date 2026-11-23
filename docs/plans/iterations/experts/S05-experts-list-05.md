# S05: EXPERTS-LIST-05 Follow Maria to her full public evidence

This plan uses [the consolidated contract](../pin-convergence-20261123-experts.md). Its shared interfaces, ownership decisions and verification-layer mapping govern this scenario. Commands in the graph below are the canonical execution gates; implementation and test bodies remain unimplemented.

```yaml
scenario: S05
acceptance_id: EXPERTS-LIST-05
feature_file_path: docs/features/act-18-experts/experts-list.feature
feature_line: 48
primary_execution_layer: at
expanded_case_count: 1
dependencies:
- S04
- S17
- S19
system_dependencies: []
status: converged_plan_unapplied
source_report_sha256:
- 136d6efcfa12da852d251fa3e99069fb69f7caf24c7542e2309a6f11d38b5ba7
```

## A — Context map


| Verified reference | Relevance |
|---|---|
| `docs/features/act-18-experts/experts-list.feature:48-52` | Exact list-to-detail contract and full-paragraph assertion. |
| `templates/mockups/experts/list.html:13-18` | Maria card and `experts-view-profile-mrodriguez` anchor. |
| `templates/mockups/experts/detail.html:4-7` | Full public summary selector and read/context recipe. |
| `test-data/experts/cedar-rfp-01.json:114-119` | Maria identity and complete nine-sentence stored-summary oracle. |
| `tests/e2e/conftest.py:101-117,159-177` | Existing fresh browser context, `page`, `live_server`, and `live_server_url`. |

Actual production Experts routes, query service, models and domain bindings remain absent at this snapshot. Prototype views read the JSON fixture; they are design references, not reusable production query behavior.

## B — Do not do


- Do not recreate list/detail routes, queries, projections, presenters or summary generation.
- Do not navigate directly to a hardcoded detail path as a substitute for following Maria’s rendered anchor.
- Do not substitute the card hint for the full stored paragraph.
- Do not introduce model/provider work, contact behavior or MCP changes.
- Do not modify prototype templates or use `/mockups/` as delivery evidence.

## C — Applicable architecture


- **Experts & Karma delivery architecture — planned delta / Awards, projections and transaction boundaries:** public detail exposes stored public prose; GET navigation must not generate prose.
- **Web delivery and notification reuse:** Django templates, existing shell and production Experts paths.
- **Test strategy for this delta:** real Django-client AT; separate Playwright certification; skipped/zero selected cases are not completion.
- **IA §11 / Exact display contract:** hints may clamp; public detail always displays full text.
- **Act 18 / FOB-EXPERTS-LIST+FIND-1 and FOB-EXPERT-VIEW-1:** Maria’s profile provides the evidence behind discovery.

## D — Tests and implementation slices


| Test / binding | Required assertions |
|---|---|
| `test_maria_profile_handoff_with_design_card_displays_full_paragraph` | Authenticate actual Cedar Elena `esvensson`; GET Design; extract Maria’s actual anchor; require href `/experts/mrodriguez/`; GET extracted href; status 200; complete oracle paragraph present. |
| `test_extract_maria_profile_href_with_invalid_anchor_rejects` | Missing anchor, duplicate anchor, missing href and external href fail loudly. |
| `test_maria_profile_handoff_with_browser_click_displays_full_paragraph` | Existing login helper and real live server; Maria’s named link has production href; click it; exact resulting URL; summary locator equals complete Cedar paragraph and is visible. |
| Given `Elena is on the Design leaderboard` | Use existing Cedar baseline; authenticate `esvensson`; reuse S03’s open-path binding. |
| When `she follows Maria's View profile link` | Extract the actual anchor from current response and request that href; retain response. |
| Existing URL assertion | Reuse S01 binding; no duplicate registration. |
| Full stored paragraph assertion | S17 owns/aliases LIST-05’s exact wording and VIEW-01’s complete-paragraph wording. |

S03 owns `context.cedar_dataset` and `load_cedar_baseline()`. S17 owns the full stored paragraph assertion. S04 owns the production anchor and selectors.

Use the narrow test-only extractor below only if parent convergence confirms no equivalent shared S04 extractor. It prevents AT and pytest from implementing separate anchor parsing.

Proposed slice order:

1. Backend contract certification and extractor tests, red → green against completed dependencies.
2. Exact AT bindings/catalog/target, red → green.
3. Actual browser click proof, then DoD review.

One issue-linked commit per slice; final slice closes the scenario. Parent PIN owns concrete issue/handoff/GO records.

### Gates



New named AT target must execute:

```makefile
DJANGO_SETTINGS_MODULE=mimir.settings.acceptance $(PYTHON) manage.py behave --simple --tags='@experts' --name='^EXPERTS-LIST-05 Follow Maria to her full public evidence$$' docs/features/act-18-experts/experts-list.feature
```

This explicitly overrides `behave.ini`’s `not @wip` selection for the named contract. Require **one selected scenario passed, zero undefined/failed/skipped steps**. Do not remove feature-level WIP for unrelated scenarios.

## E — Log story


Empty for this certification-only slice: it introduces no controller, service operation or logging decisions. S03 and S17 own production list/detail log stories and their caplog gates. No additional log-story command is declared; do not add duplicate production logging solely for S05.

## F — MCP tools


Not applicable.

## G — Agent proofs


Not applicable. Reading a persisted paragraph does not invoke the summary completion or change SAO §17 behavior.

## H — Mockup graduation


S05 does not graduate a frontend component. It certifies the composition already owned by S04 and S17:

- S04 graduates Maria’s View profile anchor from `templates/mockups/experts/list.html`.
- S17 graduates the full public paragraph from `templates/mockups/experts/detail.html`.
- Preserve `experts-view-profile-mrodriguez` and `expert-contribution-summary`.
- Actual browser click and full locator text are required; matching prototype source is insufficient.
- Full responsive geometry remains with its dedicated scenarios.

## Parent convergence

Authoritative acceptance source: `docs/features/act-18-experts/experts-list.feature:48`; 1 expanded case(s), primary layer `at`. Dependencies: S04, S17, S19. The full scenario includes all composed journey/UAT obligations assigned in the consolidated contract. Shared Make/catalog registration belongs only to S03.

## Canonical feature execution graph

```yaml
feature_execution_graph:
  feature_ref: EXPERTS-LIST-05
  nodes:
  - id: S05-N1-backend-contract
    title: Certify existing list-to-detail backend contract
    bpe: BPE-02
    depends_on: []
    footprint:
    - tests/integration/test_experts_profile_handoff.py
    - tests/support/expert_profile_handoff.py
    - tests/unit/test_expert_profile_handoff_html.py
    tests:
    - test_extract_maria_profile_href_with_invalid_anchor_rejects
    - test_maria_profile_handoff_with_design_card_displays_full_paragraph
    gate:
      command: pytest tests/unit/test_expert_profile_handoff_html.py tests/integration/test_experts_profile_handoff.py
        -x
    guidance_bundle:
      activity: BPE/BPE-02-Implement_Backend.md
      rules:
      - do-test-first
      - do-not-mock-in-integration-tests
  - id: S05-N2-at
    title: Execute the exact living acceptance contract
    bpe: BPE-04
    depends_on:
    - S05-N1-backend-contract
    footprint:
    - docs/features/steps/experts_handoff_steps.py
    gate:
      command: make test-experts-s05-at
    guidance_bundle:
      activity: BPE/BPE-04-Implement_Feature_Acceptance_Tests.md
      rules:
      - do-test-first
      - do-not-mock-in-integration-tests
  - id: S05-N3-browser
    title: Follow the actual Maria control in Chromium
    bpe: BPE-05
    depends_on:
    - S05-N2-at
    footprint:
    - tests/e2e/test_experts_profile_handoff.py
    tests:
    - test_maria_profile_handoff_with_browser_click_displays_full_paragraph
    gate:
      command: make test-experts-s05-browser
    guidance_bundle:
      activity: BPE/BPE-05-Implement_Journey_Certification_Tests.md
      rules:
      - do-test-first
      - do-not-mock-in-integration-tests
  - id: S05-N4-dod
    title: Review complete handoff evidence
    bpe: BPE-06
    depends_on:
    - S05-N3-browser
    footprint: []
    gate:
      command: make test-experts-s05
    guidance_bundle:
      activity: BPE/BPE-06-Check_Definition_of_Done.md
      rules:
      - do-test-first
      - do-not-mock-in-integration-tests
  scenario_dependencies:
  - S04
  - S17
  - S19
```

## Lessons Learned

No infrastructure or scope proposal. Converge the S17 exact phrase alias and any existing S04 HTML extractor before sequential materialization.

The handoff must prove both the real link and complete destination prose: checking `/experts/mrodriguez/` independently would miss a broken card action. Root pytest configuration excludes E2E and uses different settings, so the browser gate explicitly overrides `addopts` and selects the existing E2E settings.

No writes, commits, test runs or completion claims were made.
