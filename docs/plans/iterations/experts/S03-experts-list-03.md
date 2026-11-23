# S03: EXPERTS-LIST-03 Rank Design by total points and enforce the five-person boundary

This plan uses [the consolidated contract](../pin-convergence-20261123-experts.md). Its shared interfaces, ownership decisions and verification-layer mapping govern this scenario. Commands in the graph below are the canonical execution gates; implementation and test bodies remain unimplemented.

```yaml
scenario: S03
acceptance_id: EXPERTS-LIST-03
feature_file_path: docs/features/act-18-experts/experts-list.feature
feature_line: 25
primary_execution_layer: at
expanded_case_count: 1
dependencies: []
system_dependencies: []
status: converged_plan_unapplied
source_report_sha256:
- 10fff3e8ff8aedf25adf29450bec209cc841ceabfd89c095d08f7358be3d97b3
- 98551b6d4009438fee244e3d25b50c4a7e5303954efac19e1a6c87dc855ef5d0
- bd18655f55e502d28939f8c54d94c548f84551d46157acdfbbb1b709db2cc409
```

## A — Context Map


| Actual reference | Why it matters |
|---|---|
| `methodology/models/playbook.py:24–60` | Existing category slugs, released status and author relationship support category release counts; no category model is needed. |
| `mockups/experts_views.py:107–133` | Prototype correctly sorts total descending, username ascending and slices five, but reads declared JSON totals/categories rather than querying domain state. |
| `templates/mockups/experts/list.html:6–19` | Approved category links, leaderboard, ordered cards and stable selectors to graduate. |
| `tests/fixtures/CATALOG.md:13–24` | Pytest and Behave have separate lifecycles; historical imports require deterministic identities and isolated real DB state. |
| `tests/support/log_story.py:9–36` | Implemented caplog helper asserts all fragments for a beat occur in a matching record. Reuse it. |

Read and verified reusable bodies:

- `Playbook` has concrete ORM fields and working visibility checks. Existing `tests/unit/test_playbook_model.py`, `tests/unit/test_playbook_service.py` and `tests/integration/test_guest_playbook_browse.py` cover public/released behavior.
- `tests/conftest.py` loads existing real seed data and forces locmem email. Preserve these fixtures; add a separately named Cedar fixture.
- `docs/features/steps/http_steps.py` makes real Django-client requests; `docs/features/environment.py` exposes the transactional client.
- Existing `tests/e2e/conftest.py` provides a real live server/browser lifecycle; `tests/e2e/e2e_helpers.py` provides browser login.
- `mockups/experts_views.py` is a working design reference, not production query infrastructure.
- No Experts query service, Karma model, Cedar ORM adapter or Experts domain step bindings currently exists.

## B — Do-Not-Do List


- Do not rank using `karma_by_category`, JSON `total_karma`, or cached profile totals. Sum persisted awards across all categories.
- Do not filter award rows to Design before computing a user’s total or primary category.
- Do not take five users before filtering by positive total and primary category.
- Do not use released-playbook count as the main score, or infer availability/suitability.
- Do not require a public released playbook for leaderboard eligibility. Positive contributors such as Sam remain eligible.
- Do not expose private titles, email, tokens or historical event identities in leaderboard projections.
- Do not award points from this GET or run historical fixture records through release/PIP/consumption hooks.
- Do not add a queue, provider call, ToolExecutor, agent loop, vector database or MCP tool.
- Do not replace the prototype or bypass the shared Django shell.
- Do not change tracked `mimir.db` merely to support tests. The adapter targets runner-owned test databases.
- Do not treat a skipped/empty checkpoint or prototype screenshot as acceptance evidence.

## C — Applicable SAO Sections


- **Design Principles → FOB-Centric Architecture**
- **Web UI Architecture → UI Design Conventions**
- **Web UI Architecture → Django Implementation Details**
- **Services Layer**
- **Experts & Karma delivery architecture — planned delta → Awards, projections and transaction boundaries**
- **Experts & Karma delivery architecture — planned delta → Web delivery and notification reuse**
- **Experts & Karma delivery architecture — planned delta → Test strategy for this delta**
- **17. AI Agent Architecture — Experts contribution summary**, only its boundary: numeric projections operate without an LLM.

The exact source is `experts-list.feature:25–39`; journey Act18 explicitly explains why Maria’s overall 8,200 places her above Priya’s 7,600 despite Maria’s Design subtotal of 7,200.

### Shared interfaces and ownership

Proposed production API:

```text
ExpertsService.list_leaders(category, *, correlation_id) -> tuple[ExpertProjection, ...]
ExpertsService.project_user(user_id) -> ExpertProjection
resolve_primary_category(category_points, released_counts) -> str | None
```

`ExpertProjection` is immutable and contains only user identifier, username, display name, total, primary category, category totals and four source totals. It contains no email, token or private evidence.

Contract with S30’s ledger:

```text
recipient_id: integer
source_kind: release | major | minor | consumption | learning
points: positive integer
category: product | development | research | design | other
event_id: stable string
```

If S30 uses different field names, reconcile once before applying skeletons. This plan does not authorize a second ledger.

Algorithm:

1. Group persisted awards by recipient/category/source, preserving all categories.
2. Derive each user’s overall, category and source totals.
3. Query released-playbook counts by author/category for primary-category tie resolution.
4. Choose highest category points; break ties by released-playbook count, then category label alphabetically.
5. Keep users with positive total and primary category equal to the selected category.
6. Sort `(-total, username)`, limit exactly five, then number visible rows 1–5.

Use bulk queries rather than one query per contributor. Release counts are a tie input, never an eligibility condition.

## D — Tests to Create


| Test | Concrete proof |
|---|---|
| `test_load_cedar_baseline_with_historical_rows_reconciles_oracle` | All real imported ledger sums match JSON totals/category/source oracle; Maria is 8,200 / Design 7,200; zero account has no awards. |
| `test_load_cedar_baseline_with_second_load_preserves_awards` | Stable historical IDs prevent duplicate awards; no release/decision hooks are invoked. |
| `test_load_cedar_baseline_with_invalid_ledger_rejects_before_writes` | Negative amounts, count×unit mismatch, unsupported categories/source kinds or inconsistent oracle fail atomically. |
| `test_list_leaders_with_design_uses_total_and_limits_five` | Exact usernames/totals/subtotals; Maria precedes Priya; Theo, Mike and Nora absent. |
| `test_list_leaders_with_development_excludes_secondary_design_contributor` | Mike 12,450 precedes Jordan 6,100; Maria absent despite Development awards. |
| `test_list_leaders_with_changed_award_reads_live_projection` | Insert a real additional historical test award, requery, and observe changed score/order without updating JSON or cached fields. |
| `test_list_leaders_with_nonprimary_positive_category_excludes_user` | A large secondary-category score does not independently put a user in that leaderboard. |
| `test_list_leaders_with_invalid_category_rejects_service_input` | Service fails clearly; view fallback remains S09’s responsibility. |
| `test_list_leaders_with_positive_user_without_release_remains_eligible` | Research includes Sam; release counts do not become an eligibility restriction. |
| `test_experts_list_with_design_renders_exact_order_and_boundary` | Real Django-client HTML contains five cards in contract order with corresponding numeric totals. |
| `test_experts_list_with_development_renders_expected_order` | Follow the actual Development href and verify rendered order/exclusions. |
| `test_experts_list_with_design_log_story_happy` | caplog proves entry, aggregate, filter, limit and exit beats with request correlation. |
| `test_list_leaders_with_invalid_category_log_story_reject` | caplog proves validation rejection without querying private content or leaking sensitive fields. |
| `test_experts_list_with_design_browser_preserves_rank_order` | Real Playwright page shows same card order and category switch. Maps to CEDAR-JOURNEY-01 and EXPERTS-LIST-10. |

AT bindings execute the exact S03 Gherkin with real objects/client; do not reimplement ranking inside step definitions. The table must be checked against both real response context/projection values and rendered card order.

Behavior checkpoint:

```bash
pytest tests/unit/test_experts_projection.py tests/integration/test_experts_data.py tests/integration/test_experts_list_s03.py -x
```

Log checkpoint:

```bash
pytest tests/integration/test_experts_list_s03.py -k log_story -x
```

Exact living-spec gate, through the proposed narrow Make target:

```bash
make test-at-experts-s03
```

Browser gate:

```bash
pytest -o addopts= tests/e2e/test_experts_list_s03.py -x
```

The terminal checkpoint includes browser verification:

```bash
pytest -o addopts= tests/unit/test_experts_projection.py tests/integration/test_experts_data.py tests/integration/test_experts_list_s03.py tests/e2e/test_experts_list_s03.py -x
```

## E — Log Story Script


All rows are INFO. Use request `X-Request-ID`, or a generated correlation ID. Do not log emails, private titles, award bodies or credentials.

| Where | Beat | Trigger | Must include |
|---|---|---|---|
| `experts_list` | entry | HTTP list request | `entry`, `category=design`, `correlation_id=` |
| `ExpertsService.list_leaders` | entry | validated query requested | `entry`, `category=design`, `limit=5`, `correlation_id=` |
| `ExpertsService.list_leaders` | processing | global aggregation completed | `processing`, `scope=all_categories`, `correlation_id=` |
| `ExpertsService.list_leaders` | branch | category eligibility applied | `branch`, `primary_category=design`, `eligible_count=6`, `correlation_id=` |
| `ExpertsService.list_leaders` | exit | sorted/limited result returned | `exit`, `returned_count=5`, `order=total_desc_username_asc`, `correlation_id=` |
| `experts_list` | exit | production HTML rendered | `exit`, `status=200`, `count=5`, `correlation_id=` |
| `ExpertsService.list_leaders` | validation | unsupported service category | `validation`, `rejected=invalid_category`, `correlation_id=` |

The happy test uses the real Cedar database and client. The reject test directly calls the service with invalid input; it must not depend on S09’s HTTP fallback behavior.

## F — MCP Tools to Expose


Not applicable. S03 changes a public web query. No facade/API/tool registration or export receipt changes belong here.

## G — Agent Proofs


Not applicable. This slice never invokes summary generation or changes SAO §17’s PRF-EXPERTS/PRF-OBS paths. Numeric scores are computed directly from real ledger records. No ScriptedLLM or agent-proof command is warranted.

## H — Mockup Graduation


| Mockup | Production target | Strategy | S03 work |
|---|---|---|---|
| `templates/mockups/experts/list.html` | `templates/experts/list.html` | partial | Port ordered card loop/rank/score selectors; consume real projection context. Keep shell/category controls owned by S01/S02. |
| `mockups/experts_views.py:experts_list` | `methodology/expert_views.py` | partial | Replace JSON-declared totals/category with `ExpertsService`; do not import mockup module into production. |

Preserve `/mockups/` and its DEBUG boundary. Preserve card IDs `experts-card-<username>` and leaderboard ID `experts-leaderboard`; add noninteractive `data-total-points` and `data-category-points` only if useful for accessible AT evidence. The visible total remains formatted and readable; category subtotal need not become new visible UI.

S03 maps browser order to **CEDAR-JOURNEY-01** and **EXPERTS-LIST-10**. S04 should own full card/action visual certification; S03 supplies the exact ordering assertion reused across its seven viewport cases.

## Parent convergence

Authoritative acceptance source: `docs/features/act-18-experts/experts-list.feature:25`; 1 expanded case(s), primary layer `at`. Dependencies: none. The full scenario includes all composed journey/UAT obligations assigned in the consolidated contract. Shared Make/catalog registration belongs only to S03.

## Canonical feature execution graph

```yaml
feature_execution_graph:
  feature_ref: EXPERTS-LIST-03
  nodes:
  - id: N1-schema
    title: Establish award and stored-profile schema
    bpe: BPE-02
    depends_on: []
    footprint:
    - methodology/migrations/0027_experts_schema.py
    - methodology/models/__init__.py
    - methodology/models/expert_profile.py
    - methodology/models/karma_award.py
    - mimir.db
    - tests/integration/test_experts_schema.py
    tests:
    - test_karma_award_with_same_event_and_recipient_rejects_duplicate
    - test_karma_award_with_same_event_and_different_recipient_allows_pair
    - test_karma_award_with_second_release_recipient_rejects_duplicate_playbook
    - test_karma_award_with_nonpositive_points_rejects
    - test_expert_profile_with_same_user_rejects_duplicate
    gate:
      command: pytest tests/integration/test_experts_schema.py -x
    guidance_bundle:
      activity: BPE/BPE-02-Implement_Backend.md
      rules:
      - do-skeletons-first
      - do-test-first
      - do-not-mock-in-integration-tests
      - do-docstring-format
  - id: N2-ledger-projection
    title: Import canonical Cedar history and query exact rankings
    bpe: BPE-02
    depends_on:
    - N1-schema
    footprint:
    - Makefile
    - docs/features/CATALOG.md
    - methodology/services/expert_text.py
    - methodology/services/experts_service.py
    - tests/conftest.py
    - tests/fixtures/CATALOG.md
    - tests/integration/test_experts_acceptance_runner.py
    - tests/integration/test_experts_data.py
    - tests/integration/test_experts_list_s03.py
    - tests/support/experts_acceptance.py
    - tests/support/experts_data.py
    - tests/support/experts_html.py
    - tests/unit/test_experts_projection.py
    tests:
    - test_load_cedar_baseline_with_historical_rows_reconciles_oracle
    - test_load_cedar_baseline_with_second_load_preserves_awards
    - test_load_cedar_baseline_with_invalid_ledger_rejects_before_writes
    - test_load_cedar_baseline_with_release_rows_uses_canonical_playbook_identity
    - test_load_cedar_baseline_with_released_books_imports_version_history
    - test_load_cedar_baseline_with_second_load_preserves_release_history
    - test_list_leaders_with_design_uses_total_and_limits_five
    - test_list_leaders_with_development_excludes_secondary_design_contributor
    - test_list_leaders_with_changed_award_reads_live_projection
    - test_list_leaders_with_nonprimary_positive_category_excludes_user
    - test_list_leaders_with_invalid_category_rejects_service_input
    - test_list_leaders_with_positive_user_without_release_remains_eligible
    - test_list_leaders_with_invalid_category_log_story_reject
    log_story_rows:
    - ExpertsService.list_leaders:entry
    - ExpertsService.list_leaders:processing
    - ExpertsService.list_leaders:branch
    - ExpertsService.list_leaders:exit
    - ExpertsService.list_leaders:validation
    gate:
      command: pytest tests/unit/test_experts_projection.py tests/integration/test_experts_data.py tests/integration/test_experts_list_s03.py
        -k "not renders and not experts_list_with_design_log_story_happy" -x
      log_story_command: pytest tests/integration/test_experts_list_s03.py -k "list_leaders and log_story" -x
    guidance_bundle:
      activity: BPE/BPE-02-Implement_Backend.md
      rules:
      - do-skeletons-first
      - do-test-first
      - do-not-mock-in-integration-tests
      - do-informative-logging
      - do-assert-log-story
      - do-write-concise-methods
      - do-docstring-format
  - id: N3-direct-list-delivery
    title: Deliver the direct Experts route and graduate ranked cards
    bpe: BPE-03
    depends_on:
    - N2-ledger-projection
    footprint:
    - methodology/expert_views.py
    - mimir/urls.py
    - templates/experts/list.html
    - tests/integration/test_experts_list_s03.py
    tests:
    - test_experts_list_with_design_renders_exact_order_and_boundary
    - test_experts_list_with_development_renders_expected_order
    - test_experts_list_with_design_log_story_happy
    log_story_rows:
    - experts_list:entry
    - experts_list:exit
    - ExpertsService.list_leaders:entry
    - ExpertsService.list_leaders:processing
    - ExpertsService.list_leaders:branch
    - ExpertsService.list_leaders:exit
    mockup_source: templates/mockups/experts/list.html
    production_template: templates/experts/list.html
    graduate_strategy: partial
    gate:
      command: pytest tests/integration/test_experts_list_s03.py -x
      log_story_command: pytest tests/integration/test_experts_list_s03.py -k log_story -x
    guidance_bundle:
      activity: BPE/BPE-03-Implement_Frontend.md
      rules:
      - do-test-first
      - do-assert-log-story
      - do-semantic-versioning-on-ui-elements
  - id: N4-exact-acceptance
    title: Execute the exact ranking living specification
    bpe: BPE-04
    depends_on:
    - N3-direct-list-delivery
    footprint:
    - docs/features/steps/experts_steps.py
    gate:
      command: make test-experts-s03-at
    guidance_bundle:
      activity: BPE/BPE-04-Implement_Feature_Acceptance_Tests.md
      rules:
      - do-test-first
      - do-not-mock-in-integration-tests
  - id: N5-browser-order
    title: Certify direct Design ranking and Development switch
    bpe: BPE-05
    depends_on:
    - N4-exact-acceptance
    footprint:
    - tests/e2e/test_experts_list_s03.py
    gate:
      command: make test-experts-s03-browser
    guidance_bundle:
      activity: BPE/BPE-05-Implement_Journey_Certification_Tests.md
      rules:
      - do-semantic-versioning-on-ui-elements
  - id: N6-definition-of-done
    title: Verify schema, canonical history, ranking and browser proof
    bpe: BPE-06
    depends_on:
    - N5-browser-order
    footprint: []
    gate:
      command: make test-experts-s03
      log_story_command: pytest tests/integration/test_experts_list_s03.py -k log_story -x
    guidance_bundle:
      activity: BPE/BPE-06-Check_Definition_of_Done.md
      rules:
      - do-test-first
      - do-assert-log-story
      - do-not-mock-in-integration-tests
  scenario_dependencies: []
```

## Lessons Learned

The JSON intentionally combines independent oracle totals with aggregate historical ledger rows; copying its declared totals into production would falsely prove ranking. The adapter therefore needs independent arithmetic validation and real expanded historical rows before the query can be trusted.

The broad feature-level `@wip` tag makes the existing `make test-at-experts` insufficient for one-scenario progress. A narrow explicit S03 gate avoids both zero-selection success and prematurely enabling other unimplemented contracts.

Shared file ownership must be reconciled before skeleton application: S03 owns query/projection and ranking baseline data; S30 owns award persistence; S47 adds primary-category tie proofs without duplicating the resolver.
