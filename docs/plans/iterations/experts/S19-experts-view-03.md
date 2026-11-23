# S19: EXPERTS-VIEW-03 Follow relevant public released evidence

This plan uses [the consolidated contract](../pin-convergence-20261123-experts.md). Its shared interfaces, ownership decisions and verification-layer mapping govern this scenario. Commands in the graph below are the canonical execution gates; implementation and test bodies remain unimplemented.

```yaml
scenario: S19
acceptance_id: EXPERTS-VIEW-03
feature_file_path: docs/features/act-18-experts/experts-view.feature
feature_line: 22
primary_execution_layer: at
expanded_case_count: 1
dependencies:
- S17
system_dependencies: []
status: converged_plan_unapplied
source_report_sha256:
- a246e8f16967da616a2263b54fe42d21d2adb41db0088a7fd129811e4f0a7893
```

## A — Context map


| Verified location | Implementor context |
|---|---|
| `docs/features/act-18-experts/experts-view.feature:22-26` | Exact goal: follow Accessibility Audit Playbook v1.0 to `/playbooks/6101/` and inspect its workflow. |
| `test-data/experts/cedar-rfp-01.json:120-138` | Maria’s public playbook 6101 contains Lead an Accessibility Review and three activities; private sentinels are separate. |
| `methodology/models/playbook.py:84-125` | `can_view()` permits owners/team members and authenticated public non-draft readers; this is broader than public released evidence eligibility. |
| `methodology/playbook_views.py:334-381` | Existing guest-readable detail obtains real workflows, applies existing authorization and renders `playbooks/detail.html`. |
| `methodology/workflow_views.py:117-184` | Existing workflow detail checks playbook membership, retrieves real activities and renders their graph. |

Additional inspected anchors: `methodology/playbook_urls.py:28`, `methodology/workflow_urls.py:10`, `templates/playbooks/detail.html:320-328`, `templates/workflows/detail.html:90-132`, `tests/integration/test_guest_playbook_browse.py:187-200`, and `tests/e2e/conftest.py:101-168`.

## B — Do not do


- S19 certifies existing S03/S17 delivery. Do not create another evidence query, DTO, authorization filter, route or production template.
- S17 owns explicit `visibility="public"` **and** `status="released"` filtering and allowlisted detail projection. Do not substitute `can_view()` for that filter.
- Follow the rendered real anchor; do not manufacture `/playbooks/6101/` as the request instead of checking its href.
- Do not use `/mockups/`, mocked responses, fixtures masquerading as rendered pages, or simulated AT clicks.
- S20 owns exhaustive omission of private titles/content, tokens and other non-allowlisted fields. Preserve that dependency boundary.
- Do not change existing guest authorization, PIP permissions, activity graph behavior, seed schema or release/versioning.
- Do not replace existing working functions with raising stubs.
- No provider calls, tool registration, queue, email or contact behavior belongs here.

## C — Governing architecture


SAO headings: **Security & Access Control → FOB**, **Guest read security**, **E2E Testing with Playwright**, **Experts & Karma delivery architecture — planned delta → Awards, projections and transaction boundaries / Web delivery and notification reuse / Test strategy for this delta**.

IA §11 requires real evidence links with stable test IDs and accessible names. The existing public playbook/workflow screens remain authoritative destinations.

S03 supplies real Cedar ORM objects, historical release/version data, shared HTML parser and generic opening bindings. S17 supplies the public detail and `expert-playbook-6101` anchor. Certification consumes those completed contracts.

## D — Tests and assertions


| Test/binding | Required assertions |
|---|---|
| `test_public_evidence_with_cedar_release_links_existing_detail_route` | Parametrize Elena and anonymous visitor. GET real expert detail → 200; find `expert-playbook-6101`; associate title Accessibility Audit Playbook and version 1.0 with that evidence item; href equals reversed existing playbook-detail route and `/playbooks/6101/`; GET extracted href without redirect → 200; actual detail contains title, public/released badges and v1.0. |
| `test_public_evidence_with_followed_workflow_exposes_cedar_activities` | For both visitor modes, follow the real evidence href, find the actual Lead an Accessibility Review workflow link in returned detail, follow it → 200; workflow belongs to playbook 6101; real activities include Trace Keyboard Focus, Review Form Feedback and Document Recovery Paths. |
| Exact S19 Behave contract | Four distinct bindings below; real Django client follows extracted local href and real workflow link. Assert route/status/template and both activity names from the returned workflow response; no browser imports. |
| `test_public_evidence_with_real_browser_navigation_reaches_cedar_workflow` | Parametrize Elena/guest. Existing live server/page/context; authenticated case uses existing login helper and `CEDAR_PASSWORD`. Click actual evidence anchor, assert final URL and 200 document response; click actual workflow anchor and assert both required activities are visible/readable. Confirm third Cedar activity exists in the real workflow evidence. |

Use `load_cedar_baseline()` in fixtures before browser execution. Reuse `find_by_test_id()` and `element_text()` from S03; no additional parser class. Do not assert merely that fixture JSON contains the expected strings.

Expected backend collection: four cases. Browser collection: two cases. Exact AT: one scenario/five steps including Background. Zero collection, undefined/skipped steps or skipped cases fail delivery certification.

**Commands, proposed Make targets:**

```make
# Destination: Makefile; append during BPE, reserve comments only during PIN.
.PHONY: test-at-experts-view-03 test-e2e-experts-view-03 test-experts-view-03

test-at-experts-view-03:
	DJANGO_SETTINGS_MODULE=mimir.settings.acceptance $(PYTHON) manage.py behave --simple --tags=@experts --name='^EXPERTS-VIEW-03 Follow relevant public released evidence$$' docs/features/act-18-experts/experts-view.feature

test-e2e-experts-view-03:
	E2E_LIVE_SERVER_SCOPE=function $(PYTEST) -c tests/e2e/pytest.ini -o addopts= -p no:playwright -p no:asyncio -p no:anyio tests/e2e/test_experts_public_evidence.py -x

test-experts-view-03:
	$(PYTEST) tests/integration/test_experts_public_evidence.py -x
	$(MAKE) test-at-experts-view-03
	$(MAKE) test-e2e-experts-view-03
```

The explicit `@experts` selection overrides inherited WIP exclusion for this exact contract. Do not remove feature-level `@wip` prematurely: the aggregate `make test-at-experts` remains a later all-contract gate. Do not scan unrelated legacy feature directories.

## E — Log story


`log_story_script: []`, `log_tests: []`; no `log_story_command`.

Justification: S19 introduces certification tests and bindings only, with no production methods or new decision points. S17 owns expert-read/evidence projection observability; existing destination views retain their logging. Test-runner activity is not a new product log story.

## F — MCP tools


Not applicable. S19 changes no MCP tool, facade, REST endpoint, registration or startup wiring. Public web navigation does not imply anonymous MCP access.

## G — Agent proofs


Not applicable. SAO §17’s bounded summary completion belongs to S23/S27 and related summary scenarios. S19 reads existing stored/public evidence and invokes no LLM, agent workflow or ToolExecutor.

## H — Mockup graduation


Reference: `templates/mockups/experts/detail.html:7`; its evidence item is the recipe, while its `mockup_experts_playbook` destination is a prototype.

Graduation is owned by S17: production `templates/experts/detail.html` must link the existing `playbook_detail` route using safe projected evidence. S19 verifies that graduation through the actual href and existing playbook/workflow screens. No S19 template, CSS, JavaScript or mockup-copy footprint is required. Responsive detail geometry remains with the dedicated detail/browser certification owners.

## Parent convergence

Authoritative acceptance source: `docs/features/act-18-experts/experts-view.feature:22`; 1 expanded case(s), primary layer `at`. Dependencies: S17. The full scenario includes all composed journey/UAT obligations assigned in the consolidated contract. Shared Make/catalog registration belongs only to S03.

## Canonical feature execution graph

```yaml
feature_execution_graph:
  feature_ref: EXPERTS-VIEW-03
  scenario_id: S19
  dependencies:
  - S03
  - S17
  nodes:
  - id: S19-N1-real-route-proof
    title: Certify real evidence and destination contracts
    bpe: BPE-02
    depends_on: []
    footprint:
    - tests/integration/test_experts_public_evidence.py
    tests:
    - test_public_evidence_with_cedar_release_links_existing_detail_route
    - test_public_evidence_with_followed_workflow_exposes_cedar_activities
    gate:
      command: pytest tests/integration/test_experts_public_evidence.py -x
    guidance_bundle:
      activity: BPE/BPE-02-Implement_Backend.md
      rules:
      - do-skeletons-first
      - do-test-first
      - do-not-mock-in-integration-tests
      - do-informative-logging
      - do-assert-log-story
      - do-import-on-module-level
      - do-write-concise-methods
      - do-docstring-format
      - do-follow-commit-convention
      - do-small-increments
      - pytest
    notes: Certification only; no production change or new log-story rows.
  - id: S19-N2-living-contract
    title: Bind exact public-evidence acceptance scenario
    bpe: BPE-04
    depends_on:
    - S19-N1-real-route-proof
    footprint:
    - docs/features/steps/experts_evidence_steps.py
    gate:
      command: make test-experts-s19-at
    guidance_bundle:
      activity: BPE/BPE-04-Implement_Feature_Acceptance_Tests.md
      rules:
      - do-not-mock-in-integration-tests
      - do-runner
      - do-test-first
      - do-test-fixture-data-management
      - pytest
  - id: S19-N3-browser-follow
    title: Follow actual evidence and workflow links as Elena and guest
    bpe: BPE-05
    depends_on:
    - S19-N2-living-contract
    footprint:
    - tests/e2e/test_experts_public_evidence.py
    tests:
    - test_public_evidence_with_real_browser_navigation_reaches_cedar_workflow
    gate:
      command: make test-experts-s19-browser
    guidance_bundle:
      activity: BPE/BPE-05-Implement_Journey_Certification_Tests.md
      rules:
      - do-not-mock-in-integration-tests
      - do-runner
      - do-test-first
      - do-test-fixture-data-management
      - do-semantic-versioning-on-ui-elements
      - pytest
  - id: S19-N4-dod
    title: Certify nonempty real acceptance and browser results
    bpe: BPE-06
    depends_on:
    - S19-N3-browser-follow
    footprint: []
    gate:
      command: make test-experts-s19
    guidance_bundle:
      activity: BPE/BPE-06-Check_Definition_of_Done.md
      rules:
      - do-test-first
      - do-continuous-testing
      - do-write-concise-methods
      - do-import-on-module-level
      - do-informative-logging
      - do-assert-log-story
      - do-not-mock-in-integration-tests
      - do-follow-commit-convention
      - do-semantic-versioning-on-ui-elements
      - do-write-scenarios
      - do-add-todos-for-incomplete-items
      - pytest
    manual_checks:
    - Review real href and accessible link name
    - verify no skipped or undefined cases
    - record commit and environment
    - review Lessons Learned
  scenario_dependencies:
  - S17
```

## Lessons Learned

Proposed footprint: the three new Python files above; append-only `Makefile` and `docs/features/CATALOG.md`; parent-authored `docs/plans/experts/S19-EXPERTS-VIEW-03.md`. No migration, seed or production footprint. Shared append files must be serialized during convergence.

PIN-04 owns issue publication and docs handoff; PIN-05 owns human GO. Then four node commits use Angular format and `Refs #N`; final certified commit uses `Closes #N`. Required issue updates cite each slice SHA, result and next node. No commit/issue operation was performed here.

**Lessons Learned:** Existing guest routes already provide the destination behavior; the missing feature boundary is the Experts evidence projection, owned by S17. `can_view()` alone would admit broader authenticated content. A prototype evidence button can look correct while pointing to a mockup, so certification must follow the rendered production href through both existing screens. Existing local BPE-05 prose describes an obsolete Behave E2E runner; actual repository Playwright fixtures/settings and the replay precedence govern these browser gates.
