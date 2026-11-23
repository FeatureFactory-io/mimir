# S11: EXPERTS-PROFILE-02 Expand and collapse the long stored summary

This plan uses [the consolidated contract](../pin-convergence-20261123-experts.md). Its shared interfaces, ownership decisions and verification-layer mapping govern this scenario. Commands in the graph below are the canonical execution gates; implementation and test bodies remain unimplemented.

```yaml
scenario: S11
acceptance_id: EXPERTS-PROFILE-02
feature_file_path: tests/e2e/experts-interactions.feature
feature_line: 9
primary_execution_layer: e2e
expanded_case_count: 1
dependencies:
- S10
system_dependencies: []
status: converged_plan_unapplied
source_report_sha256:
- 411ebe97a342913a58f1c83bffac756fcd855dfce8f753f3d78a24695322733b
```

## A — Context map


| Verified reference | Relevance |
|---|---|
| `docs/features/act-18-experts/experts-profile.feature:15–24` | Exact long-paragraph initial, expanded and restored states. |
| `templates/mockups/experts/own_profile.html:6–12` | Existing native button, summary region, stable selectors and synchronous state changes. |
| `templates/accounts/profile.html:240–276` | Existing token handlers inside `extra_js`; contribution handling must coexist with them. |
| `test-data/experts/cedar-rfp-01.json:113–119` | Maria’s complete seeded nine-sentence paragraph; assert equality, including final sentence. |
| `docs/features/user_journey.md:3183–3191` | Existing account functions retained; paragraphs exceeding four lines collapse with accurate ARIA state. |

Also inspected replay AGENTS/CLAUDE, dispatch/GitHub/ownership guidance, SAO Experts delta and §17, IA §11, actual profile view/tests, prototype CSS, E2E fixtures/config/helpers, AT environment/steps/config, Makefile and existing execution graph example.

## B — Do not do


- Do not duplicate S10’s view/context, template, handler or scoped CSS.
- Do not generate summaries or depend on S23. Consume S03’s stored Cedar profile.
- Do not infer visual clipping from DOM text or the existence of a CSS class alone.
- Do not truncate the persisted paragraph, insert ellipses into stored text or replace it with fixture prose in production.
- Do not make expansion submit a form, change the URL or regenerate a token.
- Do not alter profile token/edit/PIP/team/playbook functions.
- Do not expose own-profile controls publicly.
- Do not introduce a browser or fake state machine into Django-client AT.
- Do not remove feature-level WIP or claim undefined/skipped/zero-selected scenarios passed.

## C — Applicable architecture


Governing SAO headings:

- **Web delivery and notification reuse** — existing route, Bootstrap shell, standard expansion and hooks.
- **Test strategy for this delta** — real Django-client contracts; separate actual browser certification.
- **E2E Testing with Playwright** — reuse existing `page`, `live_server_url` and login helper.

IA §11 and Act 18 govern four-line presentation and ARIA. SAO §17 is not in scope: displaying stored text introduces no agent capability.

## D — Tests and assertions


| Test | Assertions |
|---|---|
| `test_profile_summary_contract_with_seeded_maria_returns_complete_stored_paragraph` | Real authenticated GET returns 200; parsed `profile-contribution-summary` text equals Maria’s complete stored paragraph; final ninth sentence survives; GET leaves stored text unchanged. |
| `test_profile_summary_markup_with_long_paragraph_links_button_to_region` | Exactly one native `type=button` `profile-summary-toggle`; accessible Show more label; `aria-expanded=false`; nonempty `aria-controls` resolves to the unique summary region ID; token and Edit hooks remain present. |
| `test_profile_summary_with_long_paragraph_expands_and_collapses` | Exact EXPERTS-PROFILE-02 in Chromium at all seven IA viewports: actual four-line clipped box, full text retained in DOM, click expands to unclipped full paragraph, Show less/true, second click restores original height and Show more/false. |
| `test_profile_summary_with_keyboard_activation_preserves_focus_and_state` | Native button receives keyboard focus; Enter expands and Space collapses; focus remains on button; controlled-region relationship survives; URL and account controls remain unchanged. |
| `test_profile_summary_with_short_paragraph_displays_without_unnecessary_toggle` | Seeded short-profile prose fits within four lines, is completely displayed and has no visible/focusable expansion control. No clipping or misleading Show more state. |

Use shared `tests/support/experts_html.py` (`find_by_test_id`, `element_text`, `_walk_elements`, Django `parse_html`) for response assertions. No local HTML parser.

Browser geometry must measure line height and actual rendered height, not merely inspect classes. Collapsed long content must have height approximately four line heights and demonstrable overflow. Expanded content must have no clipping and greater height. Allow a small named pixel tolerance for rendering rounding.

Short-profile proof can use seeded `jlee`’s short paragraph and real account login, avoiding fixture mutation. If it wraps beyond four lines at a particular width, use an isolated test-only short stored paragraph through S03’s finalized model field; reconcile its name before application.

### Acceptance-layer reconciliation

The exact scenario includes real activation and visible geometry. Existing Django-client Behave cannot execute those steps honestly. `docs/ux/experts-test-assets.md` explicitly places browser-backed phrases in E2E.

**Proposal:** map EXPERTS-PROFILE-02’s full exact contract to the named browser pytest test, while Django-client AT proves its server-rendered contract. Record this mapping in `docs/features/CATALOG.md`; do not introduce simulated Behave expansion steps. The parent must reconcile this layer mapping before claiming all 49 living contracts executable. Running the exact Behave scenario with undefined steps is not completion.

Commands:

```text
pytest tests/integration/test_experts_profile_summary.py -x
make test-at-experts-profile-02
E2E_LIVE_SERVER_SCOPE=function pytest -c tests/e2e/pytest.ini -o addopts= -p no:playwright -p no:asyncio -p no:anyio tests/e2e/test_experts_profile_summary.py -x
make test-experts-profile-02
```

Proposed `test-at-experts-profile-02` runs the two explicitly named Django-client contract tests. Its catalog entry must call this **server contract coverage**, with the full acceptance scenario’s browser mapping clearly identified.

## E — Log story


Empty, justified. S11 adds certification of S10-owned presentation only; no production request path, domain transition, provider invocation or persistence is added. Browser expansion is local visual state. Do not introduce console output containing summary text or account data. S10’s applicable production logging proofs remain its prerequisite gates.

No S11 `log_tests` or `log_story_command`.

## F — MCP


Not applicable. No tool, facade, REST registration or MCP client change.

## G — Agent proofs


Not applicable. No agent/provider/model work and no PRF selection.

## H — Mockup graduation


S10 owns graduation of the contribution block and existing prototype behavior into `templates/accounts/profile.html`, with scoped `static/css/mimir-app.css` and a single handler appended to the existing `extra_js`.

S11’s strategy is **consume and certify**. No production comment placeholder or new BPE-03 edit is warranted.

Required shared hooks:

- Summary: `profile-contribution-summary`, unique stable `id`.
- Native toggle: `profile-summary-toggle`, visible Show more/Show less.
- `aria-controls` references that summary ID.
- `aria-expanded` reflects actual clipping state.
- Short content: no visible/focusable unnecessary toggle.

S10 should use overflow-aware initialization and resize handling if needed to maintain the same contract across IA widths. This belongs in its single handler.

## Parent convergence

Authoritative acceptance source: `tests/e2e/experts-interactions.feature:9`; 1 expanded case(s), primary layer `e2e`. Dependencies: S10. The full scenario includes all composed journey/UAT obligations assigned in the consolidated contract. Shared Make/catalog registration belongs only to S03.
This entire acceptance contract is browser-certified. Server checks are complementary initial-HTML/receipt contracts; no clipboard/hover/expansion Behave substitution is allowed.

## Canonical feature execution graph

```yaml
feature_execution_graph:
  feature_ref: EXPERTS-PROFILE-02
  scenario: S11
  scenario_dependencies:
  - S10
  nodes:
  - id: S11-N1-backend-contract
    title: Certify the stored paragraph reaches the existing own-profile route
    bpe: BPE-02
    depends_on: []
    footprint:
    - tests/integration/test_experts_profile_summary.py
    tests:
    - test_profile_summary_contract_with_seeded_maria_returns_complete_stored_paragraph
    gate:
      command: pytest tests/integration/test_experts_profile_summary.py::test_profile_summary_contract_with_seeded_maria_returns_complete_stored_paragraph
        -x
    guidance_bundle:
      activity: BPE/BPE-02-Implement_Backend.md
      rules:
      - do-skeletons-first
      - do-test-first
      - do-not-mock-in-integration-tests
    notes: Real ORM and authenticated HTTP; no production changes or generation.
  - id: S11-N2-server-acceptance-contract
    title: Prove initial server semantics and record browser ownership
    bpe: BPE-04
    depends_on:
    - S11-N1-backend-contract
    footprint:
    - tests/integration/test_experts_profile_summary.py
    tests:
    - test_profile_summary_markup_with_long_paragraph_links_button_to_region
    gate:
      command: make test-experts-s11-server
    guidance_bundle:
      activity: BPE/BPE-04-Implement_Feature_Acceptance_Tests.md
      rules:
      - do-test-first
      - do-not-mock-in-integration-tests
    notes: Explicitly server-contract coverage only. Full exact click/geometry scenario maps to N3; no simulated
      Behave state or browser inside Django-client AT. Parent must reconcile living-spec layer mapping before completion.
  - id: S11-N3-browser
    title: Certify full exact scenario keyboard and short-content behavior
    bpe: BPE-05
    depends_on:
    - S11-N2-server-acceptance-contract
    footprint:
    - tests/e2e/test_experts_profile_summary.py
    tests:
    - test_profile_summary_with_long_paragraph_expands_and_collapses
    - test_profile_summary_with_keyboard_activation_preserves_focus_and_state
    - test_profile_summary_with_short_paragraph_displays_without_unnecessary_toggle
    gate:
      command: make test-experts-s11-browser
    guidance_bundle:
      activity: BPE/BPE-05-Implement_Journey_Certification_Tests.md
      rules:
      - do-test-first
      - do-semantic-versioning-on-ui-elements
    notes: Existing page/live_server_url/login; separate browser settings. Seven real viewport proofs, keyboard
      focus, complete text and geometry.
  - id: S11-N4-definition-of-done
    title: Require complete production-route certification
    bpe: BPE-06
    depends_on:
    - S11-N3-browser
    footprint: []
    tests:
    - tests/integration/test_experts_profile_summary.py
    - tests/e2e/test_experts_profile_summary.py
    gate:
      command: make test-experts-s11
    guidance_bundle:
      activity: BPE/BPE-06-Check_Definition_of_Done.md
      rules:
      - do-test-first
      - do-github-issues
    notes: Rollup runs named server-contract gate, existing profile regression suite, and separate browser command.
      Require positive counts and no skips. Confirm one handler, S10-owned CSS, unchanged paragraph and retained
      account controls; resolve living-spec mapping before claiming EXPERTS-PROFILE-02 done.
```

## Lessons Learned

PIN-04/05 owns issue publication, docs handoff and actual human GO. Future slices: real server contract; semantic acceptance/catalog; browser certification; DoD rollup. Each implementation slice uses Angular `Refs #N` plus required issue update; final verified slice uses `Closes #N`.

Lessons:

1. Complete DOM text does not prove full visible text: the browser must distinguish clamped and expanded geometry.
2. The prototype always renders a toggle; short-content handling must be resolved in S10’s single production handler.
3. Existing token JavaScript already occupies `extra_js`; replacing that block would regress account behavior.
4. Exact activation phrases expose a real AT/E2E boundary. Catalog the boundary rather than manufacture successful Django-client transitions.

No writes, tests, commits, issues or production actions were performed.
