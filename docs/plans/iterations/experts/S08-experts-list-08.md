# S08: EXPERTS-LIST-08 Resolve an equal total deterministically

This plan uses [the consolidated contract](../pin-convergence-20261123-experts.md). Its shared interfaces, ownership decisions and verification-layer mapping govern this scenario. Commands in the graph below are the canonical execution gates; implementation and test bodies remain unimplemented.

```yaml
scenario: S08
acceptance_id: EXPERTS-LIST-08
feature_file_path: docs/features/act-18-experts/experts-list.feature
feature_line: 66
primary_execution_layer: at
expanded_case_count: 1
dependencies:
- S03
system_dependencies: []
status: skeleton_applied_unimplemented
source_report_sha256:
- ef0c0439665ef960d3f20832fe43d50df9233254ba7b9ee9e32ccb7eafd947bf
```

## A — Context map


| Verified reference | Relevance |
|---|---|
| `docs/features/act-18-experts/experts-list.feature:66–69` | Exact contract: isolated TIE03, Design route, `apark` before `sreed`. |
| `test-data/experts/cedar-rfp-01.json:947–969` | Both contributors have 15,400 and primary category Design; expected order is explicit. |
| `docs/architecture/SAO.md:3883–3889` | Rank overall total descending, username ascending, limit five. Primary-category ties are a separate rule. |
| `mockups/experts_views.py:108–133` | Real prototype sorts `(-total_karma, username)` but reads JSON without ORM evidence. Reuse design intent only. |
| `templates/mockups/experts/list.html:13–19` | Stable card hooks, readable rank, formatted total and actions to retain in S03’s production template. |

Also read: replay `AGENTS.md`, `CLAUDE.md`, dispatch guidance, GitHub rule, ownership notes, Act 18 journey, IA §11, Cedar baseline/history, actual acceptance hooks/steps, fixture catalogs, E2E helpers/conftest/config, existing integration tests and graph schema.

## B — Do not do


- Do not implement another ranking or primary-category resolver. S03 owns both.
- Do not confuse equal overall totals with S47’s equal category subtotals.
- Do not set cached profile totals or return fixture JSON as the production leaderboard.
- Do not alter Sofia’s baseline awards, shared Cedar JSON or baseline expected ranking.
- Do not invoke release/PIP hooks while importing historical test events.
- Do not introduce production query parameters or routes for TIE03.
- Do not change provider, model, prompts, scheduling, MCP registration or permissions.
- Do not replace existing Behave/pytest/browser lifecycles or run against the demo/seed DB.

## C — Applicable architecture


- **Experts & Karma delivery architecture — planned delta**
- **Awards, projections and transaction boundaries**
- **Web delivery and notification reuse**
- **Test strategy for this delta**
- **E2E Testing with Playwright**

Act 18 establishes the total/username rule. IA §11 requires DOM reading order to agree with displayed rank and preserves the existing card recipe. SAO §17 requires no work for this scenario.

## D — Tests to create


All tests use real ORM objects and HTTP/browser requests. No service, query, HTML or model doubles.

| Exact test | Assertions |
|---|---|
| `test_cedar_tie03_with_real_awards_preserves_sofia_and_matches_equal_totals` | Sofia remains unchanged; new Alina exists with later PK; real ledger aggregates both total 15,400; both project to Design; returned mapping contains Alina; original dataset mapping/oracle remain unchanged. |
| `test_cedar_tie03_with_missing_sofia_rejects_without_partial_writes` | Invalid input raises `ValueError`; no new user or awards survive. |
| `test_cedar_tie03_with_existing_alina_rejects_without_duplicate_awards` | Reapplying the isolated variant fails clearly and does not duplicate ledger rows. |
| `test_experts_list_with_equal_totals_orders_username_ascending` | Production GET returns 200, Design current; ordered card IDs are `apark,sreed,mrodriguez,pnair,dortiz`; both first totals render `15,400`; ranks are 1 and 2; Hana is pushed outside five. Later-created Alina precedes Sofia, defeating insertion/PK ordering. |
| `test_experts_list_with_equal_totals_repeated_requests_preserve_order_and_awards` | Three independent GETs produce the same actual DOM order; ledger count/payload unchanged, proving read-only rendering. |
| `test_experts_list_with_tie03_browser_preserves_dom_and_visible_rank` | Actual production browser page shows Alina before Sofia in leaderboard DOM and vertical position; rank labels agree; both totals display `15,400`; reload preserves order/query; no mockup URL. |

Use `tests/support/experts_html.py`’s shared `find_by_test_id`, `element_text` and `_walk_elements`, backed by Django `parse_html`, for integration/AT assertions. No regex/string-position ordering proof.

AT binds only these two new phrases:

1. `Given the isolated TIE03 variant with Alina Park and Sofia Reed at 15400`
2. `Then "{first_username}" precedes "{second_username}"`

Reuse the existing S03 baseline and shared `When Elena opens "{path}"` binding. Do not register duplicates.

Commands:

```text
pytest tests/integration/test_experts_list_tie.py -x
make test-at-experts-list-08
pytest -c tests/e2e/pytest.ini -o addopts= -p no:playwright -p no:asyncio -p no:anyio tests/e2e/test_experts_list_tie.py -x
make test-experts-list-08
```

Proposed Make targets:

```make
test-at-experts-list-08:
	DJANGO_SETTINGS_MODULE=mimir.settings.acceptance $(PYTHON) manage.py behave --simple --tags=@experts --name='^EXPERTS-LIST-08 Resolve an equal total deterministically$$' docs/features/act-18-experts/experts-list.feature

test-experts-list-08:
	$(PYTHON) -m pytest tests/integration/test_experts_list_tie.py -x
	$(MAKE) test-at-experts-list-08
	$(PYTHON) -m pytest -c tests/e2e/pytest.ini -o addopts= -p no:playwright -p no:asyncio -p no:anyio tests/e2e/test_experts_list_tie.py -x
```

The named AT deliberately selects this exact `@experts` contract despite its present feature-level WIP tag. Completion requires one executed scenario with all four steps passing, plus all named pytest tests. Zero selection, skips or undefined steps fail the delivery claim. Retain feature-level WIP until the feature’s broader contracts qualify.

Backend and browser commands remain separate; the browser command preserves its own settings/plugin exclusions and overrides root collection ignores.

## E — Log story


Empty, justified: S08 adds an isolated fixture and certification of S03’s existing production projection/list behavior. It adds no production decision, transition, error path or logger. S03’s production log-story gates remain required through the prerequisite. Test-fixture import diagnostics are not a production log story. No redundant log assertions or `log_story_command` are proposed.

## F — MCP tools


Not applicable. No new or modified tool, REST facade endpoint or transport registration.

## G — Agent proofs


Not applicable. The scenario neither invokes nor modifies agent capabilities. No ScriptedLLM, provider rehearsal, PRF or model-quality assertion.

## H — Mockup graduation


S03 owns graduation of `templates/mockups/experts/list.html` into `templates/experts/list.html`, rewiring fixture content to ledger projection. S08 consumes that completed route/template and certifies its ordered cards. No S08 frontend node or production-template edit is necessary.

Preserve `experts-leaderboard`, `experts-card-<username>`, `expert-card-karma`, accessible rank labels and existing actions. Browser certification uses the existing `page` and `live_server_url` fixtures plus `e2e_helpers.login`.

## Parent convergence

Authoritative acceptance source: `docs/features/act-18-experts/experts-list.feature:66`; 1 expanded case(s), primary layer `at`. Dependencies: S03. The full scenario includes all composed journey/UAT obligations assigned in the consolidated contract. Shared Make/catalog registration belongs only to S03.

## Canonical feature execution graph

```yaml
feature_execution_graph:
  feature_ref: EXPERTS-LIST-08
  scenario: S08
  scenario_dependencies:
  - S03
  nodes:
  - id: S08-N1-backend-contract
    title: Certify real isolated equal-total data and production ranking
    bpe: BPE-02
    depends_on: []
    footprint:
    - tests/integration/test_experts_list_tie.py
    - tests/support/experts_tie_data.py
    tests:
    - test_cedar_tie03_with_real_awards_preserves_sofia_and_matches_equal_totals
    - test_cedar_tie03_with_missing_sofia_rejects_without_partial_writes
    - test_cedar_tie03_with_existing_alina_rejects_without_duplicate_awards
    - test_experts_list_with_equal_totals_orders_username_ascending
    - test_experts_list_with_equal_totals_repeated_requests_preserve_order_and_awards
    gate:
      command: pytest tests/integration/test_experts_list_tie.py -x
    guidance_bundle:
      activity: BPE/BPE-02-Implement_Backend.md
      rules:
      - do-skeletons-first
      - do-test-first
      - do-not-mock-in-integration-tests
      - do-write-concise-methods
    notes: 'S03 supplies all production behavior and immutable CedarDataset. This node owns fixture normalization
      and real-DB contract proof only. Resolve Alina historical source normalization before skeleton application.

      '
  - id: S08-N2-acceptance
    title: Execute exactly EXPERTS-LIST-08 through the real AT harness
    bpe: BPE-04
    depends_on:
    - S08-N1-backend-contract
    footprint:
    - docs/features/steps/experts_list_tie_steps.py
    tests:
    - EXPERTS-LIST-08
    gate:
      command: make test-experts-s08-at
    guidance_bundle:
      activity: BPE/BPE-04-Implement_Feature_Acceptance_Tests.md
      rules:
      - do-test-first
      - do-not-mock-in-integration-tests
    notes: 'Reuse baseline and Elena-open-path bindings; register only two S08 phrases. Explicit @experts and
      anchored exact scenario selection. Require one executed scenario and four passing steps.

      '
  - id: S08-N3-browser
    title: Certify visible rank agrees with production DOM order
    bpe: BPE-05
    depends_on:
    - S08-N2-acceptance
    footprint:
    - tests/e2e/test_experts_list_tie.py
    tests:
    - test_experts_list_with_tie03_browser_preserves_dom_and_visible_rank
    gate:
      command: make test-experts-s08-browser
    guidance_bundle:
      activity: BPE/BPE-05-Implement_Journey_Certification_Tests.md
      rules:
      - do-test-first
      - do-semantic-versioning-on-ui-elements
    notes: 'Reuse actual page/live_server_url and login fixtures/helpers. Keep browser settings separate from
      backend test settings. Production route only; verify reload and visible vertical order.

      '
  - id: S08-N4-definition-of-done
    title: Require backend acceptance and browser evidence together
    bpe: BPE-06
    depends_on:
    - S08-N3-browser
    footprint: []
    tests:
    - tests/integration/test_experts_list_tie.py
    - EXPERTS-LIST-08
    - test_experts_list_with_tie03_browser_preserves_dom_and_visible_rank
    gate:
      command: make test-experts-s08
    guidance_bundle:
      activity: BPE/BPE-06-Check_Definition_of_Done.md
      rules:
      - do-test-first
      - do-not-mock-in-integration-tests
    notes: Require actual positive test counts, unchanged baseline and GET ledger, no duplicate ranking implementation,
      no production fixture switch, and complete issue/commit traceability.
```

## Lessons Learned

Plan/docs handoff precedes implementation. Proposed subsequent slices are backend fixture/proof, exact AT bindings, browser certification, and terminal rollup. Each receives an Angular commit with `Refs #N`, followed by its required issue update; only the final successful closure uses `Closes #N`. PIN-04/05 owns concrete issue publication and human GO. No estimate or standalone approval request.

Lessons Learned:

1. The prototype already sorts by username but never applies TIE03; its existing JSON sort cannot certify production tie behavior.
2. TIE03 omits Alina’s ledger decomposition. Normalize transparently in isolated historical data and reconcile against S03 before writing.
3. Creating Alina after Sofia makes a test distinguish username ordering from accidental PK/insertion ordering.
4. Adding Alina changes the five-card cutoff: the variant excludes Hana; baseline expectations remain unchanged.
5. Equal totals and primary-category ties are independent contracts.

No writes, commits, tests or implementation execution were performed.

## Structural application evidence

`docs/experts-replay/pin-evidence/S08.json` records positive scaffold selection and deliberate NotImplementedError. Existing callable ASTs were preserved. Browser collection is not interaction certification.

## Actual structural footprint

`docs/experts-replay/pin-evidence/S08.json`, `docs/features/steps/experts_list_tie_steps.py`, `docs/plans/iterations/experts/S08-experts-list-08.md`, `tests/e2e/test_experts_list_tie.py`, `tests/integration/test_experts_list_tie.py`, `tests/support/experts_tie_data.py`

Skeleton: `bac8f4d6b1c6097ea2ae949c45c91422049faa1d`; shared reconciliation: `39d598328d438d09723b6eb14574fbf92fab71c9`. Semantic and physical-file dependencies are recorded separately in the iteration manifest. Context-map line ranges record the workers’ inspection baseline; headers and the final scaffold remain authoritative.
