# S16: EXPERTS-REACH-03 Apply the same guest restriction on public detail

This plan uses [the consolidated contract](../pin-convergence-20261123-experts.md). Its shared interfaces, ownership decisions and verification-layer mapping govern this scenario. Commands in the graph below are the canonical execution gates; implementation and test bodies remain unimplemented.

```yaml
scenario: S16
acceptance_id: EXPERTS-REACH-03
feature_file_path: docs/features/act-18-experts/experts-reach-out.feature
feature_line: 14
primary_execution_layer: at
expanded_case_count: 1
dependencies:
- S03
- S07
- S14
- S15
- S17
- S20
- S06
- S21
system_dependencies: []
status: skeleton_applied_unimplemented
source_report_sha256:
- 18a8de3c144b19913ca9b3373c5351610a9b68c820ac3d6f1d9718919c3c9b30
```

## A — Context map


| Verified source | Context |
|---|---|
| `docs/features/act-18-experts/experts-reach-out.feature:22-27` | Exact guest-detail acceptance contract; no interaction simulation is needed for its initial-markup assertions. |
| `templates/mockups/experts/_reach_out.html:1-9` | Disabled native button, focusable wrapper, exact explanation and Bootstrap tooltip recipe. |
| `templates/mockups/experts/detail.html:4-7` | Contact toolbar, full public paragraph and public released-playbook evidence. |
| `docs/ux/IA_guidelines.md:1179-1216` | Accessible guest explanation, seven exact viewports and responsive evidence requirements. |
| `tests/e2e/conftest.py:101-117,142-168` | Existing fresh page/context and function-scoped live-server option; reuse without lifecycle changes. |

Also inspected AGENTS/CLAUDE, current orient roster, live guidance/rules/ownership, SAO authorization and Experts delta, Cedar job/JSON, catalogs, Makefile, actual mockup views and existing guest-browse tests. Production Experts route/service/template do not exist yet; their names are planned interfaces, not verified behavior.

## B — Do not do


- Do not duplicate S17 public detail, allowlisted DTO or `visibility=public AND status=released` query; do not use `can_view` alone as that filter.
- Do not duplicate S14 request-local contact context/shared production partial, S15 guest helpers, S03 parser/Cedar loader/path step or S07 anonymous Bob step.
- Do not serialize email into guest public/contact projections, HTML, attributes or embedded JSON.
- Do not substitute an enabled anchor or `aria-disabled` alone for a disabled native button.
- Do not send email, introduce messaging, change permissions, or infer availability.
- Do not simulate hover, focus, tooltip creation or clicks in Django-client AT.
- Do not fill behavior/assertions during PIN; every callable below raises.

## C — Governing architecture


SAO headings: **FOB Authorization**, **Guest read security**, **Experts & Karma delivery architecture — planned delta / Web delivery and notification reuse / Test strategy for this delta**. IA §11 governs presentation and certification.

S16 certifies behavior delivered by S14/S17. Dependencies carry production wiring; S16 has no production Python/template footprint and no infrastructure stub proposal.

## D — Tests and exact assertions


| Test/binding | Required assertions after GO |
|---|---|
| `test_guest_detail_with_anonymous_request_preserves_restricted_contact_and_public_evidence` | Real Cedar ORM + anonymous Django GET `/experts/mrodriguez/` returns 200 without login redirect. S15 `assert_guest_contact_markup(response, None, forbidden_emails)` proves disabled native Reach out, no destination/email, keyboard-focusable wrapper and exact description association. Public/contact DTOs omit contact email; inspect only these allowlisted projections, not the entire Django template context. |
| `assert_guest_detail_evidence_readable` | Shared S03 parser finds the complete stored Maria paragraph, matching Cedar oracle; `expert-playbook-6101` names a real public released playbook, exposes its version/title, and its actual production href returns 200 anonymously with readable public evidence. No `/mockups/` href. |
| Three S16-owned `@then` bindings below | Execute exact S16 steps against actual Django response; reuse S07 Bob, S03 baseline/path bindings. Wrapper phrase has one registration, owned here; S15 uses no competing Behave binding. |
| `test_guest_detail_with_required_viewport_keeps_tooltip_and_evidence_accessible[7 viewports]` | Existing browser fixtures; actual pointer hover and actual keyboard navigation separately reveal exact tooltip, linked to wrapper; native button stays disabled. S15 helpers prove focus and tooltip viewport bounds. Tooltip does not clip or cover the contact/evidence controls. Full summary remains visible, no page horizontal overflow; below 768px rail stacks below body. Follow actual evidence link and read keyboard-focus/form-feedback content; return still anonymous. Capture production screenshots. |

`forbidden_emails` contains fictional account emails from the Cedar oracle; do not restrict the check to the `mailto:` scheme.

Shared APIs to consume unchanged:

- `load_cedar_baseline() -> CedarDataset`, with `users_by_username`, `playbooks_by_pk`, `oracle`.
- `tests/support/experts_html.py`: `find_by_test_id`, `element_text`.
- `tests/support/experts_guest_contact.py`: `GUEST_CONTACT_EXPLANATION`, `assert_guest_contact_markup(response: HttpResponse, container_test_id: str | None, forbidden_emails: tuple[str, ...]) -> None`.
- `tests/support/experts_guest_browser.py`: `guest_contact_wrapper(page, container_test_id)`, `activate_guest_tooltip(page, wrapper, activation)` where activation is `"hover"`/`"keyboard"`, `assert_guest_tooltip_in_viewport(page, tooltip, viewport: tuple[int, int])`.

Browser helper activation must exercise keyboard events, not merely assert `tabindex`. Parent should reconcile whether the shared constant is exported from the contact module; do not create a competing literal.

Commands, defined as YAML anchors below, are separate backend/browser processes. Completion requires **one passing integration test, one passing exact S16 Behave scenario with all six steps including background, and seven passing browser cases**. Zero/skipped/undefined cases fail. Explicit `@experts` selection overrides inherited WIP for the exact scenario without removing other contracts’ WIP.

## E — Log story


No new log rows/tests: S16 introduces certification only, no service/controller/client behavior. S14/S17 own production decision logs and their caplog gates. S16 must not create redundant logging just to produce a separate log gate. Consequently omit `checkpoint.log_story_command`.

## F — MCP


Not applicable. No MCP tool, API write, facade registration/client or stdio entry-point changes.

## G — Agent proofs


Not applicable. Reading stored public prose adds no summary-generation capability, provider call, PRF row, ToolExecutor or agent trace. SAO §17 remains owned by summary scenarios.

## H — Mockup graduation


Sources: `templates/mockups/experts/detail.html` and `_reach_out.html`; production destinations owned by S17/S14: `templates/experts/detail.html` and `_reach_out.html`.

Strategy: **certify upstream rewiring**, never copy fixture access, `mock_authenticated`, `guest=1` or mockup links into production. Existing `templates/base.html:350-355` already initializes Bootstrap tooltips; S16 adds no initializer.

Record production guest-detail renders for `(1280,800)`, `(1920,1080)`, `(1512,982)`, `(768,1024)`, `(1024,768)`, `(390,844)`, `(360,800)` in `docs/ux/experts-responsive-evidence.json`, including actual commit/environment/screenshots/reviewer and defects. Prototype renders do not establish production certification. S16 contributes guest-detail coverage to CEDAR-JOURNEY-02 and EXPERTS-VIEW-07; sibling scenarios retain their other assertions and UAT ownership.

## Parent convergence

Authoritative acceptance source: `docs/features/act-18-experts/experts-reach-out.feature:14`; 1 expanded case(s), primary layer `at`. Dependencies: S03, S07, S14, S15, S17, S20, S06, S21. The full scenario includes all composed journey/UAT obligations assigned in the consolidated contract. Shared Make/catalog registration belongs only to S03.

## Canonical feature execution graph

```yaml
feature_execution_graph:
  feature_ref: EXPERTS-REACH-03
  scenario: S16
  external_dependencies:
  - S03
  - S07
  - S14
  - S15
  - S17
  nodes:
  - id: S16-N1-server-contract
    title: Certify upstream guest contact and public evidence
    bpe: BPE-02
    depends_on: []
    footprint:
    - tests/integration/test_experts_guest_detail.py
    - tests/support/experts_guest_detail.py
    tests:
    - test_guest_detail_with_anonymous_request_preserves_restricted_contact_and_public_evidence
    gate:
      command: pytest tests/integration/test_experts_guest_detail.py -x
      expected_exit_code: 0
      minimum_passed: 1
    guidance_bundle:
      activity: BPE/BPE-02-Implement_Backend.md
      rules:
      - do-skeletons-first
      - do-test-first
      - do-not-mock-in-integration-tests
      - do-docstring-format
      - pytest
  - id: S16-N2-acceptance
    title: Bind exact server-rendered S16 contract
    bpe: BPE-04
    depends_on:
    - S16-N1-server-contract
    footprint:
    - docs/features/steps/experts_contact_steps.py
    gate:
      command: make test-experts-s16-at
      expected_exit_code: 0
      required_scenarios_passed: 1
      required_steps_passed: 6
    guidance_bundle:
      activity: BPE/BPE-04-Implement_Feature_Acceptance_Tests.md
      rules:
      - do-test-first
      - do-not-mock-in-integration-tests
      - pytest
  - id: S16-N3-browser
    title: Certify actual guest tooltip and readable evidence at seven viewports
    bpe: BPE-05
    depends_on:
    - S16-N2-acceptance
    footprint:
    - tests/e2e/test_experts_guest_detail.py
    gate:
      command: make test-experts-s16-browser
      expected_exit_code: 0
      required_passed: 7
    guidance_bundle:
      activity: BPE/BPE-05-Implement_Journey_Certification_Tests.md
      rules:
      - do-test-first
      - do-semantic-versioning-on-ui-elements
      - pytest
  - id: S16-N4-dod
    title: Reconcile observed certification and delivery gates
    bpe: BPE-06
    depends_on:
    - S16-N3-browser
    footprint:
    - docs/ux/experts-responsive-evidence.json
    gate:
      command: make test-experts-s16
      acceptance_command: DJANGO_SETTINGS_MODULE=mimir.settings.acceptance .venv/bin/python manage.py behave --simple
        --tags=@experts --name='^EXPERTS-REACH-03 Apply the same guest restriction on public detail$' docs/features/act-18-experts/experts-reach-out.feature
      browser_command: E2E_LIVE_SERVER_SCOPE=function .venv/bin/pytest -c tests/e2e/pytest.ini -o addopts= -p no:playwright
        -p no:asyncio -p no:anyio tests/e2e/test_experts_guest_detail.py -x
      make_commands:
      - make test-at-harness
      - make test-at-experts
      expected_exit_code: 0
      reject_zero_skipped_or_undefined: true
    guidance_bundle:
      activity: BPE/BPE-06-Check_Definition_of_Done.md
      rules:
      - do-small-increments
      - do-follow-commit-convention
      - do-github-issues
      - pytest
  scenario_dependencies:
  - S03
  - S07
  - S14
  - S15
  - S17
  - S20
  - S06
  - S21
```

## Lessons Learned

- The same wrapper wording appears in S15/S16 but its interaction obligations differ. One S16-owned server binding plus separate real browser proof avoids duplicate registrations and dishonest simulated coverage.
- Prototype guest mode still possesses fixture email server-side. Production must consume S14 request-local contact and S17 allowlisted public projections.
- Existing browser lifecycle and Bootstrap initialization already solve infrastructure needs; new fixtures or JavaScript would create avoidable duplication.
- Clarify Cedar oracle access during parent convergence once; preserve its raw fixture records or document the single canonical accessor without inventing parallel data loaders.

PIN-04/05 owns issue publication and human GO. Later slices: handoff docs `Refs #N`; server proof `Refs #N`; AT bindings/catalog `Refs #N`; browser proof `Refs #N`; final observed DoD evidence `Closes #N`, each with required approved issue update. No writes, tests, commits or external actions were performed by this worker.

## Structural application evidence

`docs/experts-replay/pin-evidence/S16.json` records positive scaffold selection and deliberate NotImplementedError. Existing callable ASTs were preserved. Browser collection is not interaction certification.
