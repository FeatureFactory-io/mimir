# S01: EXPERTS-LIST-01 Open Experts from the in-app navigation

This plan uses [the consolidated contract](../pin-convergence-20261123-experts.md). Its shared interfaces, ownership decisions and verification-layer mapping govern this scenario. Commands in the graph below are the canonical execution gates; implementation and test bodies remain unimplemented.

```yaml
scenario: S01
acceptance_id: EXPERTS-LIST-01
feature_file_path: docs/features/act-18-experts/experts-list.feature
feature_line: 9
primary_execution_layer: at
expanded_case_count: 1
dependencies:
- S03
system_dependencies: []
status: skeleton_applied_unimplemented
source_report_sha256:
- 979062e023558cd3aea0b7fd687e3fbf346b3b2f1802a29c49e185f08aa240c7
```

## A — Context map and reuse


| Reference | Verified relevance |
|---|---|
| `methodology/context_processors.py:183–235` | Real Collaborate links, shared link builder and active-section resolver; currently no Experts entry. |
| `templates/base.html:232–253` | Working generic sidebar loop renders link dictionaries, active class and `aria-current`; no template change needed. |
| `docs/features/user_journey.md:3095–3106` | Experts belongs under Collaborate; exact route, title, subtitle and default Development. |
| `tests/unit/test_primary_nav_section.py:91–127` | Existing shell test checks realm identities and PIPs as last sidebar entry; preserve this behavior. |
| `tests/e2e/conftest.py:93–168` | Implemented `browser`, `context`, `page`, `live_server` and `live_server_url` fixtures. |

Reuse `_link`, `_collaborate_items`, `_resolve_nav_section`, `build_shell_context` and the existing shell rendering. Their bodies work; do not replace them with raising stubs. Existing `primary_nav_section` entry/branch/exit logging already supplies the applicable log story.

S03 owns schema, historical Cedar loading, ranking/projections, `experts_list` URL/view, list template, category parsing/links and default Development. S01 consumes those interfaces and certifies their appearance after actual navigation. Shared test contract:

- `load_cedar_baseline() -> CedarDataset`
- `dataset.users_by_username["esvensson"]`
- `CEDAR_PASSWORD`, limited to fictional test accounts
- Shared baseline AT binding stores `context.cedar_dataset`.

S01 owns the common navigation/title/subtitle/current-category AT phrases below. Later scenarios reuse their registered bindings. S48 depends on S01 and extends the original navigation specification; S01 does not reverse that dependency.

## B — Do not do


- No duplicate list route, category query, ranking service, Cedar adapter or model.
- No separate navbar, sidebar renderer, React application, theme or feature CSS.
- No authentication restriction on the public Experts route.
- No new mail, queue, provider, tool registry or agent framework.
- No Karma write caused by navigation or page rendering.
- No production data/seed changes, real provider calls or contact sends.

## C — Governing architecture


Apply SAO headings **Web UI Architecture → UI Design Conventions**, **Experts & Karma delivery architecture — planned delta → Awards, projections and transaction boundaries**, **Web delivery and notification reuse**, and **Test strategy for this delta**.

SAO §17 applies to contribution-summary generation elsewhere; S01 does not touch it. MCP/agent architecture therefore requires no initialization or wiring here.

## D — Tests, checkpoints and slices


Implement test assertions before behavior after PIN-05 GO. Use real database/client objects; no integration mocks.

| Test | Exact assertions |
|---|---|
| `test_is_experts_path_with_local_paths_returns_expected_match` | List/detail paths match; `/experts-other/` and unrelated existing routes do not. |
| `test_is_experts_path_with_invalid_input_raises_value_error` | Non-string, empty, external and protocol-relative input rejected clearly. |
| `test_collaborate_items_with_experts_preserves_existing_links` | Exactly one `nav-experts`, URL `/experts/`, slug `experts`; Teams and PIPs preserved; PIPs remains last. |
| `test_primary_nav_section_with_experts_path_marks_experts_current` | List/detail resolve to Experts, existing realm/chrome values preserved. |
| `test_experts_navigation_with_authenticated_elena_shows_default_page` | Start at existing landing page, extract actual sidebar href, GET it; 200, path `/experts/`, `<title>` and heading Experts, exact subtitle, Development category `aria-current="page"`, only Experts active in sidebar. No mockup banner/links. |
| `test_experts_navigation_log_story_happy` | Real authenticated `/experts/` response and all Section E beats through `caplog` plus existing `assert_log_story`. |
| `test_experts_navigation_with_sidebar_click_opens_default_page` | Real form login via existing `e2e_helpers.login`; click `nav-experts`; URL, document title, heading, subtitle and Development current state match. Preserve realm navbar/sidebar. |

Behavior checkpoint:

```sh
pytest tests/unit/test_experts_navigation.py tests/integration/test_experts_navigation.py tests/unit/test_primary_nav_section.py tests/integration/test_navbar_links.py -x
```

Log checkpoint:

```sh
pytest tests/integration/test_experts_navigation.py -k log_story -x
```

Exact living AT checkpoint:

```sh
DJANGO_SETTINGS_MODULE=mimir.settings.acceptance python manage.py behave --simple --name '^EXPERTS-LIST-01 Open Experts from the in-app navigation$' docs/features/act-18-experts/experts-list.feature
```

Browser checkpoint:

```sh
E2E_LIVE_SERVER_SCOPE=function pytest -o addopts= tests/e2e/test_experts_navigation.py -x
```

`-o addopts=` is required because the global configuration ignores `tests/e2e`. Use verified fixtures `page` and `live_server_url`, not invented browser fixtures.

The feature currently inherits file-level `@wip`. Exact-name execution can prove S01 independently; do not claim the normal `make test-at-experts` target selects it until the shared feature’s WIP tags are graduated appropriately. S03 owns that shared feature-file coordination.

After the PIN docs handoff and human GO, commit slices with `Refs #N`: backend/tests/log story; integration/AT/catalog; browser certification. Final DoD commit uses `Closes #N`. Apply the supplied GitHub approval/traceability rule when publishing updates.

## E — Log story


| Where | Beat | Trigger | Must include |
|---|---|---|---|
| `primary_nav_section` | entry | Authenticated Experts GET | `entry`, `path=/experts/` |
| `primary_nav_section` | branch | Chrome resolved | `branch`, `chrome=authenticated` |
| `primary_nav_section` | exit | Active section resolved | `exit`, `nav_section=experts` |

These existing logging statements remain; their new path/result must be proven. This navigation scenario has no domain rejection branch, so a fabricated reject log test is unnecessary.

## F — MCP tools


Not applicable. No MCP tool or facade change.

## G — Agent proofs


Not applicable. This slice adds a shell destination and active-section integration. It performs no completion, agent orchestration, capability wiring or PRF behavior.

## H — Mockup graduation and execution graph


| Source | Production destination | Strategy and ownership |
|---|---|---|
| Existing `templates/base.html` sidebar loop | Same file, reused unchanged | Feed one additional link through shell context; retain active-state mechanism. |
| `templates/mockups/experts/list.html` | `templates/experts/list.html`, S03-owned | S03 graduates title/subtitle/category controls. S01 verifies the real destination and absence of mockup chrome. |
| `methodology/context_processors.py` Collaborate group | Same module | Add Experts between Teams and PIPs; match `/experts/` and descendants. |

Only `methodology/context_processors.py` needs a production edit for S01. All later production edits are therefore inside its proposed footprint.

## Parent convergence

Authoritative acceptance source: `docs/features/act-18-experts/experts-list.feature:9`; 1 expanded case(s), primary layer `at`. Dependencies: S03. The full scenario includes all composed journey/UAT obligations assigned in the consolidated contract. Shared Make/catalog registration belongs only to S03.

## Canonical feature execution graph

```yaml
feature_execution_graph:
  feature_ref: EXPERTS-LIST-01
  scenario_dependencies:
  - S03
  nodes:
  - id: S01-N1-backend
    title: Extend shell link and active-section context
    bpe: BPE-02
    depends_on: []
    footprint:
    - methodology/context_processors.py
    - tests/integration/test_experts_navigation.py
    - tests/unit/test_experts_navigation.py
    tests:
    - test_is_experts_path_with_local_paths_returns_expected_match
    - test_is_experts_path_with_invalid_input_raises_value_error
    - test_collaborate_items_with_experts_preserves_existing_links
    - test_primary_nav_section_with_experts_path_marks_experts_current
    - test_experts_navigation_log_story_happy
    log_story_rows:
    - primary_nav_section:entry
    - primary_nav_section:branch
    - primary_nav_section:exit
    gate:
      command: pytest tests/unit/test_experts_navigation.py tests/integration/test_experts_navigation.py -k "not
        shows_default_page" -x
      log_story_command: pytest tests/integration/test_experts_navigation.py -k log_story -x
    guidance_bundle:
      activity: BPE/BPE-02-Implement_Backend.md
      rules:
      - do-test-first
      - do-skeletons-first
      - do-assert-log-story
  - id: S01-N2-render
    title: Certify shared shell rendering against S03 list
    bpe: BPE-03
    depends_on:
    - S01-N1-backend
    mockup_source: templates/mockups/experts/list.html
    production_template: templates/experts/list.html
    graduate_strategy: rewire
    footprint:
    - tests/integration/test_experts_navigation.py
    tests:
    - test_experts_navigation_with_authenticated_elena_shows_default_page
    gate:
      command: pytest tests/integration/test_experts_navigation.py -x
    guidance_bundle:
      activity: BPE/BPE-03-Implement_Frontend.md
      rules:
      - do-test-first
      - do-semantic-versioning-on-ui-elements
  - id: S01-N3-at
    title: Bind the exact navigation acceptance contract
    bpe: BPE-04
    depends_on:
    - S01-N2-render
    footprint:
    - docs/features/steps/experts_navigation_steps.py
    gate:
      command: make test-experts-s01-at
    guidance_bundle:
      activity: BPE/BPE-04-Implement_Feature_Acceptance_Tests.md
      rules:
      - do-test-first
      - do-not-mock-in-integration-tests
  - id: S01-N4-browser
    title: Certify actual signed-in sidebar navigation
    bpe: BPE-05
    depends_on:
    - S01-N3-at
    footprint:
    - tests/e2e/test_experts_navigation.py
    tests:
    - test_experts_navigation_with_sidebar_click_opens_default_page
    gate:
      command: make test-experts-s01-browser
    guidance_bundle:
      activity: BPE/BPE-05-Implement_Journey_Certification_Tests.md
      rules:
      - do-semantic-versioning-on-ui-elements
      - pytest
  - id: S01-N5-dod
    title: Require collected passing proofs and preserve shell behavior
    bpe: BPE-06
    depends_on:
    - S01-N4-browser
    footprint: []
    gate:
      command: make test-experts-s01
      log_story_command: pytest tests/integration/test_experts_navigation.py -k log_story -x
    guidance_bundle:
      activity: BPE/BPE-06-Check_Definition_of_Done.md
      rules:
      - do-assert-log-story
      - do-small-increments
      - do-github-issues
```

## Lessons Learned

The existing sidebar is data-driven, so changing `base.html` would duplicate working behavior. S03’s route/default-state ownership and S01’s navigation ownership must remain explicit to prevent circular dependencies. File-level inherited `@wip` also hides individually completed scenarios from the normal Experts AT target; exact-name evidence and tag graduation must be recorded separately.

## Structural application evidence

`docs/experts-replay/pin-evidence/S01.json` records positive scaffold selection and deliberate NotImplementedError. Existing callable ASTs were preserved. Browser collection is not interaction certification.
