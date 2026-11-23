# S17: EXPERTS-VIEW-01 Show Maria's identity and full contribution paragraph

This plan uses [the consolidated contract](../pin-convergence-20261123-experts.md). Its shared interfaces, ownership decisions and verification-layer mapping govern this scenario. Commands in the graph below are the canonical execution gates; implementation and test bodies remain unimplemented.

```yaml
scenario: S17
acceptance_id: EXPERTS-VIEW-01
feature_file_path: docs/features/act-18-experts/experts-view.feature
feature_line: 8
primary_execution_layer: at
expanded_case_count: 1
dependencies:
- S03
system_dependencies: []
status: skeleton_applied_unimplemented
source_report_sha256:
- f70c5d1800ac947db0872c38b3b95f5b71b487b7c14a5fe1cf7dbfef549dc015
```

### A — Context map


Verified in `/Users/denispetelin/GitHub/mimir-experts-replay`:

| Reference | Finding |
|---|---|
| `docs/features/act-18-experts/experts-view.feature:8–14` | Exact identity, 8,200, Design and full stored paragraph contract. |
| `test-data/experts/cedar-rfp-01.json:114–119` | Maria’s canonical identity and nine-sentence baseline paragraph; synthetic domain JSON, not a Django fixture. |
| `templates/mockups/experts/detail.html:4–7` | Approved breadcrumb, identity/contact header, unclamped summary and Bootstrap `col-md-8`/`col-md-4` recipe. |
| `methodology/models/playbook.py:94–125` | General `can_view` permits more than public released evidence; public expert evidence requires an explicit `visibility="public", status="released"` filter. |
| `tests/e2e/conftest.py:101–117,154–168` | Existing `context`, `page`, `live_server` and `live_server_url` fixtures; no existing Cedar ORM fixture. |

Production Experts files and `tests/support/experts_data.py` are absent at inspection. Mockup `expert_detail` reads JSON and is not a production implementation.

### B — Do-not-do list


- No summary generation, provider call, summary refresh, ledger award or write during a detail GET.
- Do not reuse own-profile editing/token controls.
- Do not expose raw `User`, `ExpertProfile`, email, private playbook/PIP objects or broad permission-filtered querysets as `person`.
- Do not use cached prose as the source of totals/category.
- Do not line-clamp, shorten, split or append ellipsis to public summary prose.
- Do not serve the prototype route/template as production.
- No SPA, React, new queue, new MCP tool, contact sending or inferred availability.
- Preserve all existing implementations and permissions.

### C — Governing architecture


- **Experts & Karma delivery architecture — planned delta**
  - **Awards, projections and transaction boundaries**
  - **Web delivery and notification reuse**
  - **Test strategy for this delta**
- **Web UI Architecture → UI Design Conventions / Django Implementation Details**
- **Services Layer**
- **§17 → Privacy, bounds and failure policy**: reading stored prose and live numeric projections does not require model execution.
- Act 18, **FOB-EXPERT-VIEW-1**.
- IA §11, including its exact seven viewports.

S03 owns schema, ledger-backed projection, primary-category resolver and real Cedar adapter. S17 adds detail orchestration and presentation only.

**Shared interface requirements to reconcile before applying skeletons**

1. S03 supplies an existing numeric projection for a real user, including integer overall total, resolved primary category, source/category totals and live fallback counts. S17 consumes it; it must not implement another resolver.
2. S03’s adapter stores the exact JSON paragraph in the profile summary field. It must build Maria’s real 8,200 ledger baseline and real public/private evidence; no refreshed model prose or fresh award hooks.
3. Adapter returns real Elena/Maria users and expected stored paragraph to tests. Existing E2E seed remains intact; no assumed fixture named `cedar_baseline`.
4. S17’s `ExpertsService.public_detail` returns an allowlisted presentation payload. S18–S22 add certification or narrowly scoped helpers without requiring S17 to depend on them.
5. S14 later supplies auth-aware contact context and `experts/_reach_out.html`. S17’s public payload contains no email. No S17 → S14 dependency: the detail template can conditionally include the shared contact partial only when contact context exists.
6. S18 supplies shared `_breakdown.html`; S17 reserves its conditional inclusion. Public released evidence, eligibility and empty-evidence architecture are implemented here, with S19/S20/S21/S22 owning additional proof.

### D — Tests and assertions


Proposed `tests/integration/test_expert_detail.py`:

| Test | Required assertion |
|---|---|
| `test_public_detail_with_cedar_maria_returns_identity_and_complete_summary` | Real authenticated Elena GET returns 200 using `experts/detail.html`; title/H1 Maria Rodriguez; total exactly `8,200`; Design badge; paragraph text equals the complete stored nine-sentence value, including its final sentence. |
| `test_public_detail_with_guest_returns_same_public_identity_and_summary` | Anonymous GET returns 200, same public identity/prose; no email in public payload or guest DOM. |
| `test_public_detail_with_html_summary_escapes_untrusted_markup` | Persist HTML-like text through real ORM; response escapes it and never renders executable markup. No `safe`/Markdown conversion. |
| `test_public_detail_with_request_preserves_persisted_state` | GET leaves award count, stored paragraph and refresh metadata unchanged; no interaction trace rows are created. |
| `test_public_detail_with_cedar_baseline_exposes_only_public_projection` | Payload keys are allowlisted, no raw user/profile/queryset; related books all public and released. Additional exhaustive sentinel/eligibility cases remain S20/S21. |
| `test_public_detail_log_story_happy` | Correlated entry → projection → exit logs; no summary, email or private sentinels. |

Proposed `tests/e2e/test_expert_detail.py`:

| Test | Required assertion |
|---|---|
| `test_public_detail_with_full_summary_has_no_visual_truncation` | Real page and stored paragraph match; computed `line-clamp`/`-webkit-line-clamp` are none/unset, overflow does not hide text, text-overflow is not ellipsis, summary height contains its content. |
| `test_public_detail_with_required_viewport_preserves_read_context_recipe` | Seven parameterized viewports; read column before rail in DOM; rail below body below 768px; body/rail beside each other at ≥768px; no page-level overflow or clipping; screenshot evidence and reachable present controls. |

The browser geometry test supplies S17’s part of `EXPERTS-VIEW-07`; complete contact/evidence interactions are jointly certified after S14/S19.

Living-spec bindings add only S17-specific phrases. Reuse the shared Cedar Given, Elena GET, title/testid/category assertions when owned by S03 or another worker; never register duplicate Behave patterns. Bind the full-paragraph assertion to stored ORM content, not a copied string. The no-clamp AT step checks template contract; actual computed styling is Playwright’s responsibility.

Commands, **not executed by this worker**:

```bash
pytest tests/integration/test_expert_detail.py -x
pytest tests/integration/test_expert_detail.py -k log_story -x
pytest -c tests/e2e/pytest.ini -o addopts= tests/e2e/test_expert_detail.py -x
DJANGO_SETTINGS_MODULE=mimir.settings.acceptance .venv/bin/python manage.py behave --simple --name '^EXPERTS-VIEW-01 ' docs/features/act-18-experts/experts-view.feature
```

The focused Behave command deliberately does not exclude inherited `@wip`. Retain WIP until real binding and behavior pass. Do not remove the feature-level tag while sibling contracts remain pending.

### E — Log story


| Where | Beat | Trigger | Required fields |
|---|---|---|---|
| `expert_detail` | entry | Detail GET | `correlation_id`, `authenticated`, `operation=public_expert_detail` |
| `ExpertsService.public_detail` | processing | Real projection assembled | `correlation_id`, `subject_id`, `summary_present`, `public_playbook_count`; no prose |
| `expert_detail` | exit | Render succeeds | Same correlation ID, `status=200`, `template=experts/detail.html` |
| `ExpertsService.public_detail` | branch | Missing/nonpositive subject | Same correlation ID, `reason=missing_or_ineligible`; S21 certifies reject logs |

Use `X-Request-ID` when valid, otherwise generate a bounded correlation identifier. Do not log the raw username path, email, paragraph, evidence bodies or secret sentinels. Use existing `tests/support/log_story.py:assert_log_story`.

### F — MCP


Not applicable. Public HTTP detail only; no facade or tool registration changes.

### G — Agent proofs


Not applicable. This slice reads stored prose and real projections. It neither changes nor invokes the §17 completion pipeline. No ScriptedLLM or agent-proof marker is required.

### H — Template graduation and implementation slices


**Strategy: rewire**, from `templates/mockups/experts/detail.html` into `templates/experts/detail.html`.

- Extend production `base.html`; use its actual content block and shell.
- Replace fixture names and mockup URL reversals with allowlisted projection and existing production reversals.
- Preserve read-first 8+4 layout and full escaped paragraph.
- Use `expert-contribution-summary`, `expert-karma-total`, `expert-primary-category`, `expert-read-column`, `expert-context-rail`, `expert-name`, `expert-back-link` hooks.
- Breadcrumb preserves a valid incoming category where available; otherwise use resolved primary category.
- Evidence links use existing `playbook_detail`, never prototype playbook routes.
- No feature CSS is necessary for Bootstrap grid and ordinary paragraph wrapping. Existing design tokens suffice.
- Contact and breakdown partials have conditional seams so later owners can wire them without circular scenario dependencies.
- PIN placeholder is comment-only; no filled production HTML during skeleton application.

Proposed implementation footprint:



Shared adapter changes belong in S03’s footprint; S17 must not silently add a second adapter. If the reconciled foundation interface lacks stored prose or a usable real adapter, amend S03 before execution.

Commit sequence after PIN-04 handoff and PIN-05 GO:

1. Backend projection/route and real DB tests/log story — `Refs #N`.
2. Graduated template and rendered response tests — `Refs #N`.
3. Living-spec bindings/catalog — `Refs #N`.
4. Browser certification and responsive evidence — `Refs #N`.
5. DoD checkpoint and final issue closure — `Closes #N`.

Each slice requires its commit and authorized issue update before starting the next.

## Parent convergence

Authoritative acceptance source: `docs/features/act-18-experts/experts-view.feature:8`; 1 expanded case(s), primary layer `at`. Dependencies: S03. The full scenario includes all composed journey/UAT obligations assigned in the consolidated contract. Shared Make/catalog registration belongs only to S03.

## Canonical feature execution graph

```yaml
feature_execution_graph:
  feature_ref: EXPERTS-VIEW-01
  nodes:
  - id: N1-public-detail
    title: Add public detail projection and route
    bpe: BPE-02
    depends_on: []
    footprint:
    - methodology/expert_views.py
    - methodology/services/experts_service.py
    - mimir/urls.py
    - tests/integration/test_expert_detail.py
    tests:
    - test_public_detail_with_cedar_baseline_exposes_only_public_projection
    - test_public_detail_with_request_preserves_persisted_state
    - test_public_detail_log_story_happy
    log_story_rows:
    - expert_detail:entry
    - ExpertsService.public_detail:processing
    - expert_detail:exit
    gate:
      command: pytest tests/integration/test_expert_detail.py -k 'projection or persisted_state or log_story'
        -x
      log_story_command: pytest tests/integration/test_expert_detail.py -k log_story -x
    guidance_bundle:
      activity: BPE/BPE-02-Implement_Backend.md
      rules:
      - do-skeletons-first
      - do-test-first
      - do-not-mock-in-integration-tests
      - do-assert-log-story
      - do-write-concise-methods
      - do-docstring-format
  - id: N2-graduate-detail
    title: Render complete public contribution paragraph
    bpe: BPE-03
    depends_on:
    - N1-public-detail
    footprint:
    - templates/experts/detail.html
    - tests/integration/test_expert_detail.py
    mockup_source: templates/mockups/experts/detail.html
    production_template: templates/experts/detail.html
    graduate_strategy: rewire
    tests:
    - test_public_detail_with_cedar_maria_returns_identity_and_complete_summary
    - test_public_detail_with_guest_returns_same_public_identity_and_summary
    - test_public_detail_with_html_summary_escapes_untrusted_markup
    gate:
      command: pytest tests/integration/test_expert_detail.py -x
    guidance_bundle:
      activity: BPE/BPE-03-Implement_Frontend.md
      rules:
      - do-test-first
      - do-semantic-versioning-on-ui-elements
  - id: N3-acceptance
    title: Bind S17 living specification to real Django responses
    bpe: BPE-04
    depends_on:
    - N2-graduate-detail
    footprint:
    - docs/features/steps/experts_detail_steps.py
    - tests/integration/test_expert_detail.py
    tests:
    - test_public_detail_with_cedar_maria_returns_identity_and_complete_summary
    gate:
      command: make test-experts-s17-at
    required_acceptance_command: DJANGO_SETTINGS_MODULE=mimir.settings.acceptance .venv/bin/python manage.py
      behave --simple --name '^EXPERTS-VIEW-01 ' docs/features/act-18-experts/experts-view.feature
    guidance_bundle:
      activity: BPE/BPE-04-Implement_Feature_Acceptance_Tests.md
      rules:
      - do-not-mock-in-integration-tests
      - do-test-first
  - id: N4-browser
    title: Certify complete prose and responsive reading layout
    bpe: BPE-05
    depends_on:
    - N3-acceptance
    footprint:
    - tests/e2e/test_expert_detail.py
    tests:
    - test_public_detail_with_full_summary_has_no_visual_truncation
    - test_public_detail_with_required_viewport_preserves_read_context_recipe
    gate:
      command: make test-experts-s17-browser
    guidance_bundle:
      activity: BPE/BPE-05-Implement_Journey_Certification_Tests.md
      rules:
      - do-semantic-versioning-on-ui-elements
      - do-test-first
  - id: N5-dod
    title: Verify S17 delivery and recorded evidence
    bpe: BPE-06
    depends_on:
    - N4-browser
    footprint: []
    gate:
      command: make test-experts-s17
      log_story_command: pytest tests/integration/test_expert_detail.py -k log_story -x
    required_browser_command: pytest -c tests/e2e/pytest.ini -o addopts= tests/e2e/test_expert_detail.py -x
    required_acceptance_command: DJANGO_SETTINGS_MODULE=mimir.settings.acceptance .venv/bin/python manage.py
      behave --simple --name '^EXPERTS-VIEW-01 ' docs/features/act-18-experts/experts-view.feature
    guidance_bundle:
      activity: BPE/BPE-06-Check_Definition_of_Done.md
      rules:
      - do-test-first
      - do-assert-log-story
      - do-github-issues
  scenario_dependencies:
  - S03
```

## Lessons Learned

The prototype copies the entire fixture person, including private fields, before template rendering. Graduation must replace that data shape with an allowlisted public projection. Likewise, existing general playbook visibility is broader than the public expert evidence contract. The adapter and browser fixtures are not yet implemented; naming an assumed Cedar fixture would conceal a real prerequisite. No files were written, tests run or provider calls made.

## Structural application evidence

`docs/experts-replay/pin-evidence/S17.json` records positive scaffold selection and deliberate NotImplementedError. Existing callable ASTs were preserved. Browser collection is not interaction certification.

## Actual structural footprint

`docs/experts-replay/pin-evidence/S17.json`, `docs/features/steps/experts_detail_steps.py`, `docs/plans/iterations/experts/S17-experts-view-01.md`, `methodology/expert_views.py`, `methodology/services/experts_service.py`, `mimir/urls.py`, `templates/experts/detail.html`, `tests/e2e/test_expert_detail.py`, `tests/integration/test_expert_detail.py`

Skeleton: `f042c884552a15c127982b6a2e1b7cde07744cb7`; shared reconciliation: `39d598328d438d09723b6eb14574fbf92fab71c9`. Semantic and physical-file dependencies are recorded separately in the iteration manifest. Context-map line ranges record the workers’ inspection baseline; headers and the final scaffold remain authoritative.
