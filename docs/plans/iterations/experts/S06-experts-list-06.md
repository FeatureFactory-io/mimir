# S06: EXPERTS-LIST-06 Explain an empty category

This plan uses [the consolidated contract](../pin-convergence-20261123-experts.md). Its shared interfaces, ownership decisions and verification-layer mapping govern this scenario. Commands in the graph below are the canonical execution gates; implementation and test bodies remain unimplemented.

```yaml
scenario: S06
acceptance_id: EXPERTS-LIST-06
feature_file_path: docs/features/act-18-experts/experts-list.feature
feature_line: 54
primary_execution_layer: at
expanded_case_count: 1
dependencies:
- S03
system_dependencies: []
status: skeleton_applied_unimplemented
source_report_sha256:
- b8a05dcf48d7d896379c863efc94ef4fd1607fe2cae6109c9a34e5a6d68abc7f
```

## A — Context map


| Actual reference | Implementation relevance |
|---|---|
| `docs/features/act-18-experts/experts-list.feature:54–57` | Exact request, absence of cards and required message. |
| `templates/mockups/experts/list.html:6–21` | Existing category links, leaderboard container and generic `{% empty %}` branch with `experts-empty`. |
| `test-data/experts/cedar-rfp-01.json:657–685` | Five category names; `expected_other_order` is empty. |
| `docs/architecture/SAO.md:3883–3928` | Real ledger projections, production Django routes, real-client AT and separate browser certification. |
| `docs/ux/IA_guidelines.md:1167–1204` | Exact message, stable selectors and seven viewport profiles. |

Also inspected replay AGENTS/CLAUDE, supplied PIN guidance/ownership/GitHub rules, Act 18 journey, prototype view, acceptance lifecycle/catalog, Makefile, graph schema, pytest configurations and actual browser fixtures/helpers.

## B — Do not do


- Do not add an empty-category service, alternate query, hardcoded Other response or fixture-backed production view.
- Do not introduce models, migrations, provider calls, awards, notifications, MCP tools or permissions.
- Do not infer availability, suitability or certification from an empty ranking.
- Do not modify `/mockups/` or certify those routes as implemented Experts behavior.
- Do not duplicate S03 baseline/open-path bindings, S01 URL bindings or S03 HTML parser.
- Do not replace existing working methods with raising stubs.
- Do not mark zero/skipped AT cases as delivery evidence.

## C — Applicable architecture


SAO **Experts & Karma delivery architecture — planned delta**, especially **Awards, projections and transaction boundaries**, **Web delivery and notification reuse**, and **Test strategy for this delta**.

S03 owns complete production list architecture, including query/category selection and graduation of the existing generic empty branch. The production contract required here is:

1. A real GET `/experts/?category=other` succeeds with HTTP 200.
2. Other remains the selected category; its category link has `aria-current="page"`.
3. `experts-leaderboard` contains zero `experts-card-*` elements.
4. `experts-empty` contains exactly `No experts in Other yet — release a playbook to be the first`.
5. An eligible populated category does not display this empty-state element.

No S06 production change is necessary once S03 graduates that complete recipe. S06 owns dedicated certification.

Pseudocode: load real isolated Cedar records → request production route → parse actual HTML through S03 helpers → assert current category, zero cards and exact message → repeat in browser at required widths.

## D — Tests to create


| Test/binding | Assertions |
|---|---|
| `test_experts_other_with_baseline_renders_exact_empty_state` | Parameterized authenticated Elena/anonymous client; HTTP 200, Other current, zero card elements and exact message. Real ORM baseline and production view; no mocked collaborators. |
| `test_experts_design_with_baseline_omits_empty_state` | Positive control: HTTP 200, Design current, five actual cards and no `experts-empty`. Prevents unconditional empty-state rendering. |
| `no_contributor_cards` | Exact existing Gherkin phrase; checks response status and absence of cards in leaderboard. |
| `other_empty_message` | Exact existing Gherkin message phrase; checks rendered element text and Other current state. |
| `test_experts_other_with_responsive_viewport_shows_empty_state` | Actual authenticated browser, exact message visible, zero cards, Other current and no page-level horizontal overflow across all seven IA profiles. |

Shared parsing: `find_by_test_id`, `element_text`, `_walk_elements` in S03-owned `tests/support/experts_html.py`, implemented with Django `parse_html`. No additional parser.

Browser fixtures are the existing `page` and `live_server_url`; reuse `e2e_helpers.login`, S03 `load_cedar_baseline()` and fictional `CEDAR_PASSWORD`. Preserve existing fixture loading and live-server lifecycle.

Exact AT target explicitly selects `@experts` and the named scenario despite feature-level `@wip`; do not weaken the aggregate target.

## E — Log story


Empty for this scenario. S06 adds tests and acceptance bindings only; no production decision point or operation is introduced. S03 owns list/query logging and its matching caplog proof. Do not invent a second logging implementation or count AT harness logs as production observability.

Accordingly, no `log_tests` or `log_story_command` is declared.

## F — MCP tools


Not applicable. This is certification of an existing planned web list contract.

## G — Agent proofs


Not applicable. No summary generation, LLM port, provider, tool wiring or agent capability changes.

## H — Mockup graduation


S03 owns `templates/mockups/experts/list.html` → `templates/experts/list.html`, including the existing generic empty-loop recipe and `experts-empty` selector. S06 adds no frontend node or production template footprint.

If S03 omits that branch, reconcile the shared architecture before applying skeletons; do not create a parallel S06 rendering path.

## Parent convergence

Authoritative acceptance source: `docs/features/act-18-experts/experts-list.feature:54`; 1 expanded case(s), primary layer `at`. Dependencies: S03. The full scenario includes all composed journey/UAT obligations assigned in the consolidated contract. Shared Make/catalog registration belongs only to S03.

## Canonical feature execution graph

```yaml
feature_execution_graph:
  feature_ref: EXPERTS-LIST-06
  nodes:
  - id: N1-backend-contract
    title: Prove the production empty-list HTTP contract
    bpe: BPE-02
    depends_on: []
    footprint:
    - tests/integration/test_experts_empty_category.py
    - tests/support/experts_html.py
    tests:
    - test_experts_other_with_baseline_renders_exact_empty_state
    - test_experts_design_with_baseline_omits_empty_state
    gate:
      command: make test-experts-s06-backend
    guidance_bundle:
      activity: BPE/BPE-02-Implement_Backend.md
      rules:
      - do-skeletons-first
      - do-test-first
      - do-not-mock-in-integration-tests
  - id: N2-acceptance
    title: Bind and run the exact living contract
    bpe: BPE-04
    depends_on:
    - N1-backend-contract
    footprint:
    - docs/features/steps/experts_empty_steps.py
    gate:
      command: make test-experts-s06-at
    guidance_bundle:
      activity: BPE/BPE-04-Implement_Feature_Acceptance_Tests.md
      rules:
      - do-test-first
      - do-not-mock-in-integration-tests
  - id: N3-browser
    title: Certify the actual empty screen at seven viewports
    bpe: BPE-05
    depends_on:
    - N2-acceptance
    footprint:
    - tests/e2e/test_experts_empty_category.py
    gate:
      command: make test-experts-s06-browser
    guidance_bundle:
      activity: BPE/BPE-05-Implement_Journey_Certification_Tests.md
      rules:
      - do-test-first
      - do-semantic-versioning-on-ui-elements
  - id: N4-dod
    title: Verify complete empty-category certification
    bpe: BPE-06
    depends_on:
    - N3-browser
    footprint: []
    gate:
      command: make test-experts-s06
    guidance_bundle:
      activity: BPE/BPE-06-Check_Definition_of_Done.md
      rules:
      - do-test-first
      - do-follow-commit-convention
  scenario_dependencies:
  - S03
```

## Lessons Learned

The prototype already specifies the complete empty-category rendering branch; assigning a second production implementation to S06 would create unnecessary overlap. Dedicated certification preserves scenario ownership without duplicating S03 architecture.

The feature-level `@wip` tag makes the existing aggregate Experts target insufficient for this contract during incremental delivery. Its exact named target must explicitly select `@experts` and report one executed scenario.

Browser configuration has deliberate plugin exclusions. Clearing `addopts` requires retaining those exclusions explicitly; browser checks remain separate from ordinary HTTP/caplog runs.

No unresolved infrastructure or scope proposal, new architectural decision, or time estimate. Actual passes and final footprints remain unverified until authorized implementation.

## Structural application evidence

`docs/experts-replay/pin-evidence/S06.json` records positive scaffold selection and deliberate NotImplementedError. Existing callable ASTs were preserved. Browser collection is not interaction certification.

## Actual structural footprint

`docs/experts-replay/pin-evidence/S06.json`, `docs/features/steps/experts_empty_steps.py`, `docs/plans/iterations/experts/S06-experts-list-06.md`, `tests/e2e/test_experts_empty_category.py`, `tests/integration/test_experts_empty_category.py`, `tests/support/experts_html.py`

Skeleton: `04402ab629c90267f3e0ac0a9646199c89d578c2`; shared reconciliation: `39d598328d438d09723b6eb14574fbf92fab71c9`. Semantic and physical-file dependencies are recorded separately in the iteration manifest. Context-map line ranges record the workers’ inspection baseline; headers and the final scaffold remain authoritative.
