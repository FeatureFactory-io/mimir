# S09: EXPERTS-LIST-09 Recover an unknown category

This plan uses [the consolidated contract](../pin-convergence-20261123-experts.md). Its shared interfaces, ownership decisions and verification-layer mapping govern this scenario. Commands in the graph below are the canonical execution gates; implementation and test bodies remain unimplemented.

```yaml
scenario: S09
acceptance_id: EXPERTS-LIST-09
feature_file_path: docs/features/act-18-experts/experts-list.feature
feature_line: 71
primary_execution_layer: at
expanded_case_count: 1
dependencies:
- S03
- S01
system_dependencies: []
status: converged_plan_unapplied
source_report_sha256:
- 9ef80850b87d55686d19ba18884b703ac5913b191a6ba889d880703eca22487d
```

## A — Context map


| Verified reference | Why it matters |
|---|---|
| `docs/features/act-18-experts/experts-list.feature:71–74` | Exact contract: unknown category selects Development without error or unrelated cards. |
| `docs/features/user_journey.md:3095–3103` | Production route, category links, `aria-current="page"` and Development fallback. |
| `mockups/experts_views.py:107–133` | Existing prototype uses an exact lowercase allowlist, defaults to Development, then filters and ranks that category. Design reference only. |
| `docs/architecture/SAO.md:3883–3928` | Ledger-derived primary-category projections, public web delivery, separate real-DB AT and browser certification. |
| `docs/ux/IA_guidelines.md:1167–1192` | Current-category semantics and stable leaderboard/card hooks. |

Additional inspected evidence: Cedar JSON contains Development contributors `mchen` with 12,450 and `jlee` with 6,100; the prototype list template already exposes category and per-person hooks. Production Experts services, views and tests do not exist in the inspected baseline.

## B — Do not do


- Do not add a second query parser or fallback service.
- Do not relax strict service validation: HTTP input recovery belongs to S03’s view/parser boundary.
- Do not treat an invalid category as “all categories.”
- Do not compute ranking from stored prose or read Cedar JSON in production.
- Do not add redirects or URL normalization that the acceptance contract does not require.
- Do not render mockup state controls, banners or fixture-only authentication controls in production.
- Do not change Karma awards, summary generation, contact policy or MCP tools.
- Do not log arbitrary raw query values, HTML/control characters, credentials or private evidence.
- Do not change existing fixture lifecycles; consume the parent’s shared function-scoped Cedar baseline.
- Do not certify with skipped, undefined or zero-selected acceptance cases.

## C — Applicable architecture


Governing SAO headings:

1. **Experts & Karma delivery architecture — planned delta**
2. **Awards, projections and transaction boundaries**
3. **Web delivery and notification reuse**
4. **Test strategy for this delta**

This is a certification slice over S03’s completed HTTP parser, query service and production list template. S01 supplies the reusable current-category assertion. No production helper, model, migration or template placeholder is required for S09.

## D — Tests to create


| Test | Required assertion |
|---|---|
| `test_experts_list_with_unknown_category_returns_development_only` | Real GET of the exact acceptance URL returns 200; Development alone is current; exact card order is `mchen`, `jlee`; displayed totals are 12,450 and 6,100. |
| `test_experts_list_with_invalid_category_variant_returns_development_only` | Parameterized missing, blank, whitespace, unknown, uppercase, bracket-name and encoded-control variants recover to the same bounded Development result. |
| `test_experts_category_fallback_log_story_happy` | Recognized Development request follows S03’s successful selection/query/exit story. |
| `test_experts_category_fallback_log_story_reject` | Unknown input records S03’s recoverable fallback branch and successful Development exit, with no ERROR or raw hostile input. |
| Exact named Behave `EXPERTS-LIST-09` | Existing Cedar background and S03 URL-opening step exercise real Django HTTP; dedicated assertions prove the exact scenario. |
| `test_experts_list_with_unknown_category_survives_browser_refresh` | Actual browser receives 200, sees Development current and only Mike/Jordan cards; refresh preserves the recovered presentation; category links remain usable. |

The response assertion checks leaderboard card identities, rather than asserting that words such as “Design” are globally absent: all five category labels must remain visible.

Matrix proposed for the parameterized backend proof:

```text
/experts/
/experts/?category=
/experts/?category=%20%09
/experts/?category=unrecognized
/experts/?category=DESIGN
/experts/?category[]=design
/experts/?category=%00design
```

These are absence, empty, unknown or noncanonical inputs under the prototype’s exact-slug contract. No new case-folding or trimming policy is introduced. Duplicate-key precedence is outside this scenario; S03 remains its single owner.

Real DB objects come from `load_cedar_baseline()` through the shared `cedar_dataset` fixture. Snapshot ledger identities/counts before and after GETs to prove fallback reads create no awards.

### Commands

Backend checkpoint:

```bash
pytest tests/integration/test_experts_category_fallback.py -x
```

Log gate:

```bash
pytest tests/integration/test_experts_category_fallback.py -k log_story -x
```

Exact acceptance gate:

```bash
make test-at-experts-list-09
```

Browser gate, separately configured:

```bash
pytest -c tests/e2e/pytest.ini -o addopts= tests/e2e/test_experts_category_fallback.py -x
```

The future Make target runs the existing runner with acceptance settings, `--simple`, `--tags='@experts'`, the exact scenario name and only `experts-list.feature`. This deliberately overrides default WIP exclusion for this named contract; it does not mark the aggregate Experts suite complete.

## E — Log story consumed from S03


S09 adds proof, not new production logging.

| Where | Beat | Trigger | Must include |
|---|---|---|---|
| S03’s production list view | entry | GET received | Operation/path and actor or guest context; no raw query payload. |
| S03’s category resolver | branch | Unknown category | Recoverable fallback reason and effective Development category. |
| S03’s list projection/view | exit | Recovered query succeeds | Effective Development category, result count 2, successful outcome. |
| S03’s selection path | validation/exit | Recognized Development | Recognized selection and count 2 without a fallback branch. |

Exact `where` strings and field spellings must be copied from the consolidated S03 contract during sequential application; the inspected baseline has no production grammar to verify. Do not introduce competing S09 log identifiers.

Use `assert_log_story` with explicit beat fragments. Test-only capture must temporarily enable the relevant production loggers and propagation because `mimir.settings.test` disables existing loggers. Restore logger configuration afterward; browser settings stay separate.

## F — MCP tools


Not applicable. This scenario changes no MCP registration, facade or client surface.

## G — Agent proofs


Not applicable. This scenario invokes no LLM, provider, agent workflow or tool executor.

## H — Mockup graduation


`templates/mockups/experts/list.html` is the verified recipe. S03 owns its production graduation to `templates/experts/list.html`.

S09’s strategy is **consume and certify**. There is no additional BPE-03 production node or production comment placeholder. Browser certification uses stable category/card hooks and the seven IA viewports; it checks the fallback state within the already graduated recipe.

## Parent convergence

Authoritative acceptance source: `docs/features/act-18-experts/experts-list.feature:71`; 1 expanded case(s), primary layer `at`. Dependencies: S03, S01. The full scenario includes all composed journey/UAT obligations assigned in the consolidated contract. Shared Make/catalog registration belongs only to S03.

## Canonical feature execution graph

```yaml
feature_execution_graph:
  feature_ref: EXPERTS-LIST-09
  nodes:
  - id: S09-N1-backend-contract
    title: Certify the shared HTTP fallback and log story
    bpe: BPE-02
    depends_on: []
    footprint:
    - tests/integration/test_experts_category_fallback.py
    - tests/support/experts_fallback_assertions.py
    tests:
    - test_experts_list_with_unknown_category_returns_development_only
    - test_experts_list_with_invalid_category_variant_returns_development_only
    - test_experts_category_fallback_log_story_happy
    - test_experts_category_fallback_log_story_reject
    log_story_rows:
    - S03-list-view:entry
    - S03-category-resolver:branch
    - S03-list-view:exit
    gate:
      command: pytest tests/integration/test_experts_category_fallback.py -x
      log_story_command: pytest tests/integration/test_experts_category_fallback.py -k log_story -x
    guidance_bundle:
      activity: BPE/BPE-02-Implement_Backend.md
      rules:
      - do-skeletons-first
      - do-test-first
      - do-not-mock-in-integration-tests
      - do-assert-log-story
    notes: Consume S03 behavior and exact consolidated log identifiers; no production edits.
  - id: S09-N2-exact-acceptance
    title: Bind the exact unknown-category acceptance contract
    bpe: BPE-04
    depends_on:
    - S09-N1-backend-contract
    footprint:
    - docs/features/steps/experts_fallback_steps.py
    tests:
    - EXPERTS-LIST-09
    gate:
      command: make test-experts-s09-at
    guidance_bundle:
      activity: BPE/BPE-04-Implement_Feature_Acceptance_Tests.md
      rules:
      - do-test-first
      - do-not-mock-in-integration-tests
    notes: Reuse S03 baseline/open-URL and S01 current-category bindings.
  - id: S09-N3-browser-certification
    title: Verify recovered presentation and refresh in the real browser
    bpe: BPE-05
    depends_on:
    - S09-N2-exact-acceptance
    footprint:
    - tests/e2e/test_experts_category_fallback.py
    tests:
    - test_experts_list_with_unknown_category_survives_browser_refresh
    gate:
      command: make test-experts-s09-browser
    guidance_bundle:
      activity: BPE/BPE-05-Implement_Journey_Certification_Tests.md
      rules:
      - do-test-first
      - do-semantic-versioning-on-ui-elements
    notes: Use existing page/live_server_url and shared function-scoped Cedar baseline.
  - id: S09-N4-definition-of-done
    title: Complete fallback certification
    bpe: BPE-06
    depends_on:
    - S09-N3-browser-certification
    footprint: []
    tests:
    - test_experts_list_with_unknown_category_returns_development_only
    - test_experts_list_with_invalid_category_variant_returns_development_only
    - test_experts_category_fallback_log_story_happy
    - test_experts_category_fallback_log_story_reject
    - EXPERTS-LIST-09
    gate:
      command: make test-experts-s09
      log_story_command: pytest tests/integration/test_experts_category_fallback.py -k log_story -x
      acceptance_command: make test-at-experts-list-09
    guidance_bundle:
      activity: BPE/BPE-06-Check_Definition_of_Done.md
      rules:
      - do-test-first
      - do-assert-log-story
      - do-github-issues
    notes: Browser predecessor must actually pass; zero/skipped AT is not completion.
  scenario_dependencies:
  - S03
  - S01
```

## Lessons Learned

Proposed footprint is the six files shown in graph nodes. Parent-owned plan/manifest/handoff files remain separate. Dependencies are `[S03, S01]`; there are no infrastructure or scope proposals.

PIN-04 supplies the concrete issue and docs handoff; PIN-05 obtains human GO. Future slices are backend certification plus log proofs, exact AT, browser certification, then final DoD. Each implementation slice requires its Angular commit with `Refs #N` and approved issue update; the final slice uses `Closes #N`.

Lessons Learned:

- An invalid HTTP category must recover before reaching the strictly validating service.
- “No unrelated data” means exact leaderboard membership, while preserving all category navigation labels.
- Prototype behavior supports planning but does not prove production recovery.
- Disabled test loggers and the global E2E ignore setting require explicit, separate certification setup.
- No files were written, tests run, issues posted or commits created by this worker.
