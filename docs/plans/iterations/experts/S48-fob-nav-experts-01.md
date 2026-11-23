# S48: FOB-NAV-EXPERTS-01 Discover Experts in the existing app sidebar

This plan uses [the consolidated contract](../pin-convergence-20261123-experts.md). Its shared interfaces, ownership decisions and verification-layer mapping govern this scenario. Commands in the graph below are the canonical execution gates; implementation and test bodies remain unimplemented.

```yaml
scenario: S48
acceptance_id: FOB-NAV-EXPERTS-01
feature_file_path: docs/features/act-0-auth/experts-navigation.feature
feature_line: 8
primary_execution_layer: at
expanded_case_count: 1
dependencies:
- S01
- S03
system_dependencies: []
status: skeleton_applied_unimplemented
source_report_sha256:
- 30c92e546175c89d8b3034119dd89763389e0febf68537424130294469b34589
```

## A — Context map and reuse


| Verified reference | Relevance |
|---|---|
| `methodology/context_processors.py:128–191,215–255` | Existing Workspace/Methodology/Collaborate groups, Teams/PIPs entries and path resolver; S01 exclusively owns Experts addition and active context. |
| `templates/base.html:206–252` | Existing desktop/offcanvas sidebar, labelled section lists, decorative icons, `.active` and `aria-current="page"` rendering. |
| `docs/ux/IA_guidelines.md:404–441,1152–1171` | Preserve shell, existing navigation order and URL-derived active state; Experts uses existing tokens and real category links. |
| `tests/unit/test_primary_nav_section.py:105–134` | Existing realm identities and PIPs-last invariant; add Experts without breaking these assertions. |
| `tests/e2e/conftest.py:101–168` | Working `page`, `live_server_url` and function-scoped live-server selection; no new browser lifecycle needed. |

Also verified existing shell regressions in `tests/integration/test_base_shell.py`, `test_navbar_links.py`, and caplog recipe in `test_app_shell_log_story.py`.

S03 owns real Cedar loading, shared HTML parsing, list route/view/template and Development default. S01 owns Elena authentication, following Experts, URL/title/subtitle/category bindings and all production navigation behavior. S48 adds distinct certification only.

Legacy source has unrelated Maria/dashboard Background at lines 6–8 and malformed historical prose/table around line 20. Exact-name selection still parses that file and inherits its Background. Parent will **relocate**, preserving IDs/statements, the two Experts navigation contracts into `docs/features/act-0-auth/experts-navigation.feature` with one Cedar Background. No temporary extraction adapter, duplicate requirement or legacy cleanup.

## B — Do not do


- Do not add another menu, controller, route, context processor or active-state implementation.
- Do not change `base.html`, existing navigation order, icons, collapse persistence or realm identities.
- Do not create a collapsible Collaborate component: it is a labelled section, not an accordion.
- Do not simulate a click in Django-client AT; real sidebar/offcanvas activation belongs to Playwright.
- Do not scan unrelated legacy features or treat zero/skipped tests as completion.
- Do not award Karma, generate summaries, send mail or touch production/idle databases.

## C — Governing architecture


Apply SAO **Experts & Karma delivery architecture — planned delta → Web delivery and notification reuse** (`3897–3910`) and **Test strategy for this delta** (`3912–3928`), plus **E2E Testing with Playwright**.

UI remains Django templates, Bootstrap/HTMX, existing shell and stable selectors. S48 introduces no new infrastructure, business behavior or provider seam.

## D — Tests and precise assertions


| Test | Required assertions |
|---|---|
| `test_sidebar_with_authenticated_elena_preserves_existing_navigation` | Load real Cedar; authenticate `esvensson`; GET `/dashboard/`. Exactly one sidebar; section labels Workspace/Methodology/Collaborate; unchanged Methodology ordering; Collaborate exactly Teams→Experts→PIPs. Experts is a real anchor named Experts, href exactly `/experts/`, test ID `nav-experts`; existing link destinations retained; icon is decorative and follows S01’s existing `_link` recipe. |
| `test_sidebar_with_experts_destination_marks_only_experts_current` | Extract actual href using S03 parser, GET it; 200, final path `/experts/`, `experts-leaderboard` present. Within sidebar only Experts has both `.active` and `aria-current="page"`; Teams/PIPs lack them. Realm Mimir independently remains current. Development remains selected through S03. No mockup chrome. |
| `test_sidebar_log_story_happy` | Real authenticated Experts GET; use existing `assert_log_story` to prove all Section E beats from `methodology.context_processors` at INFO. |
| `test_sidebar_acceptance_with_exact_contract_runs_one_passing_scenario` | Subprocess runs real `manage.py behave --simple`, relocated exact feature, exact anchored name and explicit `--tags=@experts`; JSON report contains exactly this one executed passing scenario, all steps passed, no undefined/skipped/failed steps. Nonzero exit or absent/empty report fails. |
| `test_sidebar_with_real_navigation_opens_experts` | Parameterize desktop `1280×720` and narrow `390×844`; load Cedar before browser work; use existing form-login helper. Desktop uses existing sidebar; narrow clicks `sidebar-toggler`, verifies actual drawer visible. Locate labelled Collaborate list; click real `nav-experts`, assert exact destination, leaderboard, Development current and sole current sidebar link. Reopen narrow drawer after navigation when needed to inspect active state. |

Use S03 `find_by_test_id`/`element_text`; do not create another parser. Do not import decorated Behave modules.

Gate definitions, materialized only during BPE:

- `test-experts-s48-backend`: pytest the two rendered-response tests plus existing `test_primary_nav_section.py`, `test_base_shell.py`, `test_navbar_links.py`, `test_app_shell_log_story.py`, and the new log-story test.
- `test-at-experts-s48`: pytest the exact-contract wrapper above.
- `test-e2e-experts-s48`: the separate browser command below.
- `test-experts-s48`: conjunctively requires backend, exact AT, browser and explicit log-story gates.

Browser command:

```sh
E2E_LIVE_SERVER_SCOPE=function pytest -c tests/e2e/pytest.ini -o addopts= -p no:playwright -p no:asyncio -p no:anyio tests/e2e/test_experts_sidebar_s48.py -x
```

The acceptance wrapper invokes:

```sh
DJANGO_SETTINGS_MODULE=mimir.settings.acceptance python manage.py behave --simple --tags=@experts --name '^FOB-NAV-EXPERTS-01 Discover Experts in the existing app sidebar$' --format=json --outfile=<pytest-temporary-report> docs/features/act-0-auth/experts-navigation.feature
```

The explicit tag expression overrides default `not @wip` selection for this exact contract. WIP graduation remains honest and coordinated; no aggregate completeness claim follows from one scenario.

After PIN-04 issue/docs handoff and PIN-05 GO, implement four slices matching the graph. Every slice uses `Refs #N`, commit-linked approved issue updates, and the final passing slice uses `Closes #N`. No work or gates were executed by this worker.

## E — Log story


| Where | Beat | Trigger | Must include |
|---|---|---|---|
| `primary_nav_section` | entry | Authenticated Experts response | `entry`, `path=/experts/` |
| `primary_nav_section` | branch | Existing chrome resolution | `branch`, `chrome=authenticated` |
| `primary_nav_section` | exit | S01 active-section resolution | `exit`, `nav_section=experts` |

Reuse working statements at `methodology/context_processors.py:90–106`. No additional production logging or invented rejection path. The new caplog proof certifies this contract.

## F — MCP tools


Not applicable. No MCP registration, facade, authorization-forwarding or client behavior changes.

## G — Agent proofs


Not applicable. No completion, agent capability, ToolExecutor or PRF control-plane behavior is touched.

## H — Graduation and local execution graph


S48 graduates no template. It certifies S01’s context-backed entry rendered through unchanged `templates/base.html`; S03 owns production list graduation from `templates/mockups/experts/list.html`. Real clicks target production `/experts/`.

Guidance paths below resolve under the verified repository playbook root `.windsurf/workflows/Edda/`, not the absent FeatureFactory directory.

## Parent convergence

Authoritative acceptance source: `docs/features/act-0-auth/experts-navigation.feature:8`; 1 expanded case(s), primary layer `at`. Dependencies: S01, S03. The full scenario includes all composed journey/UAT obligations assigned in the consolidated contract. Shared Make/catalog registration belongs only to S03.

## Canonical feature execution graph

```yaml
feature_execution_graph:
  feature_ref: FOB-NAV-EXPERTS-01
  scenario_dependencies:
  - S01
  - S03
  nodes:
  - id: S48-N1-shell-proof
    title: Certify inherited shell and log story
    bpe: BPE-02
    depends_on: []
    footprint:
    - tests/integration/test_experts_sidebar_s48.py
    tests:
    - test_sidebar_with_authenticated_elena_preserves_existing_navigation
    - test_sidebar_with_experts_destination_marks_only_experts_current
    - test_sidebar_log_story_happy
    log_story_rows:
    - primary_nav_section:entry
    - primary_nav_section:branch
    - primary_nav_section:exit
    gate:
      command: make test-experts-s48-backend
      log_story_command: pytest tests/integration/test_experts_sidebar_s48.py -k log_story -x
    guidance_bundle:
      activity: BPE/BPE-02-Implement_Backend.md
      rules:
      - do-skeletons-first
      - do-test-first
      - do-not-mock-in-integration-tests
      - do-assert-log-story
  - id: S48-N2-exact-at
    title: Bind and execute the relocated exact living specification
    bpe: BPE-04
    depends_on:
    - S48-N1-shell-proof
    footprint:
    - docs/features/steps/experts_navigation_steps.py
    - tests/integration/test_experts_sidebar_s48.py
    gate:
      command: make test-experts-s48-at
    guidance_bundle:
      activity: BPE/BPE-04-Implement_Feature_Acceptance_Tests.md
      rules:
      - do-test-first
      - do-not-mock-in-integration-tests
      - pytest
  - id: S48-N3-real-browser
    title: Certify desktop and offcanvas navigation
    bpe: BPE-05
    depends_on:
    - S48-N2-exact-at
    footprint:
    - tests/e2e/test_experts_sidebar_s48.py
    gate:
      command: make test-experts-s48-browser
    guidance_bundle:
      activity: BPE/BPE-05-Implement_Journey_Certification_Tests.md
      rules:
      - do-test-first
      - do-semantic-versioning-on-ui-elements
      - pytest
  - id: S48-N4-dod
    title: Require every certification layer
    bpe: BPE-06
    depends_on:
    - S48-N3-real-browser
    footprint: []
    gate:
      command: make test-experts-s48
      log_story_command: pytest tests/integration/test_experts_sidebar_s48.py -k log_story -x
    guidance_bundle:
      activity: BPE/BPE-06-Check_Definition_of_Done.md
      rules:
      - do-test-first
      - do-assert-log-story
      - do-small-increments
      - do-github-issues
```

## Lessons Learned

Exact-name filtering does not isolate a scenario from an invalid legacy feature or its unrelated Background. Relocating the two owned navigation contracts preserves their meaning while enabling honest scoped execution. Collaborate is an existing labelled sidebar group, so inventing another toggle or menu would contradict both the implementation and ownership contract.

## Structural application evidence

`docs/experts-replay/pin-evidence/S48.json` records positive scaffold selection and deliberate NotImplementedError. Existing callable ASTs were preserved. Browser collection is not interaction certification.

## Actual structural footprint

`docs/experts-replay/pin-evidence/S48.json`, `docs/features/steps/experts_navigation_steps.py`, `docs/plans/iterations/experts/S48-fob-nav-experts-01.md`, `tests/e2e/test_experts_sidebar_s48.py`, `tests/integration/test_experts_sidebar_s48.py`

Skeleton: `275962514dc23b3cf4614326da33ed348b9d6239`; shared reconciliation: `39d598328d438d09723b6eb14574fbf92fab71c9`. Semantic and physical-file dependencies are recorded separately in the iteration manifest. Context-map line ranges record the workers’ inspection baseline; headers and the final scaffold remain authoritative.
