# S10: EXPERTS-PROFILE-01 Add contribution signals to Maria's existing profile

This plan uses [the consolidated contract](../pin-convergence-20261123-experts.md). Its shared interfaces, ownership decisions and verification-layer mapping govern this scenario. Commands in the graph below are the canonical execution gates; implementation and test bodies remain unimplemented.

```yaml
scenario: S10
acceptance_id: EXPERTS-PROFILE-01
feature_file_path: docs/features/act-18-experts/experts-profile.feature
feature_line: 7
primary_execution_layer: at
expanded_case_count: 1
dependencies:
- S03
system_dependencies: []
status: skeleton_applied_unimplemented
source_report_sha256:
- f210f2fcc77513feaa51285ba5440d8c78b4585cf55ddccc9e8f99ae28ad65a1
```

## A — Context map and implementation contract


| Verified reference | Relevance |
|---|---|
| `accounts/views.py:285–318` | Real `login_required` profile view reads only `request.user`; creates/reads that user's token and retains account, PIP, playbook and team context. |
| `templates/accounts/profile.html:1–60` | Working production profile extends the real shell; account edit and token controls already exist. Extend this template. |
| `templates/mockups/experts/own_profile.html:5–13` | Prototype contribution card, summary preview and accessible expansion recipe to graduate. |
| `tests/integration/test_profile_page.py:13–58` | Real Django-client profile/authentication and token/PIP/playbook assertions to retain. |
| `tests/e2e/conftest.py:112–168` | Actual browser fixtures are `page` and `live_server_url`; preserve their existing context/server lifecycle. |

The exact scenario requires authenticated Maria to open `/auth/user/profile/`, see `profile-karma-card`, `profile-karma-total` containing `8,200`, primary category `Design`, and existing account controls.

S03 owns the numeric API:

```text
ExpertsService.project_user(user_id: int) -> immutable ExpertProjection
ExpertProjection(
    user_id, username, display_name, total_points, primary_category,
    category_points: tuple pairs, source_points: tuple pairs
)
```

Pass `request.user.pk`, never a `User` object or caller-selected username. S10 reads `ExpertProfile.contribution_summary` separately. S03 owns that schema and seeds Maria's stored paragraph through `load_cedar_baseline()`. No generation or S23 dependency.

Complete core profile architecture belongs here:

1. Keep the existing authenticated view and route.
2. Add one namespaced `contributions` context value alongside existing keys.
3. Use the projection for live numeric values, independently of stored prose.
4. Read stored prose without creating or updating an `ExpertProfile`.
5. Render source/category rows and the accessible four-line expansion structure now; S11/S12 subsequently certify their precise contracts.
6. Preserve account editing, token display/copy/toggle/regeneration, PIPs, owned playbooks and teams.

Shared data contract: explicitly call `load_cedar_baseline() -> CedarDataset`, use `users_by_username`, `playbooks_by_pk`, `oracle`, and `CEDAR_PASSWORD`. Behave reuses S03's `context.cedar_dataset`; do not introduce a second baseline loader.

## B — Do-not-do list


- Do not replace existing `profile_view` with a raising stub or make it public.
- Do not select another subject from query parameters, usernames or token arguments.
- Do not create an anonymous token or Karma account.
- Do not touch authentication, email verification, account editing or token rotation policy.
- Do not generate prose, invoke Galdr/provider code, schedule jobs or mutate awards during GET.
- Do not compute totals from prose or duplicate S03's aggregation/category rules.
- Do not hide the whole contribution card for zero-point users.
- Do not copy the prototype's simplified account card over the existing account UI.
- Do not introduce React, another shell, raw color overrides or a new public profile route.
- Do not log prose, email, token, password or private playbook/PIP content.
- Do not mutate seed/demo/production data. S03 owns schema and tracked-seed obligations.
- Do not treat skeleton failures, skipped tests or zero selected Behave cases as completion.

## C — Governing SAO headings


- **Web UI Architecture → Django Implementation Details / Progressive Enhancement / Testing Strategy**
- **Security & Access Control → FOB / Guest read security**
- **Request ID Logging**
- **Experts & Karma delivery architecture — planned delta → Awards, projections and transaction boundaries / Web delivery and notification reuse / Test strategy for this delta**
- **E2E Testing with Playwright**

IA §11 and the Act18 journey require the existing profile functions, live numeric totals, four-line own-profile preview and accessible expansion. §17 governs generation elsewhere; S10 reads stored text only.

## D — Tests and checkpoints


Create the following real-DB tests; do not mock services or projections.

| Test | Required assertions |
|---|---|
| `test_profile_view_with_maria_adds_contribution_context` | Cedar Maria authenticated; GET 200; existing profile template; total 8200/formatted `8,200`; `Design`; stored nine-sentence oracle paragraph; four source rows and category rows supplied. |
| `test_profile_view_with_maria_preserves_account_controls` | Existing account values, edit link, token field/toggle/copy/password-confirmed regeneration form, PIP/playbook/team sections remain. GET retains an existing token rather than rotating it. |
| `test_profile_view_with_other_subject_query_uses_request_owner` | Authenticate Maria, supply another username/user-id query; context and rendered contribution signals remain Maria's; other account token absent. |
| `test_profile_view_with_missing_expert_profile_preserves_account_page` | Real authenticated user without `ExpertProfile`; GET succeeds, numeric projection remains available, summary is empty; no profile/award/interaction row created. |
| `test_profile_view_with_summary_markup_escapes_content` | Store literal markup in a real profile; template escapes it, preserving normal autoescaping rather than marking generated text safe. |
| `test_profile_contribution_context_with_maria_log_story_happy` | `caplog` + `assert_log_story` prove entry/stored branch/exit for supplied request ID; no prose/email/token/password. |
| `test_profile_contribution_context_with_anonymous_request_log_story_reject` | Direct helper boundary with actual `AnonymousUser` raises `PermissionDenied`; reject log precedes projection/token access; token/award/profile counts unchanged. |
| `test_own_profile_with_maria_renders_signals_and_existing_controls` | Real browser login using `CEDAR_PASSWORD`; production URL; exact score/category locators and existing controls visible. Parametrize all seven IA viewports; no page-level horizontal overflow. |

S11 owns detailed overflow measurement, Show more/less interaction and keyboard certification; S12 owns exact four-source arithmetic; S13 owns HTTP authentication-preservation certification. Their work depends on this complete core rather than supplying architecture missing from S10.

AT bindings in `docs/features/steps/experts_profile_steps.py`:

- `Maria is authenticated`
- `she opens "{path}"`
- `"{test_id}" is present`
- `"{test_id}" reads "{value}"`
- `the primary playbook category is "{category}"`
- `existing account/profile controls remain available`

Reuse any generic binding already assigned during convergence rather than registering duplicate decorators. S10 owns Maria authentication and profile-specific assertions. Catalog exact ownership in `docs/features/CATALOG.md`.

Proposed behavior checkpoint, identical to terminal graph gate:

```bash
pytest -o addopts= tests/integration/test_experts_own_profile.py tests/integration/test_profile_page.py tests/integration/test_profile_teams.py tests/integration/test_profile_edit_email_change.py tests/e2e/test_experts_own_profile.py -x
```

Log checkpoint:

```bash
pytest -o addopts= tests/integration/test_experts_own_profile.py -k log_story -x
```

Exact living-spec gate:

```bash
DJANGO_SETTINGS_MODULE=mimir.settings.acceptance python manage.py behave --simple --tags=@experts --name='^EXPERTS-PROFILE-01 Add contribution signals to Maria.s existing profile$' docs/features/act-18-experts/experts-profile.feature
```

The explicit tag override permits this named WIP contract to run during implementation. Completion requires exactly the selected scenario to execute and pass, not merely exit successfully with nothing selected. Keep the feature-level WIP policy until the owning contracts are implemented.

Browser gates use `pytest -o addopts=` because repository defaults ignore `tests/e2e`. `page` and `live_server_url` are verified fixtures. The browser test loads Cedar into its runner-owned database and uses the existing `e2e_helpers.login`; it must not connect to the recording database. Use function-scoped live-server mode if mixing test categories exposes database-lifecycle interference.

## E — Log story


`where` is the literal function name in messages; levels are INFO.

| Where | Beat | Trigger | Required fragments |
|---|---|---|---|
| `accounts.views._profile_contribution_context` | entry | Authenticated profile projection begins | `beat=entry`, `actor_user_id=<Maria pk>`, `request_id=<request id>` |
| `accounts.views._profile_contribution_context` | branch | Stored paragraph found | `beat=branch`, `summary_state=stored`, `subject_user_id=<Maria pk>` |
| `accounts.views._profile_contribution_context` | branch | No profile/prose | `beat=branch`, `summary_state=missing`, `subject_user_id=<pk>` |
| `accounts.views._profile_contribution_context` | exit | Context assembled | `beat=exit`, `total_points=8200`, `primary_category=Design`, `source_count=4`, `request_id=<request id>` |
| `accounts.views._validate_profile_contribution_request` | validation | Anonymous/unsaved subject rejected | `beat=validation`, `outcome=rejected`, `reason=authentication_required` or `reason=invalid_user_id`, `request_id=<request id>` |

The happy test also exercises the missing-summary branch using a second real user. The reject test proves the validation row. Assert explicit `beat=...` fragments because the shared helper does not infer beat presence from its dictionary keys.

## F — MCP tools


Not applicable. This adds session-authenticated HTML context to an existing web route. No MCP facade, REST registration, token contract or tool changes.

## G — Agent proofs


Not applicable. No agent capability or model orchestration is introduced. Stored Cedar prose is display evidence, not a provider proof.

## H — Mockup graduation


**Strategy: partial.**

Source: `templates/mockups/experts/own_profile.html`, its `_breakdown.html`, and the four-line rule in `templates/mockups/experts/base.html`.

Destination: existing `templates/accounts/profile.html`; scoped truncation styling in existing `static/css/mimir-app.css`.

Retain the production shell and all account sections. Port only the contribution card, source/category display and expansion recipe. Required hooks:

```text
profile-karma-card
profile-karma-total
profile-primary-category
profile-contribution-summary
profile-summary-toggle
profile-karma-source-breakdown
profile-karma-category-breakdown
```

Use `own-contribution-summary` as the controlled summary ID. Initial long-summary state has a four-line clamp and `aria-expanded="false"`; expansion toggles class/state/Show more–Show less without touching token handlers. Render the complete escaped stored paragraph in the DOM. Keep the existing `extra_js` token code; append the separately scoped summary handler. Production must not inherit the mockup base/banner or read fixture JSON.

During PIN, add comments only to production template/CSS destinations. No active markup, CSS rules, JavaScript handlers or view wiring.

## Parent convergence

Authoritative acceptance source: `docs/features/act-18-experts/experts-profile.feature:7`; 1 expanded case(s), primary layer `at`. Dependencies: S03. The full scenario includes all composed journey/UAT obligations assigned in the consolidated contract. Shared Make/catalog registration belongs only to S03.

## Canonical feature execution graph

```yaml
feature_execution_graph:
  feature_ref: EXPERTS-PROFILE-01
  nodes:
  - id: N1-profile-context
    title: Add owner-only numeric and stored-prose context
    bpe: BPE-02
    depends_on: []
    footprint:
    - accounts/views.py
    - tests/integration/test_experts_own_profile.py
    tests:
    - test_profile_view_with_maria_adds_contribution_context
    - test_profile_view_with_other_subject_query_uses_request_owner
    - test_profile_view_with_missing_expert_profile_preserves_account_page
    - test_profile_contribution_context_with_maria_log_story_happy
    - test_profile_contribution_context_with_anonymous_request_log_story_reject
    log_story_rows:
    - accounts.views._profile_contribution_context:entry
    - accounts.views._profile_contribution_context:branch
    - accounts.views._profile_contribution_context:exit
    - accounts.views._validate_profile_contribution_request:validation
    gate:
      command: pytest -o addopts= tests/integration/test_experts_own_profile.py -k "context or other_subject or
        missing_expert" -x
      log_story_command: pytest -o addopts= tests/integration/test_experts_own_profile.py -k log_story -x
    guidance_bundle:
      activity: BPE/BPE-02-Implement_Backend.md
      rules:
      - do-skeletons-first
      - do-test-first
      - do-not-mock-in-integration-tests
      - do-assert-log-story
      - do-write-concise-methods
  - id: N2-graduate-profile-contributions
    title: Graduate contribution card without replacing account controls
    bpe: BPE-03
    depends_on:
    - N1-profile-context
    footprint:
    - static/css/mimir-app.css
    - templates/accounts/profile.html
    - tests/integration/test_experts_own_profile.py
    mockup_source: templates/mockups/experts/own_profile.html
    production_template: templates/accounts/profile.html
    graduate_strategy: partial
    tests:
    - test_profile_view_with_maria_adds_contribution_context
    - test_profile_view_with_maria_preserves_account_controls
    - test_profile_view_with_summary_markup_escapes_content
    gate:
      command: pytest -o addopts= tests/integration/test_experts_own_profile.py tests/integration/test_profile_page.py
        tests/integration/test_profile_teams.py tests/integration/test_profile_edit_email_change.py -x
    guidance_bundle:
      activity: BPE/BPE-03-Implement_Frontend.md
      rules:
      - do-test-first
      - do-semantic-versioning-on-ui-elements
  - id: N3-profile-acceptance
    title: Bind and execute the exact profile acceptance contract
    bpe: BPE-04
    depends_on:
    - N2-graduate-profile-contributions
    footprint:
    - docs/features/steps/experts_profile_steps.py
    gate:
      command: make test-experts-s10-at
    guidance_bundle:
      activity: BPE/BPE-04-Implement_Feature_Acceptance_Tests.md
      rules:
      - do-not-mock-in-integration-tests
      - do-test-first
    notes: 'The current Makefile ignores AT_PROFILE_SCENARIO; this command must not be accepted as a scoped gate.
      Use the exact Behave command from Section D as an additional required execution gate, without a Makefile change.
      Aggregate make test-at-experts is useful only with recorded selected scenario counts. Zero/skipped scenarios
      fail certification.

      '
  - id: N4-profile-browser
    title: Certify profile signals and retained controls at seven viewports
    bpe: BPE-05
    depends_on:
    - N3-profile-acceptance
    footprint:
    - tests/e2e/test_experts_own_profile.py
    tests:
    - test_own_profile_with_maria_renders_signals_and_existing_controls
    gate:
      command: make test-experts-s10-browser
    guidance_bundle:
      activity: BPE/BPE-05-Implement_Journey_Certification_Tests.md
      rules:
      - do-test-first
      - do-semantic-versioning-on-ui-elements
  - id: N5-profile-dod
    title: Verify complete profile integration and account regressions
    bpe: BPE-06
    depends_on:
    - N4-profile-browser
    footprint: []
    gate:
      command: make test-experts-s10
      log_story_command: pytest -o addopts= tests/integration/test_experts_own_profile.py -k log_story -x
    guidance_bundle:
      activity: BPE/BPE-06-Check_Definition_of_Done.md
      rules:
      - do-test-first
      - do-assert-log-story
      - do-not-mock-in-integration-tests
    required_evidence:
    - Exact Section D Behave scenario executed and passed
    - Seven browser viewport cases executed and passed
    - Existing account and email-change behavior retained
    - No provider, award or summary write on GET
    - S11/S12/S13 certification obligations remain separately tracked
  scenario_dependencies:
  - S03
```

## Lessons Learned

After PIN-04 issue creation and the docs-only handoff commit, execute one commit per graph node. Use `Refs #N` for N1–N4 and `Closes #N` only after N5 and exact AT evidence pass. Every execution update cites its commit and next node, following the controlling issue-publication authorization. No merge/release is authorized here.

Lessons Learned:

- The production profile is substantially richer than its prototype; whole-template replacement would remove working account functions.
- S03's numeric projection and separately persisted prose allow profile delivery independently of provider generation.
- Existing browser defaults ignore E2E tests; explicit `-o addopts=` and collected-case counts are essential.
- Cedar JSON is an oracle, not a fixture to read from production templates. Its adapter belongs in runner-owned test data.
- S11/S12/S13 can remain dedicated certification scenarios because S10 declares their necessary core interfaces and markup architecture now.

## Structural application evidence

`docs/experts-replay/pin-evidence/S10.json` records positive scaffold selection and deliberate NotImplementedError. Existing callable ASTs were preserved. Browser collection is not interaction certification.
