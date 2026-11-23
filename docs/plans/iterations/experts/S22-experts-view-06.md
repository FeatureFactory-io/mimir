# S22: EXPERTS-VIEW-06 Explain a positive contributor with no public released playbook

This plan uses [the consolidated contract](../pin-convergence-20261123-experts.md). Its shared interfaces, ownership decisions and verification-layer mapping govern this scenario. Commands in the graph below are the canonical execution gates; implementation and test bodies remain unimplemented.

```yaml
scenario: S22
acceptance_id: EXPERTS-VIEW-06
feature_file_path: docs/features/act-18-experts/experts-view.feature
feature_line: 43
primary_execution_layer: at
expanded_case_count: 1
dependencies:
- S17
system_dependencies: []
status: skeleton_applied_unimplemented
source_report_sha256:
- 3acd2eb73e00ffec3b74c19cef89571b167cbdb6eb85dc3d6a7dc991c05f58f7
```

## A — Context map


All references are relative to `/Users/denispetelin/GitHub/mimir-experts-replay`.

| File:lines | Verified relevance |
|---|---|
| `docs/features/act-18-experts/experts-view.feature:43–46` | Exact S22 contract: Sam remains an eligible positive contributor; evidence explicitly explains its absence. |
| `test-data/experts/cedar-rfp-01.json:592–631` | Existing Sam fixture: `skim`, Research, 4,800 total; 4,600 PIP plus 200 Learning; zero released awards; empty public-playbook list. |
| `docs/architecture/SAO.md:3883–3905` | Ledger-derived positive eligibility, currently public released evidence, existing Django delivery and production routes. |
| `methodology/models/playbook.py:84–125` | `can_view` is broader than public evidence eligibility: owners and some authenticated readers can view content that must remain absent here. |
| `templates/mockups/experts/detail.html:5–7` | Existing identity/score hooks, context rail, public-playbook link pattern and exact empty-state recipe. |

Additional verified fixture variant: Maria’s existing public playbook is **6101**, “Accessibility Audit Playbook”, version 1.0 (`cedar-rfp-01.json:114–138`). Her private sentinel already exists separately.

## B — Do not do


- Do not require an authored public released playbook for positive-Karma profile eligibility.
- Do not conflate Sam’s successful profile with S21’s missing/zero-Karma 404 cases.
- Do not alter JSON baseline, tracked seed, award history, categories or totals.
- Do not create another ledger, projection, Cedar loader, HTML parser or production view.
- Do not use prototype fixture dictionaries as the production data source.
- Do not substitute `can_view` for `visibility="public" AND status="released"`.
- Do not generate prose, invoke providers, send contact messages or award points on GET.

## C — Applicable architecture and ownership


Governing headings: **Awards, projections and transaction boundaries**, **Web delivery and notification reuse**, **Test strategy for this delta**, and IA §11 **Exact display contract**.

The user journey explicitly defines positive eligibility independently of evidence availability (`docs/features/user_journey.md:3126–3130,3161–3164`). IA fixes the empty sentence and distinguishes it from a 404 (`docs/ux/IA_guidelines.md:1186–1188`).

S03 supplies real Cedar ORM records, historical projection, shared HTML parsing and baseline/Elena/path bindings. S17 supplies positive-profile eligibility, public detail, approved projection and empty-evidence rendering. S22 only certifies these interfaces.

## D — Tests and exact assertions


| Test / binding | Required assertions |
|---|---|
| `test_expert_detail_with_positive_sam_without_public_playbooks_returns_profile` | Real baseline; authenticate Elena; GET `/experts/skim/`; status 200 without login redirection; H1 “Sam Kim”; `expert-karma-total` exactly “4,800”; primary category Research; stored Sam summary retained; “Public released playbooks” section contains exact empty sentence; no playbook evidence links; award rows unchanged by GET. |
| `test_expert_detail_with_only_ineligible_current_playbook_keeps_positive_profile` | Three independent cases below; GET Maria’s profile returns 200 and “8,200”; current evidence is empty; no `expert-playbook-6101` link; ledger snapshots remain unchanged. |
| `sam_positive_identity` | Existing real response status 200; Sam identity, “4,800” and Research; use shared parser, not fabricated context values. |
| `evidence_section_says` | Exact sentence within actual context rail/evidence section; no evidence View links; response came from production `/experts/skim/`. |
| `test_expert_detail_with_positive_sam_shows_empty_evidence_in_browser` | Real browser login as Elena; navigate production URL; successful HTTP response; identity/4,800 visible; exact empty sentence visible beneath public-evidence heading; no evidence View links. |

**Precisely bounded current-state variants:** restore Cedar independently for each case; obtain existing `dataset.playbooks_by_pk[6101]`; update only its current visibility/status in the runner-owned DB:

| Visibility | Status | Reason excluded |
|---|---|---|
| private | released | Released is insufficient without public visibility. |
| public | draft | Public visibility is insufficient without released status. |
| public | disabled | Authenticated `can_view` may allow this; public evidence must still exclude it. |

Use a test-local ORM update, preserving Maria’s historical 8,200 and existing private record. No release hooks, new historical awards, invented fixture IDs or JSON edits. Baseline Sam remains the literal AT/browser case.

Backend expected count: **4 passed**: one Sam case plus three parameterized current-state cases. Browser: **1 passed**. Named AT: **1 scenario, 4 steps passed**, none undefined/skipped.

## E — Log story


No new log-story rows or log-test command.

Justification: S22 modifies certification assets only. S17 owns the real view’s entry, eligibility/evidence decision and exit logging and its caplog proofs. S22 must not add production logging solely to make a separate test pass. All GET tests additionally verify absence of award writes.

## F — MCP surface


Not applicable. No tool, facade, REST client or registration changes; this contract is production HTTP detail presentation. No MCP initialization work is introduced.

## G — Agent proofs


Not applicable. Rendering existing stored prose does not invoke or extend the §17 contribution-summary capability. PRF-EXPERTS and PRF-OBS remain with S23/S27 and their dependants; no ScriptedLLM fixture or ToolExecutor is required.

## H — Graduation, execution and gates


S17 graduates the existing `templates/mockups/experts/detail.html` recipe into `templates/experts/detail.html`, including the empty branch. S22 adds no template or CSS changes. Its browser proof verifies rendered visibility, while responsive matrix certification remains the existing EXPERTS-VIEW-07 obligation.

Proposed S22 implementation footprint:

- **Create** `tests/integration/test_experts_empty_evidence.py`
- **Create** `docs/features/steps/experts_empty_evidence_steps.py`
- **Create** `tests/e2e/test_experts_empty_evidence.py`
- **Append** two owned phrases and their real-layer mapping to `docs/features/CATALOG.md`

Production footprint: **empty**. Shared files remain S03/S17-owned. Existing scenario text stays unchanged; retain feature-level `@wip` until the aggregate contracts genuinely pass.



The existing `make test-at-experts` excludes `@wip` (`Makefile:121–122`). The named command explicitly selects `@experts` to execute this exact contract during staged implementation. It does not substantiate completion of the aggregate scope.

Use existing function-scoped `page` and `live_server_url` (`tests/e2e/conftest.py:101–117,141–168`), existing browser `login` (`tests/e2e/e2e_helpers.py:14–28`) and S03’s `CEDAR_PASSWORD`. Preserve fixture loading and plugin exclusions. Backend checks and browser checks run separately.

### Full skeleton text

Destination: `tests/integration/test_experts_empty_evidence.py` — **create**.

```python
"""Real-DB certification of positive Experts profiles without eligible evidence."""

import pytest
from django.test import Client

pytestmark = pytest.mark.django_db


def test_expert_detail_with_positive_sam_without_public_playbooks_returns_profile(
    client: Client,
) -> None:
    """Certify Sam's real positive profile and explicit empty evidence.

    :param client: Real Django client. Example: Elena-authenticated client.
    :return: None. Example: status, identity, evidence and no-write checks pass.
    :raises AssertionError: If Sam is rejected, misrepresented or GET awards points.
    """
    raise NotImplementedError()


@pytest.mark.parametrize(
    ("visibility", "status"),
    [("private", "released"), ("public", "draft"), ("public", "disabled")],
)
def test_expert_detail_with_only_ineligible_current_playbook_keeps_positive_profile(
    client: Client, visibility: str, status: str,
) -> None:
    """Certify current evidence filtering without rewriting historical Karma.

    :param client: Real Django client. Example: Elena-authenticated client.
    :param visibility: Current 6101 visibility. Example: "private".
    :param status: Current 6101 status. Example: "released".
    :return: None. Example: Maria remains 8,200 with empty current evidence.
    :raises AssertionError: If ineligible evidence leaks or positive eligibility changes.
    """
    raise NotImplementedError()
```

Destination: `docs/features/steps/experts_empty_evidence_steps.py` — **create**. Reuse S03’s baseline, Elena/path and HTML helpers; do not register duplicate generic bindings.

```python
"""S22-only Django-client assertions; no browser activation or domain mocks."""

from behave import then
from behave.runner import Context


@then("Sam Kim's positive Karma identity is shown")
def sam_positive_identity(context: Context) -> None:
    """Check Sam's identity using the actual response and Cedar oracle.

    :param context: Transactional AT context. Example: response for /experts/skim/.
    :return: None. Example: status 200, Sam Kim, 4,800 and Research verified.
    :raises AssertionError: If positive identity is absent or incorrect.
    """
    raise NotImplementedError()


@then('the evidence section says "{message}"')
def evidence_section_says(context: Context, message: str) -> None:
    """Check exact empty evidence text inside the real evidence section.

    :param context: Real response context. Example: Sam's production profile.
    :param message: Required text. Example: "No public released playbooks to show".
    :return: None. Example: exact message and absence of evidence links verified.
    :raises AssertionError: If text is misplaced, absent or evidence links exist.
    """
    raise NotImplementedError()
```

Destination: `tests/e2e/test_experts_empty_evidence.py` — **create**.

```python
"""Browser certification of the existing positive empty-evidence contract."""

import pytest
from playwright.sync_api import Page

pytestmark = [pytest.mark.e2e, pytest.mark.django_db(transaction=True)]


def test_expert_detail_with_positive_sam_shows_empty_evidence_in_browser(
    page: Page, live_server_url: str,
) -> None:
    """Observe Sam's actual production profile after normal Elena login.

    :param page: Existing fresh browser page. Example: Chromium page.
    :param live_server_url: Existing function-scoped server. Example: http://localhost:8081.
    :return: None. Example: visible positive identity and empty evidence verified.
    :raises AssertionError: If navigation, identity, visibility or evidence is incorrect.
    """
    raise NotImplementedError()
```

Each future test directly calls S03’s loader in its own runner-owned DB scope; support modules are not automatically discovered fixtures. No additional fixture lifecycle or helper method is necessary.

### Delivery boundaries and Lessons Learned

PIN applies raising stubs only; no assertions or production behavior are filled now. PIN-04 publishes A–H and graph with the actual footprint; PIN-05 obtains GO. After GO, use one commit per graph node, `Refs #N` until the final `Closes #N`, with required issue updates through the parent’s authorization process.

- Positive contribution and authored public evidence are separate predicates; Sam is the existing counterexample.
- Maria 6101 provides precise current-state variants without inventing users, ledger events or baseline edits.
- Authenticated `can_view` would incorrectly admit disabled public evidence.
- Feature-level WIP and globally ignored E2E paths make explicit selection and positive execution counts essential.
- No commands, tests, writes or commits were executed by this worker.

## Parent convergence

Authoritative acceptance source: `docs/features/act-18-experts/experts-view.feature:43`; 1 expanded case(s), primary layer `at`. Dependencies: S17. The full scenario includes all composed journey/UAT obligations assigned in the consolidated contract. Shared Make/catalog registration belongs only to S03.

## Canonical feature execution graph

```yaml
feature_execution_graph:
  feature_ref: EXPERTS-VIEW-06
  scenario_id: S22
  scenario_dependencies:
  - S17
  nodes:
  - id: S22-N1-backend-certification
    title: Certify positive eligibility independently of current evidence
    bpe: BPE-02
    depends_on: []
    footprint:
    - tests/integration/test_experts_empty_evidence.py
    tests:
    - test_expert_detail_with_positive_sam_without_public_playbooks_returns_profile
    - test_expert_detail_with_only_ineligible_current_playbook_keeps_positive_profile
    gate:
      command: pytest tests/integration/test_experts_empty_evidence.py -q
      expected_exit_code: 0
      expected_passed: 4
    guidance_bundle:
      activity: BPE/BPE-02-Implement_Backend.md
      rules:
      - do-skeletons-first
      - do-test-first
      - pytest
      - do-not-mock-in-integration-tests
      - do-docstring-format
  - id: S22-N2-acceptance
    title: Bind only the two S22-specific assertions
    bpe: BPE-04
    depends_on:
    - S22-N1-backend-certification
    footprint:
    - docs/features/steps/experts_empty_evidence_steps.py
    gate:
      command: make test-experts-s22-at
      expected_exit_code: 0
      expected_scenarios_passed: 1
      expected_steps_passed: 4
    guidance_bundle:
      activity: BPE/BPE-04-Implement_Feature_Acceptance_Tests.md
      rules:
      - do-test-first
      - pytest
      - do-not-mock-in-integration-tests
  - id: S22-N3-browser
    title: Observe the positive empty-evidence profile in Chromium
    bpe: BPE-05
    depends_on:
    - S22-N2-acceptance
    footprint:
    - tests/e2e/test_experts_empty_evidence.py
    gate:
      command: make test-experts-s22-browser
      expected_exit_code: 0
      expected_passed: 1
    guidance_bundle:
      activity: BPE/BPE-05-Implement_Journey_Certification_Tests.md
      rules:
      - do-test-first
      - pytest
      - do-semantic-versioning-on-ui-elements
  - id: S22-N4-dod
    title: Reconcile certification and non-vacuous execution evidence
    bpe: BPE-06
    depends_on:
    - S22-N3-browser
    footprint: []
    gate:
      command: make test-experts-s22
      supporting_commands:
      - make test-at-harness
      - make test-at-experts
      - ruff check tests/integration/test_experts_empty_evidence.py docs/features/steps/experts_empty_evidence_steps.py
        tests/e2e/test_experts_empty_evidence.py
      - black --check tests/integration/test_experts_empty_evidence.py docs/features/steps/experts_empty_evidence_steps.py
        tests/e2e/test_experts_empty_evidence.py
      expected_exit_code: 0
      requirements:
      - Preserve successful named AT and separate browser results.
      - Harness success alone is not feature success.
      - Aggregate Experts execution must report its actual selected count.
      - Zero selected, skipped or undefined S22 is never completion.
    guidance_bundle:
      activity: BPE/BPE-06-Check_Definition_of_Done.md
      rules:
      - pytest
      - do-follow-commit-convention
      - do-github-issues
```

## Lessons Learned

PIN applies raising stubs only; no assertions or production behavior are filled now. PIN-04 publishes A–H and graph with the actual footprint; PIN-05 obtains GO. After GO, use one commit per graph node, `Refs #N` until the final `Closes #N`, with required issue updates through the parent’s authorization process.

- Positive contribution and authored public evidence are separate predicates; Sam is the existing counterexample.
- Maria 6101 provides precise current-state variants without inventing users, ledger events or baseline edits.
- Authenticated `can_view` would incorrectly admit disabled public evidence.
- Feature-level WIP and globally ignored E2E paths make explicit selection and positive execution counts essential.
- No commands, tests, writes or commits were executed by this worker.

## Structural application evidence

`docs/experts-replay/pin-evidence/S22.json` records positive scaffold selection and deliberate NotImplementedError. Existing callable ASTs were preserved. Browser collection is not interaction certification.

## Actual structural footprint

`docs/experts-replay/pin-evidence/S22.json`, `docs/features/steps/experts_empty_evidence_steps.py`, `docs/plans/iterations/experts/S22-experts-view-06.md`, `tests/e2e/test_experts_empty_evidence.py`, `tests/integration/test_experts_empty_evidence.py`

Skeleton: `36188e3e95cb7199220d8571e9f1168a1d3ec7df`; shared reconciliation: `39d598328d438d09723b6eb14574fbf92fab71c9`. Semantic and physical-file dependencies are recorded separately in the iteration manifest. Context-map line ranges record the workers’ inspection baseline; headers and the final scaffold remain authoritative.
