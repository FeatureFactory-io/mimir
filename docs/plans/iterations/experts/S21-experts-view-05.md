# S21: EXPERTS-VIEW-05 Reject missing and ineligible profiles

This plan uses [the consolidated contract](../pin-convergence-20261123-experts.md). Its shared interfaces, ownership decisions and verification-layer mapping govern this scenario. Commands in the graph below are the canonical execution gates; implementation and test bodies remain unimplemented.

```yaml
scenario: S21
acceptance_id: EXPERTS-VIEW-05
feature_file_path: docs/features/act-18-experts/experts-view.feature
feature_line: 35
primary_execution_layer: at
expanded_case_count: 2
dependencies:
- S17
system_dependencies: []
status: skeleton_applied_unimplemented
source_report_sha256:
- 6cdcb1d95acb745fe1dc53cd2acbc6bd06ab1b7a8dc8b092bfc70f965557615f
```

### A — Context map


Paths are relative to `/Users/denispetelin/GitHub/mimir-experts-replay`.

| File:lines | Verified relevance |
|---|---|
| `docs/features/act-18-experts/experts-view.feature:35-46` | Both `no-such-cedar-user` and `nberg` require 404. The adjacent positive contributor case belongs to S22. |
| `test-data/experts/cedar-rfp-01.json:592-658` | Sam has 4,800 historical points and no public playbooks; Nora exists, has zero points, no primary category, a draft and an email. |
| `methodology/utils/playbook_access.py:15-42` | Established no-leak 404 policy; reusable security principle, not an Experts eligibility implementation. |
| `docs/ux/IA_guidelines.md:1179-1192` | Missing/non-expert response is 404; public pages exclude tokens and guest contact addresses. |
| `tests/e2e/conftest.py:101-117,141-168` | Existing isolated `page` and function-scoped live-server support; reuse `live_server_url`. |

Additional actual source inspected: SAO Experts delta/security/§17; `templates/playbooks/404.html`; `docs/features/steps/http_steps.py`; acceptance catalog/environment; Makefile; pytest/Behave configurations.

### B — Do not do


- Do not implement another eligibility query, not-found policy, route, view or template. S17 owns these; S03 supplies the ledger/projection.
- Do not classify “no public released playbook” as ineligible: Sam remains eligible; S22 certifies that case.
- Do not expose Nora’s account existence, name, email, draft, profile controls or private values through the rejection response.
- Do not change account lookup/authentication, award points, create profiles on GET, or alter seed/migrations.
- Do not copy `templates/playbooks/404.html` literally: its text identifies a playbook ID. Reuse its shell/card/error-state recipe through S17’s generic expert response.
- Do not build mockups, generated screens, another browser lifecycle, MCP tools or agent infrastructure.

### C — Governing SAO sections


- **Security & Access Control → FOB; Guest read security:** 404 conceals existence/access differences.
- **Experts & Karma delivery architecture → Awards, projections and transaction boundaries:** positive ledger totals establish contribution identity; detail remains public and allowlisted.
- **Web delivery and notification reuse:** Django/templates, existing shell and production detail route.
- **Test strategy for this delta:** real database/client AT; separate Playwright certification; zero/skipped selected tests do not certify completion.
- **Request ID Logging:** safe correlation.
- **§17 AI Agent Architecture:** reviewed, not applicable to this read-only HTTP rejection slice.

### D — Tests and exact assertions


Create dedicated tests using the real S03 Cedar loader and S17 detail route.

| Test | Required assertions |
|---|---|
| `test_expert_detail_with_missing_or_zero_karma_subject_returns_404` | Parameterize exactly `no-such-cedar-user`, `nberg`. Prove first account absent; second present with zero projected total. Anonymous GET returns actual 404, no redirect and no detail/summary/contact/account-token controls. No profile/award creation. |
| `test_expert_detail_with_ineligible_subject_hides_account_existence` | Compare normalized S17 generic rejection content for missing/Nora paths. Neither response contains Nora’s display name, email, draft title, `mailto:`, private Cedar titles/content or token sentinel. Do not compare unstable whole HTML bytes. |
| `test_expert_detail_with_rejected_subject_log_story_reject` | Both requests prove the same S17 safe rejection narrative; request correlation present; no reason identifying account presence or private values. |
| `test_expert_detail_with_missing_or_zero_karma_subject_browser_returns_404` | Browser navigates both exact URLs; each navigation response is 404; remains on requested Experts path without sign-in redirect; same generic visible rejection content; no expert/contact/token controls or hidden email. Existing shell remains navigable. |

Fixture/API assumptions: `tests/support/experts_data.py::load_cedar_baseline()` returns `CedarDataset`; HTML inspection uses S03’s `tests/support/experts_html.py`, never another parser.

**Exact AT:** execute both expanded rows of the unchanged outline using real Django-client bindings:

```text
DJANGO_SETTINGS_MODULE=mimir.settings.acceptance python manage.py behave --simple --tags=@experts --name='^EXPERTS-VIEW-05 Reject missing and ineligible profiles' docs/features/act-18-experts/experts-view.feature
```

The explicit tag overrides `behave.ini`’s default WIP exclusion for this named contract. Require two executed/passing outline examples, no undefined/pending/failed/skipped selected example.

Reuse centrally owned bindings for baseline, Bob’s anonymous path request and generic response-status assertion. During convergence, register exact aliases for `Bob opens "{path}"` and `the response status is {status:d}` once through their existing generic owners. S21 adds no duplicate actor/path/status step functions.

**Backend gate**

```text
pytest tests/integration/test_experts_not_found.py -x
```

**Browser gate — separate process/settings**

```text
E2E_LIVE_SERVER_SCOPE=function pytest -c tests/e2e/pytest.ini -o addopts= -p no:playwright -p no:asyncio -p no:anyio tests/e2e/test_experts_not_found.py -x
```

### E — Log story


S21 adds no production logging. It certifies S17’s shared rejection path; reconcile stable message labels with S17 before apply.

| Where | Beat | Trigger | Must include |
|---|---|---|---|
| S17 public detail view | entry | Either detail GET | stable operation, anonymous actor, request correlation |
| Same view | branch | No eligible public expert | generic `expert_unavailable`; no account-exists distinction |
| Same view | exit | Rejection response | status 404, same correlation |

Use existing `assert_log_story`; inspect structured fields as well where applicable. Exclude target email, private titles/content, token, model bodies and exception details identifying the account.

```text
pytest tests/integration/test_experts_not_found.py -k log_story -x
```

If S17’s committed logging contract differs, align this certification with its equivalent safe narrative; do not introduce competing production log instrumentation.

### F — MCP tools


Not applicable. No tool, facade, API or registration changes. This contract covers public web GET rejection; existing authenticated MCP policy stays owned elsewhere.

### G — Agent proofs


Not applicable. No LLM invocation, orchestration or selected §17 PRF changes; no ScriptedLLM scripts or agent-proof gate.

### H — Mockup graduation and frontend


No new mockup or production template footprint. S17 graduates the generic not-found presentation using the established shell and `templates/playbooks/404.html` recipe. S21 certifies its actual 404 response and browser presentation. Existing playbook-specific wording must not identify an expert account.

Use S17’s final accessible heading/test IDs; do not invent parallel selectors or alternate error text. No seven-viewport screen generation is required for this status-policy contract; existing responsive shell and parent visual/UAT obligations remain.

## Parent convergence

Authoritative acceptance source: `docs/features/act-18-experts/experts-view.feature:35`; 2 expanded case(s), primary layer `at`. Dependencies: S17. The full scenario includes all composed journey/UAT obligations assigned in the consolidated contract. Shared Make/catalog registration belongs only to S03.

## Canonical feature execution graph

```yaml
feature_execution_graph:
  feature_ref: EXPERTS-VIEW-05
  scenario: S21
  scenario_dependencies:
  - S17
  nodes:
  - id: S21-N1
    title: Certify inherited rejection policy
    bpe: BPE-02
    depends_on: []
    footprint:
    - tests/integration/test_experts_not_found.py
    tests:
    - test_expert_detail_with_missing_or_zero_karma_subject_returns_404
    - test_expert_detail_with_ineligible_subject_hides_account_existence
    - test_expert_detail_with_rejected_subject_log_story_reject
    gate:
      command: pytest tests/integration/test_experts_not_found.py -x
      log_story_command: pytest tests/integration/test_experts_not_found.py -k log_story -x
    guidance_bundle:
      activity: BPE/BPE-02-Implement_Backend.md
      rules:
      - do-test-first
      - do-not-mock-in-integration-tests
      - do-assert-log-story
  - id: S21-N2
    title: Certify both exact outline rows
    bpe: BPE-04
    depends_on:
    - S21-N1
    footprint: []
    shared_bindings:
    - S03-baseline
    - shared-Bob-path
    - shared-response-status
    gate:
      command: pytest tests/integration/test_experts_not_found.py -x
      acceptance_command: DJANGO_SETTINGS_MODULE=mimir.settings.acceptance python manage.py behave --simple --tags=@experts
        --name='^EXPERTS-VIEW-05 Reject missing and ineligible profiles' docs/features/act-18-experts/experts-view.feature
      harness_command: make test-at-harness
    guidance_bundle:
      activity: BPE/BPE-04-Implement_Feature_Acceptance_Tests.md
      rules:
      - pytest
      - do-test-first
      - do-not-mock-in-integration-tests
  - id: S21-N3
    title: Certify anonymous browser rejection
    bpe: BPE-05
    depends_on:
    - S21-N2
    footprint:
    - tests/e2e/test_experts_not_found.py
    gate:
      command: make test-experts-s21-browser
    guidance_bundle:
      activity: BPE/BPE-05-Implement_Journey_Certification_Tests.md
      rules:
      - pytest
      - do-semantic-versioning-on-ui-elements
  - id: S21-N4
    title: Review evidence and Definition of Done
    bpe: BPE-06
    depends_on:
    - S21-N3
    footprint: []
    gate:
      command: make test-experts-s21
      log_story_command: pytest tests/integration/test_experts_not_found.py -k log_story -x
      aggregate_command: make test-at-experts
    guidance_bundle:
      activity: BPE/BPE-06-Check_Definition_of_Done.md
      rules:
      - do-assert-log-story
      - do-github-issues
```

## Lessons Learned

- The outline deliberately distinguishes a missing user from an existing zero-point account; checking only “a URL returns 404” would not prove the eligibility boundary.
- Sam’s adjacent positive historical contribution case prevents accidentally substituting a live-public-playbook requirement.
- Existing 404 markup supplies a visual recipe, but its playbook-specific copy cannot be reused unchanged.
- Shared actor/path/status aliases need one owner; duplicate Behave registrations would obscure otherwise valid acceptance coverage.
- This is a certification scenario with no production footprint. Any discovered implementation defect belongs to S17’s policy owner and must follow the parent footprint/drift rules.

## Structural application evidence

`docs/experts-replay/pin-evidence/S21.json` records positive scaffold selection and deliberate NotImplementedError. Existing callable ASTs were preserved. Browser collection is not interaction certification.
