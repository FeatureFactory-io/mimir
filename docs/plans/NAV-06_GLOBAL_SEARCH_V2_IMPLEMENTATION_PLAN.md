# NAV-06 Global Search V2 — Implementation Plan (BPE-01)

**Feature**: FOB-GLOBAL-SEARCH (NAV-06) — full playbook entity search with accordion UI and term highlighting  
**Supersedes**: [`NAV_06_GLOBAL_SEARCH_IMPLEMENTATION_PLAN.md`](NAV_06_GLOBAL_SEARCH_IMPLEMENTATION_PLAN.md) (v1 MVP: 3 entity types, 3-column layout, status/source filters)  
**Spec**: [`docs/features/act-0-auth/global-search.feature`](../features/act-0-auth/global-search.feature) (25 scenarios, all `@wip`)  
**Journey**: [`docs/features/user_journey.md`](../features/user_journey.md) — FOB Global Search + FOB Search Results  
**Mockup** (DEBUG): `/mockups/search/?q=React` — production templates should mirror this UX  
**Branch**: `feature/nav-06-global-search-v2`  
**Issue**: TBD (GitLab)

---

## 0. Executive Summary

V1 shipped navbar search + a minimal results page for **Playbooks, Workflows, Activities** scoped to **owned playbooks only**. V2 aligns production with the approved BDD spec and mockup:

| Area | V1 (today) | V2 (target) |
|------|------------|-------------|
| Entity types | 3 | 8 (+ phases, artifacts, skills, agents, rules) |
| Access scope | `author=user` only | `PlaybookService.get_accessible_playbook_ids` |
| Filters | q, type, **status**, **source** | **q, type only** |
| Results layout | 3-column static lists | Accordion (All types) / flat card (single type) |
| Highlighting | None | `<mark class="mm-search-highlight">` case-insensitive |
| Empty / no-query | Single empty alert | Distinct no-query prompt vs no-match empty state |
| Suggestions | 3 flat sections | Grouped sections, highlight, `global-search-see-all-results` |
| Filter UX | Apply button | Debounced Search-for input + Type `change` auto-submit (IA §5.2) |

**MCP / Agent**: Not in scope — read-only Web UI find; no new MCP tools.

---

## Section A — Context Map

| File | Lines | One-line note |
|------|-------|---------------|
| `methodology/services/global_search_service.py` | 1–112 | V1 service — extend entity searches + accessible playbook scope |
| `methodology/services/playbook_service.py` | 312–364 | `get_accessible_playbook_ids(user)` — canonical read scope for search |
| `methodology/views.py` | 217–347 | `global_search` / `global_search_suggestions` — thin controllers to refactor |
| `templates/search/results.html` | 1–134 | V1 3-column page — replace with mockup-aligned accordion layout |
| `templates/mockups/search/results.html` | 1–214 | **Reference UX** — port structure/partials to production templates |
| `mockups/views.py` | 874–947 | `_highlight_search_term`, `_mock_search_grouped` — move highlight + grouping logic to production utils/service |
| `static/css/mimir-app.css` | 458–590 | `.mm-search-*` + `mark.mm-search-highlight` already defined |
| `templates/base.html` | 186–204 | Navbar HTMX wiring — keep; suggestions partial will change shape |
| `tests/integration/test_global_search.py` | 1–158 | V1 integration tests — expand for V2 scenarios |
| `tests/unit/test_global_search_service.py` | 1–85 | V1 unit tests — expand per entity + access scope |

---

## Section B — Do-Not-Do List

Derived from SAO + user journey + feature spec:

- **Do not** add Status or Source filters to the search results page (removed from NAV-06 spec).
- **Do not** expose global search to anonymous users (navbar form stays auth-only).
- **Do not** add MCP tools for search in this feature (Web UI only).
- **Do not** put search/business logic in templates or MCP wrappers — keep in `GlobalSearchService` + small utils.
- **Do not** scope search to owned playbooks only — use accessible playbook IDs (public non-draft, team, group-shared).
- **Do not** include draft playbooks owned by other authors in results (FOB-GLOBAL-SEARCH-17).
- **Do not** store highlight HTML in the database — highlight at render time only.
- **Do not** use `data-copy` attributes for large text — N/A here; use server-side `mark` wrapping in service/view layer.
- **Do not** defer logging to a final slice — log-story tests ship with each green slice (workspace rule).

---

## Section C — SAO.md Sections That Apply

| SAO section | Relevance |
|-------------|-----------|
| **§3 Shared Services Layer** | Search logic lives in `methodology/services/`; views are thin. |
| **§5 Design Principles — REST + Web UI** | Django templates + HTMX; no SPA. |
| **§765 Web UI Architecture** | Bootstrap 5.3, `data-testid`, tooltips, `hg-page-header` (IA §3.4–3.5). |
| **§1795 Global Search Service pattern** | Extend registered entity types; keep `search()` entry point stable for callers. |
| **§1465 Data Model** | Query existing models only — no migrations. |
| **§2 Hybrid MCP Access** | N/A — search is not exposed via MCP in V2. |

---

## Section D — Tests to Create

| Test | File | Asserts |
|------|------|---------|
| `test_highlight_search_term_wraps_case_insensitive_match` | `tests/unit/test_search_highlight.py` | `React` wrapped in `<mark class="mm-search-highlight">` when query is `react` |
| `test_highlight_escapes_html_before_wrapping` | same | User content with `<script>` escaped, not executed |
| `test_search_includes_public_playbook_not_owned` | `tests/unit/test_global_search_service.py` | Other author's public released playbook appears |
| `test_search_excludes_other_authors_draft` | same | FOB-GLOBAL-SEARCH-17 |
| `test_search_all_entity_types_returned` | same | Keys for all 8 entity types when fixtures match |
| `test_type_filter_limits_to_one_entity_key` | same | `type=skills` → only skills list populated |
| `test_build_result_row_includes_context_and_snippet` | same | Activity context `Playbook › Workflow` |
| `test_global_search_log_story_happy` | `tests/integration/test_global_search.py` | caplog: service entry/exit beats with query + counts |
| `test_global_search_log_story_reject` | same | caplog: empty query path (no error) |
| `test_results_page_filter_bar_q_and_type_only` | same | FOB-GLOBAL-SEARCH-03; no `filter-status` / `filter-source` |
| `test_results_page_accordion_first_section_expanded` | same | FOB-GLOBAL-SEARCH-19 |
| `test_results_page_single_type_no_accordion` | same | FOB-GLOBAL-SEARCH-06 / 23 |
| `test_results_page_highlight_in_html` | same | FOB-GLOBAL-SEARCH-09, 09b |
| `test_results_page_no_query_prompt` | same | FOB-GLOBAL-SEARCH-13 |
| `test_results_page_empty_state` | same | FOB-GLOBAL-SEARCH-12 |
| `test_suggestions_grouped_with_see_all` | same | FOB-GLOBAL-SEARCH-14, 02 |
| `test_suggestions_highlight_query` | same | FOB-GLOBAL-SEARCH-25 |
| `test_suggestions_empty_query_empty_fragment` | same | FOB-GLOBAL-SEARCH-16 |
| `test_navbar_search_auth_only` | same | FOB-GLOBAL-SEARCH-18 (existing, keep) |
| `test_result_link_navigates_to_detail` | same | FOB-GLOBAL-SEARCH-11 |
| `test_complete_global_search_journey` | `tests/e2e/test_journey_global_search.py` | Update for accordion + `global-search-summary` |
| `test_e2e_accordion_expand_section` | same (new) | FOB-GLOBAL-SEARCH-20 — optional Playwright slice |

**Accordion interaction tests (20–22)**: Bootstrap collapse is client-side; cover **aria-expanded / `.show`** in integration tests (parsed HTML). Full click-toggle behavior in one Playwright scenario.

---

## Section E — Log Story Script

| Where | Beat | Trigger | Must include |
|-------|------|---------|--------------|
| `GlobalSearchService.search` | entry | non-empty query | `GlobalSearchService.search started`, `user=`, `query=` |
| `GlobalSearchService.search` | processing | per-type counts | `finished`, playbook/workflow/… counts (aggregate line OK) |
| `GlobalSearchService.search` | branch | empty query | `empty query`, no exception |
| `global_search` | entry | GET `/search/` | `Global search requested`, `user=`, `query=` |
| `global_search` | exit | render results | `Global search completed`, result counts |
| `global_search_suggestions` | branch | empty q | `empty query`, `empty fragment` |
| `global_search_suggestions` | exit | matches | `suggestions`, limited counts |

**Log-story tests** (same commit as behavior):

- `test_global_search_log_story_happy` — non-empty query through view + service
- `test_global_search_log_story_reject` — empty query on service (empty lists, INFO branch)

Use `tests/support/log_story.py` → `assert_log_story(...)`.

---

## Section F — MCP Tools to Expose

**Not applicable.** Global search is authenticated Web UI + HTMX only. No REST endpoint or MCP tool required for NAV-06 V2. (Future: optional `search_playbook_content` MCP tool is out of scope.)

---

## 1. Resolved Assumptions (no blocker questions)

| Topic | Decision | Source |
|-------|----------|--------|
| Accordion single-open panel | Yes — `data-bs-parent="#global-search-sections"` | Mockup + FOB-GLOBAL-SEARCH-21 |
| First expanded section | First entity type **with matches** in canonical order | FOB-GLOBAL-SEARCH-19 |
| Searchable fields | name/title/description/guidance/content/slug per entity (see §2.1) | SAO §1795 + journey |
| Snippet length | ~20 words, markdown stripped for display | Journey |
| Type filter values | `playbooks`, `workflows`, `phases`, `activities`, `artifacts`, `skills`, `agents`, `rules` | FOB-GLOBAL-SEARCH-05 |
| Teams in search | Out of scope | Journey NAV-06 |
| Debounced filter submit | 300ms on Search-for input; immediate on Type change | Mockup JS + IA §5.2 |

---

## 2. Backend Design

### 2.1 Entity registration (search fields + context)

| Entity | QuerySet scope | `icontains` fields | Context line |
|--------|----------------|-------------------|--------------|
| Playbook | accessible IDs | `name`, `description` | `{author} · v{version} · {category\|status}` |
| Workflow | `playbook_id__in=…` | `name`, `description` | `{playbook.name} · {n} activities` |
| Phase | `playbook_id__in=…` | `name`, `description` | `{playbook.name}` |
| Activity | `workflow__playbook_id__in=…` | `name`, `guidance` | `{playbook} › {workflow}` |
| Artifact | `playbook_id__in=…` | `name`, `description` | `{playbook.name}` |
| Skill | `playbook_id__in=…` | `title`, `content`, `capability_domain`, `technology_stack` | `{domain} · {stack}` when set |
| Agent | `playbook_id__in=…` | `name`, `description` | `{playbook.name}` |
| Rule | `playbook_id__in=…` | `title`, `slug`, `content` | `{playbook.name} · always_apply` |

### 2.2 New / moved modules

```
methodology/utils/search_highlight.py     # highlight_search_term(text, query) -> SafeString
methodology/services/global_search_service.py
  - SEARCH_ENTITY_ORDER constant (canonical section order)
  - _accessible_playbook_ids(user) -> delegates PlaybookService
  - _search_{entity}() x8
  - search() -> dict[str, list[Model]]  (keep backward-compatible keys)
  - build_sections(query, raw_results, type_filter) -> list[SearchSection]
  - serialize_result(entity, instance, query) -> SearchResult dict for templates
```

`SearchResult` template dict keys: `testid`, `title`, `title_html`, `context_html`, `snippet_html`, `type_label`, `icon`, `url`.

Icons align with navbar (`fa-book-sparkles`, `fa-diagram-project`, …).

### 2.3 View changes (`methodology/views.py`)

**`global_search`**:

- Read only `q` and `type` from GET.
- Call `service.search()` then `service.build_sections()` (or combined method).
- Context: `query`, `sections`, `total_count`, `type_filter`, `type_choices`, `show_no_query_prompt`, `show_empty_state`.
- Remove `status_filter`, `source_filter`.

**`global_search_suggestions`**:

- Build grouped sections (limit 5 items per type).
- Pass `sections`, `query`, `total_count` to partial (mirror mockup).

---

## 3. Frontend Design

Port from `templates/mockups/search/` → `templates/search/`:

| Production file | Action |
|-----------------|--------|
| `search/results.html` | Replace with mockup layout (breadcrumb, `hg-page-header`, filter card, accordion/flat) |
| `search/partials/result_row.html` | **Add** — shared row (icon, title_html, context, snippet, badge) |
| `search/partials/suggestions.html` | Replace with grouped mockup partial + `data-testid="global-search-see-all-results"` |
| `static/css/mimir-app.css` | Already has `.mm-search-*` — no change unless gap found |

**data-testid contract** (from feature file): preserve all IDs listed in FOB-GLOBAL-SEARCH-03 through 25.

**Filter form**: `data-testid="global-search-filters-form"`, `global-search-query-input`, `global-search-type-filter`, `global-search-submit-button` (keep explicit Search button per spec scenario 03 — debounce supplements, does not remove button).

---

## 4. Implementation Steps (vertical slices)

### Slice 1 — Highlight util + service skeleton (RED → GREEN)

1. Add `methodology/utils/search_highlight.py` with tests in `tests/unit/test_search_highlight.py`.
2. Add `SEARCH_ENTITY_ORDER` + `_accessible_playbook_ids()` to service.
3. Commit: `feat(search): add highlight util and accessible playbook scope`

### Slice 2 — All entity type searches (RED → GREEN)

1. Implement `_search_phases`, `_search_artifacts`, `_search_skills`, `_search_agents`, `_search_rules`.
2. Refactor existing `_search_playbooks/workflows/activities` to use accessible IDs (not `author=user` only).
3. Remove status/source filter branches from service.
4. Unit tests: all types, access scope, type filter, empty query.
5. Commit: `feat(search): extend GlobalSearchService to eight entity types`

### Slice 3 — Result serialization + sections (RED → GREEN)

1. Add `serialize_result()` + `build_sections()` with highlight HTML fields.
2. Unit tests for context lines, snippet truncation, section ordering, zero-hit omission.
3. Log-story tests for service happy/reject paths.
4. Commit: `feat(search): add grouped sections and highlighted result rows`

### Slice 4 — Views wired to sections (RED → GREEN)

1. Refactor `global_search` / `global_search_suggestions` views.
2. Integration tests: filter bar, no-query prompt, empty state, highlight in response.
3. Log-story tests for views.
4. Commit: `feat(search): wire global search views to grouped sections`

### Slice 5 — Production templates (RED → GREEN)

1. Replace `templates/search/results.html` + partials from mockup.
2. Integration tests: accordion markup (19), single-type flat (23), section toggles testids (07).
3. Commit: `feat(search): accordion results page and highlighted suggestions UI`

### Slice 6 — E2E + spec hygiene

1. Update `tests/e2e/test_journey_global_search.py` for summary line + suggestions see-all.
2. Optional: Playwright accordion expand (20).
3. Remove `@wip` from passing scenarios in `global-search.feature`.
4. Commit: `test(search): e2e journey for NAV-06 v2`

---

## 5. Scenario → Slice Mapping

| Scenarios | Slice |
|-----------|-------|
| 01–06, 12–13 | 4–5 (navbar flow, filters, empty/no-query) |
| 07–11, 19–24 | 3–5 (accordion, rows, navigation) |
| 09b–09c, 25 | 1, 3, 5 (highlight) |
| 14–16 | 4–5 (suggestions) |
| 17 | 2 (access scope) |
| 18 | existing navbar test (keep) |
| 20–22 | 5 + optional E2E (client-side collapse) |

---

## 6. Commit Strategy

Angular convention; one commit per slice above. Each slice: behavior tests green + log-story green before commit.

---

## 7. Definition of Done

- [ ] All 25 FOB-GLOBAL-SEARCH scenarios pass (integration + unit; E2E for 01–02, 18 minimum)
- [ ] `@wip` removed from `global-search.feature`
- [ ] No Status/Source filters in production templates
- [ ] Eight entity types searchable under accessible playbook scope
- [ ] Mockup and production UX visually aligned (accordion, highlight, filter bar)
- [ ] Log Story Script proven via caplog tests
- [ ] `docs/plans/NAV_06_GLOBAL_SEARCH_IMPLEMENTATION_PLAN.md` header note pointing to this V2 plan

---

## 8. GitHub Issue Body (paste when opening)

Use Sections A–F from this document inline in the issue description. Checkpoint command:

```bash
.venv/bin/python -m pytest tests/unit/test_search_highlight.py tests/unit/test_global_search_service.py tests/integration/test_global_search.py -v
```

Optional E2E:

```bash
.venv/bin/python -m pytest tests/e2e/test_journey_global_search.py -v
```

---

## 9. Approval

**Status**: Draft — awaiting user approval before Slice 1 implementation.

After approval: create GitLab issue, branch `feature/nav-06-global-search-v2`, execute Slice 1.
