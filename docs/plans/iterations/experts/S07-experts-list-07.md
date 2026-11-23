# S07: EXPERTS-LIST-07 Allow Bob to evaluate public rankings

This plan uses [the consolidated contract](../pin-convergence-20261123-experts.md). Its shared interfaces, ownership decisions and verification-layer mapping govern this scenario. Commands in the graph below are the canonical execution gates; implementation and test bodies remain unimplemented.

```yaml
scenario: S07
acceptance_id: EXPERTS-LIST-07
feature_file_path: docs/features/act-18-experts/experts-list.feature
feature_line: 59
primary_execution_layer: at
expanded_case_count: 1
dependencies:
- S03
- S01
system_dependencies: []
status: converged_plan_unapplied
source_report_sha256:
- 5ead70f80bd8b2dec59b2093a7429f7ccbc6ee49e03ed349a2b2249da154afd9
```

## A — Context map


| Verified reference | Consequence |
|---|---|
| `docs/features/act-18-experts/experts-list.feature:59–64` | Bob anonymously opens Design; same five contributors, guest auth banner, no account Karma/token controls. |
| `docs/architecture/SAO.md:3883–3905` | Ranking is total descending/username ascending, capped at five; Django templates and existing shell own delivery. |
| `test-data/experts/cedar-rfp-01.json:658–685` | Exact Design order is sreed, mrodriguez, pnair, dortiz, hkim; named exclusions distinguish category, sixth place and zero Karma. |
| `templates/partials/guest_auth_banner.html:1–14`; `templates/base.html:165–200` | Working reusable banner already has Sign In/Register hooks; account menu already requires authentication. |
| `tests/integration/test_guest_playbook_browse.py:245–264`; `tests/e2e/conftest.py:101–117,154–168` | Existing guest-shell assertions and real `page`/`live_server_url` fixtures establish reusable verification patterns. |

Additional sources inspected: CLAUDE.md; all three `/tmp` instructions; Act 18 narrative; IA §11; prototype list/contact bodies; account profile view; API permissions; AT environment/HTTP steps; pytest configurations.

## B — Do not do


- Do not introduce a new authentication policy, guest account or Bob Karma account.
- Do not duplicate S03 schema, ledger, category resolution, projection, list route or template.
- Do not duplicate S01 sidebar changes or common URL assertions.
- Do not call own-profile view to render public rankings: it creates an account token.
- Do not modify `IsOwnerOrReadOnly`, PIP permissions, MCP access or released-playbook rules.
- Do not copy mock authentication/query switches into production.
- Do not implement S14 contact behavior or its guest early return.
- Do not add a model/provider/agent invocation to this read.
- Do not treat prototype screenshots, skipped tests or zero selections as completion.

## C — Governing architecture


Applicable SAO headings:

- **UI Design Conventions**
- **FOB Authorization**
- **Guest read security**
- **Experts & Karma delivery architecture — planned delta**
- **Awards, projections and transaction boundaries**
- **Web delivery and notification reuse**
- **Test strategy for this delta**

Act 18 explicitly says guest Bob sees the same public rankings and no private
account/token controls (`user_journey.md:3136–3139`).

IA §11 requires the existing shell, stable selectors, public-screen token
exclusion and reachable Sign In/Register (`IA_guidelines.md:1152–1192`).

S07 adds certification rather than production behavior. If the contract fails,
repair belongs to the owning S03/S01 slice; contact-specific failure belongs to
S14. Reconcile ownership before expanding S07’s production footprint.

## D — Tests and exact assertions


| Test/binding | Required assertions |
|---|---|
| `test_experts_list_with_anonymous_design_request_matches_public_ranking` | Real Cedar DB; anonymous GET `/experts/?category=design` returns 200 without redirect; exactly five ordered card IDs match the fixed Design oracle; totals 15,400/8,200/7,600/6,900/5,800; authenticated Elena’s card ID/order/total projection is identical. |
| Same test, state boundary | Snapshot User, Token and KarmaAward counts after fixture setup; both list requests leave them unchanged; anonymous request remains unauthenticated. |
| `assert_public_design_ranking` | Within `experts-leaderboard`, count exactly five contributor articles; ordered IDs are sreed/mrodriguez/pnair/dortiz/hkim; each has expected formatted total. Exclude tmartin, mchen and nberg explicitly. |
| `assert_guest_auth_banner` | Exactly one `guest-auth-banner`; nested Sign In and Register anchors have correct accessible text and resolve to existing login/register routes. Login may retain the existing path-only `next` behavior. |
| `assert_no_private_account_controls` | No profile-karma-card, profile-contribution-summary, profile-token-field/toggle/copy/regenerate controls, profile-api-token element or nav-view-profile. No fixture private token sentinel or actual synthetic test Token keys in HTML. |
| `test_experts_list_with_guest_browser_shows_public_cards_and_auth_actions` | Fresh anonymous browser context; real production URL; ordered five visible cards; visible banner actions with real destinations; absent private account controls; keyboard Tab reaches both banner actions. |
| Named living contract | Exact LIST-07 scenario executes all five scenario steps plus shared baseline; zero undefined, skipped or failed steps. |

Use S03’s HTML helpers in `tests/support/experts_html.py`:
`find_by_test_id`, `element_text`, `_walk_elements`. No second HTML parser.

Consume S03 `load_cedar_baseline() -> CedarDataset` and
`users_by_username["esvensson"]`; Bob is deliberately absent as an account.

S03 owns baseline/open-URL phrases, including the exact `he opens "{path}"`.
S01 owns common URL assertion. S07 owns these reusable AT phrases:

1. `Bob is an anonymous visitor`
2. `the same five Design contributors are visible`
3. `a guest banner offers Sign In and Register`
4. `no own-profile Karma card or API token is present`

Future commands, never executed by this worker:

```text
pytest tests/integration/test_experts_guest_contract.py -x
pytest -c tests/e2e/pytest.ini -o addopts= -p no:playwright -p no:asyncio -p no:anyio tests/e2e/test_experts_guest.py -x
make test-at-experts-contract EXPERTS_NAME='^EXPERTS-LIST-07 Allow Bob to evaluate public rankings$' EXPERTS_TAGS='@experts'
```

The last command is a **proposed shared harness gate**, not an existing target.
Parent must consolidate its Makefile implementation; it must use acceptance
settings, `--simple`, only `experts-list.feature`, exact name and explicit tags.
Explicit `@experts` selection overrides inherited `not @wip` for this contract.
Keep aggregate Experts WIP selection until its own full gate is honestly green.

## E — Log Story Script


Empty, justified: this slice introduces no production operation, decision or
state transition. It verifies the public view and existing guest chrome owned
by S03/S01. Their declared production/log-story gates remain required.

Do not add artificial logs solely to make certification produce a narrative.
No S07 `log_tests` or `log_story_command`; backend and E2E processes stay separate.

## F — MCP tools


Not applicable. Public browser rankings do not create an anonymous MCP surface.

## G — Agent proofs


Not applicable. No summary generation, orchestration, provider or trace changes.
SAO §17 PRFs remain with their owning summary slices.

## H — Mockup graduation




Prototype lines 5–19 demonstrate banner/cards; production must use real
`request.user.is_authenticated`, real projections and real routes.
S03 graduates the page; S07 certifies its anonymous rendition.
No `guest=1`, `mock_authenticated`, mockup route or fixture-derived rendering
becomes production behavior.

## Parent convergence

Authoritative acceptance source: `docs/features/act-18-experts/experts-list.feature:59`; 1 expanded case(s), primary layer `at`. Dependencies: S03, S01. The full scenario includes all composed journey/UAT obligations assigned in the consolidated contract. Shared Make/catalog registration belongs only to S03.

## Canonical feature execution graph

```yaml
feature_execution_graph:
  feature_ref: EXPERTS-LIST-07
  scenario_id: S07
  external_dependencies:
  - S03
  - S01
  nodes:
  - id: S07-backend-contract
    title: Certify anonymous ranking and account boundary
    bpe: BPE-02
    depends_on: []
    footprint:
    - tests/integration/test_experts_guest_contract.py
    - tests/support/experts_guest_assertions.py
    tests:
    - test_experts_list_with_anonymous_design_request_matches_public_ranking
    log_story_rows: []
    gate:
      command: pytest tests/integration/test_experts_guest_contract.py -x
    guidance_bundle:
      activity: BPE/BPE-02-Implement_Backend.md
      rules:
      - do-skeletons-first
      - do-test-first
      - do-not-mock-in-integration-tests
  - id: S07-acceptance
    title: Execute the exact Bob living contract
    bpe: BPE-04
    depends_on:
    - S07-backend-contract
    footprint:
    - docs/features/steps/experts_guest_steps.py
    tests:
    - EXPERTS-LIST-07
    gate:
      command: make test-experts-s07-at
      prerequisite: parent supplies shared exact-contract Makefile target
    guidance_bundle:
      activity: BPE/BPE-04-Implement_Feature_Acceptance_Tests.md
      rules:
      - pytest
      - do-not-mock-in-integration-tests
  - id: S07-browser
    title: Certify visible public ranking and auth entry points
    bpe: BPE-05
    depends_on:
    - S07-acceptance
    footprint:
    - tests/e2e/test_experts_guest.py
    mockup_source: templates/mockups/experts/list.html
    production_template: templates/experts/list.html
    graduate_strategy: reuse_owner_delivery
    tests:
    - test_experts_list_with_guest_browser_shows_public_cards_and_auth_actions
    gate:
      command: make test-experts-s07-browser
    guidance_bundle:
      activity: BPE/BPE-05-Implement_Journey_Certification_Tests.md
      rules:
      - do-semantic-versioning-on-ui-elements
  - id: S07-dod
    title: Review Bob contract and preserve delivery gates
    bpe: BPE-06
    depends_on:
    - S07-browser
    footprint: []
    tests:
    - test_experts_list_with_anonymous_design_request_matches_public_ranking
    gate:
      command: make test-experts-s07
    guidance_bundle:
      activity: BPE/BPE-06-Check_Definition_of_Done.md
      rules:
      - do-follow-commit-convention
      - do-github-issues
  scenario_dependencies:
  - S03
  - S01
```

## Lessons Learned

Future S07 footprint: the four skeleton paths above plus
`docs/features/CATALOG.md`. Shared dependency additions belong to the parent:
one exact-contract Makefile gate. S03 supplies Cedar and HTML helpers;
S01 supplies shell navigation. No S07 model, migration, seed or production file.

Commit slices after PIN-04/05 GO: docs-only handoff `Refs #N`; backend assertions
and real contract `Refs #N`; AT bindings/catalog `Refs #N`; browser certification
`Closes #N`. Each slice requires its commit-linked issue update and the applicable
approval rule; this worker posts nothing.

Lessons Learned:

- Existing guest banner and shell already solve the chrome requirement.
- Own-profile rendering creates a token; public rendering must remain separate.
- Prototype authentication flags prove appearance only.
- Existing AT target excludes WIP and cannot currently select one exact contract.
- E2E collection needs its own config and explicit global-addopts override.
- No system-infrastructure or scope-reduction proposal is necessary.
