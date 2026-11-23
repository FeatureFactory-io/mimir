# S04: EXPERTS-LIST-04 Show readable contribution signals and actions

This plan uses [the consolidated contract](../pin-convergence-20261123-experts.md). Its shared interfaces, ownership decisions and verification-layer mapping govern this scenario. Commands in the graph below are the canonical execution gates; implementation and test bodies remain unimplemented.

```yaml
scenario: S04
acceptance_id: EXPERTS-LIST-04
feature_file_path: docs/features/act-18-experts/experts-list.feature
feature_line: 41
primary_execution_layer: at
expanded_case_count: 1
dependencies:
- S03
- S17
- S14
system_dependencies: []
status: converged_plan_unapplied
source_report_sha256:
- 194b49d1f30a67dcd642c8fa1423970cfc46d4a60db03fe4067a8a9958028ce7
```

## A — Context map


| Verified source | Lines | Implementation relevance |
|---|---:|---|
| `docs/features/act-18-experts/experts-list.feature` | 41–47 | Maria’s card: rank 2, name, 8,200 total, Design, accessibility hint and actions. |
| `templates/mockups/experts/list.html` | 13–19 | Existing card recipe, identity, score and stable action selectors to graduate. |
| `mockups/experts_views.py` | 38–58 | Prototype uses full stored prose or numeric fallback; production must replace fixture-derived numbers with live projections. |
| `docs/ux/IA_guidelines.md` | 1172–1218 | Only hints may be visually clamped; seven exact viewports; Mike’s exact fallback. |
| `docs/architecture/SAO.md` | 3875–3906 | Public projections, no inferred suitability, Django/Bootstrap delivery, authenticated contact and real acceptance tests. |

Actual source findings: production Experts behavior is absent; the DEBUG prototype is functional design evidence. `templates/base.html` already loads `static/css/mimir-app.css`, Bootstrap and the shared design system. Existing browser fixtures are named `page` and `live_server_url`; they must remain intact.

## B — Do not do


- Do not change ranking, eligibility, primary-category resolution or award accounting.
- Do not generate summaries, call an LLM or infer availability, certification or suitability.
- Do not copy fixture dictionaries into production context.
- Do not expose User objects, email, tokens or private evidence through this presenter.
- Do not truncate stored text in Python or clamp names, scores or public detail prose.
- Do not recreate contact policy: consume S14’s context and shared partial.
- Do not alter or remove DEBUG mockups, their banner, inventory or existing design-system rules.

Maria’s stored paragraph explicitly says availability and project fit require a conversation. Tests must preserve that caveat; banning every occurrence of “availability” would incorrectly reject the approved prose.

## C — Governing architecture and interfaces


Applicable SAO headings: **Web UI Architecture → UI Design Conventions**, **Architecture Pattern**, **Experts & Karma delivery architecture → Awards, projections and transaction boundaries**, **Web delivery and notification reuse**, and **Test strategy for this delta**. Section 17’s display boundary applies: numeric fallback is live and display never triggers another model completion.

Canonical S03 contract, confirmed by the parent:

```python
ExpertProjection(
    user_id: int,
    username: str,
    display_name: str,
    total_points: int,
    primary_category: str,
    category_points: tuple[tuple[str, int], ...],
    source_points: tuple[tuple[str, int], ...],
    released_public_playbook_count: int,
    successful_gui_copy_count: int,
)
```

`ExpertsService.project_user(...) -> ExpertProjection` remains S03-owned. S04 consumes that entire allowlisted interface, without redefining it. S03 owns independent live count queries and `event_channel`: GUI-copy author awards count toward `successful_gui_copy_count`; MCP detail/export awards do not. Mike’s 47 GUI copies must not become his 470 author-consumption awards.

S04 adds an immutable presentation result, using the stored public paragraph when nonblank and otherwise exactly:

`<released_public_playbook_count> released playbooks · <successful_gui_copy_count> copies`

For Mike: **2 released playbooks · 47 copies**.

Pseudocode: validate projection → choose existing public prose or live fallback → derive initials → format total/category → return allowlisted presentation. The view joins presentations with S14’s separate authenticated contact contexts. CSS supplies the two-line visual clamp.

## D — Tests, assertions and implementation slices


All tests use real Cedar data through `load_cedar_baseline() -> CedarDataset`; access users through `users_by_username`, playbooks through `playbooks_by_pk` and expectations through `oracle`. Preserve existing pytest and browser setup.

| Planned test | Concrete assertion |
|---|---|
| `test_present_with_stored_summary_preserves_public_prose` | Full original paragraph retained; Maria’s identity/initials, Design and 8,200 formatted total correct; no extra recommendation fields. |
| `test_present_with_missing_summary_uses_live_numeric_fallback` | `None`, empty and whitespace summaries use counts; Mike yields exact 2/47 fallback; changed projection counts immediately change hint. |
| `test_present_with_invalid_projection_rejects_input` | Negative/noninteger counts, nonpositive totals, blank identity and unknown categories fail clearly; booleans do not pass as counts. |
| `test_experts_card_with_cedar_baseline_shows_readable_signals` | Real GET scopes assertions to Maria’s article: rank 2, full name, 8,200 rather than 7,200, Design, escaped complete stored paragraph in hint DOM, initials, correct profile href and S14 contact control. |
| `test_experts_card_with_stored_caveat_adds_no_suitability_claim` | Exact approved prose retained; no computed availability/suitability/recommendation field, badge or extra claim. |
| `test_expert_card_log_story_happy` | Stored-summary and live-count branches emit E’s beats without paragraph/email/private sentinel content. |
| `test_expert_card_log_story_reject` | Invalid projection emits entry/reject beats, no successful exit or sensitive values. |
| `test_experts_cards_with_required_viewports_keep_actions_readable` | Seven viewports × normal, long-name/prose and missing-summary states; identity/score readable, hints at most two visible lines, both actions reachable, no overlap or horizontal overflow; keyboard order follows visual rank. |
| `test_experts_card_with_view_profile_opens_full_evidence` | Maria’s View profile opens S17 route; full untruncated stored paragraph appears. |
| `test_experts_cards_with_reviewed_visual_evidence_cover_required_states` | Current implementation screenshots and review records cover required states/viewports, identify environment/commit/reviewer, and record defects; prototype captures cannot satisfy this gate. |

AT: own only these four exact Then phrases in `docs/features/steps/experts_card_steps.py`:

1. `card "{card_id}" shows rank {rank:d} and "{display_name}"`
2. `it shows total "{total}", category "{category}", and an accessibility contribution hint`
3. `it has an avatar or initials plus View profile and Reach out controls`
4. `it makes no availability or suitability assertion`

Reuse S03 baseline/open-path bindings and common S01 bindings when referenced; register no duplicates. Scope HTML extraction to the requested card’s `<article>` and compare actual HTTP output. Browser geometry belongs exclusively to Playwright.

Proposed Make targets:

- `test-at-experts-s04`: acceptance settings, real Behave simple runner, exact scenario name `^EXPERTS-LIST-04 Show readable contribution signals and actions$`, explicit `@experts` selection to execute this named WIP contract.
- `test-experts-s04`: integration file, that AT target, then browser file using `pytest -o addopts=`.

Slices after GO: presentation + log proofs; view/template/CSS; AT; browser and visual certification; DoD. Each slice uses `Refs #N`; final passing slice uses `Closes #N`. PIN-04/05 owns issue/handoff/GO.

## E — Log story


Logger: `methodology.services.expert_card_presentation`; `where=ExpertCardPresentationService.present`.

| Beat | Trigger | Required fields |
|---|---|---|
| entry | Presentation requested | `entry`, `subject_id=`, `correlation_id=` |
| branch | Nonblank stored public summary | `branch`, `hint_source=stored_summary`, `reason=stored_public_prose` |
| branch | Missing/blank summary | `branch`, `hint_source=live_counts`, `reason=no_stored_public_prose` |
| exit | Successful projection | `exit`, `status=ok`, `subject_id=`, `correlation_id=` |
| validation | Invalid projection | `validation`, `status=rejected`, `reason=invalid_projection`, `correlation_id=` |

Use `caplog` and existing `tests/support/log_story.py::assert_log_story`. Never log names, usernames, prose, email or projection contents. Carry the view’s request correlation ID into the presenter.

## F — MCP


Not applicable. This scenario changes public web presentation only; no tool, facade registration or MCP client behavior changes.

## G — Agent proofs


Not applicable. No agent capability, provider boundary, prompt, generation or persisted trace changes. S23/S27 own summary proofs; seeded stored prose proves this display contract independently.

## H — Mockup graduation


| Source | Target | Strategy |
|---|---|---|
| `templates/mockups/experts/list.html` | `templates/experts/list.html` | Partial: graduate card identity/hint/score/action layout into S03’s list foundation. |
| `templates/mockups/experts/base.html` | `static/css/mimir-app.css` | Partial: scoped card sizing/wrapping and hint clamp, retaining shared tokens. |
| `templates/mockups/experts/_reach_out.html` | `templates/experts/_reach_out.html` | S14-owned; include its actual production partial. |

Use existing `experts-card-<username>`, `expert-card-karma`, `experts-view-profile-<username>` and S14 contact selectors. Add `experts-card-hint-<username>` and `experts-card-initials-<username>`. Initials satisfy the accepted avatar alternative without introducing avatar storage or remote fetches.

Use a scoped CSS variable such as `--experts-hint-lines: 2`; preserve token-derived colors and existing `hg-card`, Bootstrap button/badge classes. Names and scores wrap or retain readable width; narrow action clusters stack underneath. Preserve all existing stylesheet content.

PIN materialization adds only comments to existing template/CSS/view bodies and uncalled raising helpers. It must not replace S03 working bodies with stubs. Future implementation evidence belongs in new `docs/ux/experts-card-implementation-evidence.json`; preserve ESM evidence.

## Parent convergence

Authoritative acceptance source: `docs/features/act-18-experts/experts-list.feature:41`; 1 expanded case(s), primary layer `at`. Dependencies: S03, S17, S14. The full scenario includes all composed journey/UAT obligations assigned in the consolidated contract. Shared Make/catalog registration belongs only to S03.

## Canonical feature execution graph

```yaml
feature_execution_graph:
  feature_ref: EXPERTS-LIST-04
  nodes:
  - id: N1-card-presentation
    title: Present stored contribution prose and live fallback
    bpe: BPE-02
    depends_on: []
    footprint:
    - methodology/services/expert_card_presentation.py
    - tests/integration/test_expert_card_presentation.py
    tests:
    - test_present_with_stored_summary_preserves_public_prose
    - test_present_with_missing_summary_uses_live_numeric_fallback
    - test_present_with_invalid_projection_rejects_input
    - test_expert_card_log_story_happy
    - test_expert_card_log_story_reject
    log_story_rows:
    - ExpertCardPresentationService.present:entry
    - ExpertCardPresentationService.present:branch
    - ExpertCardPresentationService.present:exit
    - ExpertCardPresentationService.present:validation
    gate:
      command: pytest tests/integration/test_expert_card_presentation.py -x
      log_story_command: pytest tests/integration/test_expert_card_presentation.py -k log_story -x
    guidance_bundle:
      activity: BPE/BPE-02-Implement_Backend.md
      rules:
      - do-skeletons-first
      - do-test-first
      - do-informative-logging
      - do-assert-log-story
  - id: N2-card-template
    title: Graduate readable cards and shared actions
    bpe: BPE-03
    depends_on:
    - N1-card-presentation
    footprint:
    - methodology/expert_views.py
    - static/css/mimir-app.css
    - templates/experts/list.html
    - tests/integration/test_expert_cards.py
    tests:
    - test_experts_card_with_cedar_baseline_shows_readable_signals
    - test_experts_card_with_stored_caveat_adds_no_suitability_claim
    mockup_source: templates/mockups/experts/list.html
    production_template: templates/experts/list.html
    graduate_strategy: partial
    gate:
      command: pytest tests/integration/test_expert_cards.py -x
    guidance_bundle:
      activity: BPE/BPE-03-Implement_Frontend.md
      rules:
      - do-test-first
      - do-semantic-versioning-on-ui-elements
  - id: N3-card-acceptance
    title: Bind the exact readable-card contract
    bpe: BPE-04
    depends_on:
    - N2-card-template
    footprint:
    - docs/features/steps/experts_card_steps.py
    gate:
      command: make test-experts-s04-at
    guidance_bundle:
      activity: BPE/BPE-04-Implement_Feature_Acceptance_Tests.md
      rules:
      - do-test-first
      - do-not-mock-in-integration-tests
  - id: N4-card-certification
    title: Certify responsive cards and visual fidelity
    bpe: BPE-05
    depends_on:
    - N3-card-acceptance
    footprint:
    - docs/ux/experts-card-implementation-evidence.json
    - tests/e2e/test_expert_cards.py
    - tests/integration/test_expert_card_visual_evidence.py
    gate:
      command: make test-experts-s04-browser
    guidance_bundle:
      activity: BPE/BPE-05-Implement_Journey_Certification_Tests.md
      rules:
      - do-test-first
      - do-semantic-versioning-on-ui-elements
  - id: N5-card-done
    title: Verify the complete card contract
    bpe: BPE-06
    depends_on:
    - N4-card-certification
    footprint: []
    gate:
      command: make test-experts-s04
      log_story_command: pytest tests/integration/test_expert_card_presentation.py -k log_story -x
    guidance_bundle:
      activity: BPE/BPE-06-Check_Definition_of_Done.md
      rules:
      - do-test-first
      - do-assert-log-story
  scenario_dependencies:
  - S03
  - S17
  - S14
```

## Lessons Learned

No infrastructure or scope-removal proposal. Parent must normalize S03’s DTO import and ExpertProfile summary field during sequential materialization; S04 introduces no duplicate projection or schema.

The prototype’s numeric fallback is a design recipe, not a permissible production data source. GUI-copy channel separation is necessary to preserve Mike’s 47-copy meaning. CSS-only truncation keeps public prose stable while making cards readable. Shared contact policy prevents public presentation from accidentally leaking email. Existing global pytest configuration ignores `tests/e2e`, so explicit `-o addopts=` is essential to collect the browser gate.

No source writes, commits, tests or browser runs were performed.
