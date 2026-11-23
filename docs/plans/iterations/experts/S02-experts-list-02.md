# S02: EXPERTS-LIST-02 Preserve category selection in the URL

This plan uses [the consolidated contract](../pin-convergence-20261123-experts.md). Its shared interfaces, ownership decisions and verification-layer mapping govern this scenario. Commands in the graph below are the canonical execution gates; implementation and test bodies remain unimplemented.

```yaml
scenario: S02
acceptance_id: EXPERTS-LIST-02
feature_file_path: docs/features/act-18-experts/experts-list.feature
feature_line: 17
primary_execution_layer: at
expanded_case_count: 1
dependencies:
- S03
- S01
system_dependencies: []
status: skeleton_applied_unimplemented
source_report_sha256:
- 9ae81c0ad2e87344fcf2030c94922be4e8cbab86442eab3daf454a3dedc47d51
```

## A — Context map


S02 certifies S03’s public list implementation. S03 owns `/experts/`, `experts_list`, `_selected_category`, `_category_links`, the query service, Cedar ORM baseline and `templates/experts/list.html`. S02 adds no production parser, service, route, template behavior or schema.

S01 supplies the shared `Then the URL is "{path}"` AT binding. That is S02’s only S01 dependency; sidebar implementation is not needed to select a list category.

Reuse:

- `tests/support/experts_data.py:load_cedar_baseline() -> CedarDataset`, with `users_by_username["esvensson"]`.
- Existing real Django-client lifecycle in `docs/features/environment.py`.
- Existing Playwright `page`, `live_server_url` and `login`.
- Existing `tests/support/log_story.py:assert_log_story`.

Add one test-only HTML extractor because the current support library contains no shared HTML parser. It snapshots actual category anchors; it does **not** normalize category input or reproduce production selection rules.

Verified references:

1. `docs/features/act-18-experts/experts-list.feature:17–23`: exact selection, five links, current state and refresh contract.
2. `docs/architecture/SAO.md:3875–3914`: shared query projection, Django/template delivery and distinct AT/browser certification.
3. `docs/ux/IA_guidelines.md:1167–1192`: actual category links, `aria-current`, persistent query and stable hooks.
4. `templates/mockups/experts/list.html:6–8`: approved category navigation recipe and `experts-category-<slug>` selectors.
5. `tests/e2e/conftest.py:112–117,155–168`: actual `page` and `live_server_url` fixtures.

Cedar data is `test-data/experts/cedar-rfp-01.json`; it is a domain oracle, not a directly loadable Django fixture.

## B — Do not do


- Do not duplicate or take ownership of S03’s category parser, default selection, projection, list template or route.
- Do not store category selection in session, local storage or profile preferences. The requested URL determines the view.
- Do not replace existing working methods with raising stubs.
- Do not edit DEBUG-only prototypes or copy mockup `guest=1` behavior into production.
- Do not broaden S02 into ranking, unknown-category fallback, profile-return navigation, contact restrictions or responsive certification.
- Do not add browser imports to AT bindings.
- Do not treat WIP-filtered aggregate runs, zero collected tests or skipped selected contracts as passing evidence.
- Do not change seed data, migrations, MCP, model providers or award lifecycle.

## C — Governing architecture


- **SAO, Web UI Architecture / Progressive Enhancement:** server-rendered real links; browser refresh must reproduce server output.
- **SAO, Experts planned delta / Web delivery:** existing Django/Bootstrap shell; public `/experts/`.
- **SAO, Experts planned delta / Test strategy:** real DB and Django client for AT; Playwright separately proves navigation/reload/history.
- **SAO, Request ID Logging:** reuse correlation context; no secrets or contact data in logs.
- **IA §11:** exact labels/order and stable category selectors.
- **SAO §17:** N/A for this scenario; category navigation invokes no agent capability.

## D — Tests and implementation slices


| Test/contract | Exact assertions |
|---|---|
| `test_category_links_with_design_query_show_five_links_and_one_current` | Real authenticated GET returns 200 at `/experts/?category=design`; category nav contains exactly Product, Development, Research, Design, Other in that order; each anchor has expected stable test ID and an href resolving to `/experts/?category=<slug>`; exactly Design has `aria-current="page"` and all four other anchors omit `aria-current`. |
| `test_category_selection_with_repeated_design_get_remains_current` | Two independent GETs of the identical Design URL return 200 and identical category-anchor snapshots; Design remains uniquely current; query remains `category=design`. |
| `test_category_selection_log_story_happy` | Capture each real Design GET independently with `caplog`; assert S03’s INFO `experts_list` entry and exit beats using `assert_log_story`, including canonical `category=design` and `correlation_id=`. |
| Named AT `EXPERTS-LIST-02 Preserve category selection in the URL` | Execute the exact six scenario steps plus Cedar background with real Django client; follow the actual rendered Design href; refresh the actual last requested URL; reuse S01’s URL binding. Expected: **one selected scenario and seven passing steps**, no undefined/pending selected step. |
| `test_category_navigation_with_reload_and_history_preserves_query` | Authenticate Elena through existing browser login; open `/experts/`; click `experts-category-design`; verify absolute URL, five labels and unique current state; reload and reassert; select Development, go back, and reassert Design URL/current state. This browser-history check covers the Act18 refresh/back-navigation requirement without depending on public detail. |

AT’s “refresh” binding performs a second HTTP GET. It does not claim browser interaction proof; the Playwright test supplies that proof.

Planned slices after PIN-04 handoff and PIN-05 GO:

1. `docs(plan): contract Experts category persistence` — plan/docs handoff, `Refs #N`.
2. `test(experts): certify category query rendering` — HTML helper, HTTP tests and log proof together, `Refs #N`.
3. `test(experts): bind category persistence acceptance` — exact AT bindings, catalogs and named Make target, `Refs #N`.
4. `test(experts): certify category reload and history` — browser proof and final rollup, `Closes #N` only after all gates pass.

Each implementation slice requires its commit-linked issue update before the next slice. No worker posts those updates.

### Exact future gates

```makefile
.PHONY: test-at-experts-list-02 test-experts-list-02

test-at-experts-list-02:
	DJANGO_SETTINGS_MODULE=mimir.settings.acceptance $(PYTHON) manage.py behave --simple --tags=@experts --name='^EXPERTS-LIST-02 Preserve category selection in the URL$$' docs/features/act-18-experts/experts-list.feature

test-experts-list-02:
	$(PYTEST) tests/integration/test_experts_category_persistence.py -x
	$(MAKE) test-at-experts-list-02
	$(PYTEST) -o addopts= tests/e2e/test_experts_category_persistence.py -x
```

These are proposed execution recipes, **not PIN skeleton implementation**. The Make escaping `$$` supplies the regex end anchor. The exact-name override intentionally permits this single contract despite feature-level `@wip`; the aggregate Experts target remains incomplete until every acceptance contract genuinely executes.

## E — Log story


Consume S03’s view story; add no logging service or second parser.

| Where | Beat | Trigger | Level | Required fragments |
|---|---|---|---|---|
| `experts_list` | entry | Design query GET, including repeated GET | INFO | `entry`, `category=design`, `correlation_id=` |
| `experts_list` | exit | Successful Design response | INFO | `exit`, `category=design`, `status=200`, `correlation_id=` |

Entry may additionally include `category_input=design`. `_selected_category`’s `source=query/default` decision belongs to S03. Match its final declared vocabulary during convergence.

Only happy-path log proof applies here. S09 owns unknown-category recovery/reject coverage. Clear captured records between repeated requests so the first response cannot satisfy the second response’s required story.

## F — MCP tools


Not applicable. No tool, REST facade, registration or client contract changes.

## G — Agent proofs


Not applicable. No model calls, prompts, tool execution, interaction records or SAO §17 PRF rows are affected.

## H — Mockup graduation


S03 owns graduation of `templates/mockups/experts/list.html` into `templates/experts/list.html` using **rewire**. S02 certifies its category portion:

- Real anchors styled with existing Bootstrap pills.
- `experts-category-tabs` plus `experts-category-product/development/research/design/other`.
- Accessible navigation label and visible category labels.
- Exactly one `aria-current="page"`.
- Production URLs preserve canonical category query.

S02 does not need a BPE-03 node or production template placeholder. If certification reveals absent behavior, fix it in S03’s declared ownership before S02 proceeds; do not silently expand S02.

## Parent convergence

Authoritative acceptance source: `docs/features/act-18-experts/experts-list.feature:17`; 1 expanded case(s), primary layer `at`. Dependencies: S03, S01. The full scenario includes all composed journey/UAT obligations assigned in the consolidated contract. Shared Make/catalog registration belongs only to S03.

## Canonical feature execution graph

```yaml
feature_execution_graph:
  feature_ref: EXPERTS-LIST-02
  nodes:
  - id: N1-http-category-contract
    title: Certify category links and repeated server requests
    bpe: BPE-02
    depends_on: []
    footprint:
    - tests/integration/test_experts_category_persistence.py
    - tests/support/experts_category_html.py
    tests:
    - test_category_links_with_design_query_show_five_links_and_one_current
    - test_category_selection_with_repeated_design_get_remains_current
    - test_category_selection_log_story_happy
    log_story_rows:
    - experts_list:entry
    - experts_list:exit
    gate:
      command: pytest tests/integration/test_experts_category_persistence.py -x
      log_story_command: pytest tests/integration/test_experts_category_persistence.py -k log_story -x
    guidance_bundle:
      activity: BPE/BPE-02-Implement_Backend.md
      rules:
      - do-skeletons-first
      - do-test-first
      - do-not-mock-in-integration-tests
      - do-assert-log-story
      - do-write-concise-methods
      - do-docstring-format
  - id: N2-category-acceptance
    title: Bind the exact category persistence acceptance contract
    bpe: BPE-04
    depends_on:
    - N1-http-category-contract
    footprint:
    - docs/features/steps/experts_category_steps.py
    tests:
    - EXPERTS-LIST-02 Preserve category selection in the URL
    gate:
      command: make test-experts-s02-at
    guidance_bundle:
      activity: BPE/BPE-04-Implement_Feature_Acceptance_Tests.md
      rules:
      - do-test-first
      - do-not-mock-in-integration-tests
      - do-docstring-format
  - id: N3-category-browser
    title: Certify real category navigation reload and history
    bpe: BPE-05
    depends_on:
    - N2-category-acceptance
    footprint:
    - tests/e2e/test_experts_category_persistence.py
    tests:
    - test_category_navigation_with_reload_and_history_preserves_query
    gate:
      command: make test-experts-s02-browser
    guidance_bundle:
      activity: BPE/BPE-05-Implement_Journey_Certification_Tests.md
      rules:
      - do-test-first
      - do-semantic-versioning-on-ui-elements
  - id: N4-definition-of-done
    title: Verify every category persistence gate
    bpe: BPE-06
    depends_on:
    - N3-category-browser
    footprint: []
    gate:
      command: make test-experts-s02
      log_story_command: pytest tests/integration/test_experts_category_persistence.py -k log_story -x
    guidance_bundle:
      activity: BPE/BPE-06-Check_Definition_of_Done.md
      rules:
      - do-test-first
      - do-assert-log-story
      - do-github-issues
  scenario_dependencies:
  - S03
  - S01
```

## Lessons Learned

The category controls already have a concrete prototype recipe, but production behavior is absent at this baseline. Assigning the complete list to S03 avoids duplicate parsers and ownership cycles. S02 still needs S01’s shared URL binding for its exact living specification. Global pytest options ignore E2E, so every browser gate must explicitly clear `addopts`. No tests were run and no files were written during this read-only planning task.

## Structural application evidence

`docs/experts-replay/pin-evidence/S02.json` records positive scaffold selection and deliberate NotImplementedError. Existing callable ASTs were preserved. Browser collection is not interaction certification.

## Actual structural footprint

`docs/experts-replay/pin-evidence/S02.json`, `docs/features/steps/experts_category_steps.py`, `docs/plans/iterations/experts/S02-experts-list-02.md`, `tests/e2e/test_experts_category_persistence.py`, `tests/integration/test_experts_category_persistence.py`, `tests/support/experts_category_html.py`

Skeleton: `4c31344d9b88875f649b885abac80183b5d2fbd6`; shared reconciliation: `39d598328d438d09723b6eb14574fbf92fab71c9`. Semantic and physical-file dependencies are recorded separately in the iteration manifest. Context-map line ranges record the workers’ inspection baseline; headers and the final scaffold remain authoritative.
