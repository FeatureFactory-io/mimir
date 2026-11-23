# S18: EXPERTS-VIEW-02 Reconcile the public score-source breakdown

This plan uses [the consolidated contract](../pin-convergence-20261123-experts.md). Its shared interfaces, ownership decisions and verification-layer mapping govern this scenario. Commands in the graph below are the canonical execution gates; implementation and test bodies remain unimplemented.

```yaml
scenario: S18
acceptance_id: EXPERTS-VIEW-02
feature_file_path: docs/features/act-18-experts/experts-view.feature
feature_line: 16
primary_execution_layer: at
expanded_case_count: 1
dependencies:
- S12
- S17
system_dependencies: []
status: converged_plan_unapplied
source_report_sha256:
- b09e2a7f3fef13518a4ff2a010d848468a2b0bee66f00ad9f6598135fd4f7247
```

## A — Context map


Verified in `/Users/denispetelin/GitHub/mimir-experts-replay`:

| File:lines | Context |
|---|---|
| `docs/features/act-18-experts/experts-view.feature:16–20` | Exact S18 contract: four source amounts, reconciliation to 8200, separate category subtotals. |
| `test-data/experts/cedar-rfp-01.json:139–193` | Maria’s historical events yield sources 5000/1600/1200/400; categories Design 7200, Development 1000. |
| `docs/architecture/SAO.md:3836–3895` | Immutable ledger, snapshot categories, live source/category projections and public detail boundaries. |
| `docs/ux/IA_guidelines.md:1152–1218` | Public detail context rail, seven exact viewports and a separate category section. |
| `templates/mockups/experts/_breakdown.html:1–5` | Existing recipe already separates source-table body, total footer and category `<dl>`. |

Actual implementation bodies inspected: `mockups/experts_views.py:38–58` derives display fields directly from fictional JSON; it is a prototype, not a reusable production projection. `tests/e2e/conftest.py:101–117,141–169` supplies real function-scoped `page` and optional function-scoped `live_server_url`. `docs/features/steps/http_steps.py` contains only three generic HTTP primitives; S18 bindings remain absent.

## B — Do not do


- Do not copy prototype JSON projection into production or create a second score calculator/parser.
- Do not filter Maria’s total to Design: her Development awards contribute to both overall total and PIP source.
- Do not treat category rows or the total footer as source rows.
- Do not derive numeric values from stored summary prose, declared fixture totals or CSS text fragments.
- Do not award Karma, regenerate/persist summaries or modify profiles on production GET.
- Do not add MCP, provider calls, ToolExecutor, messaging or infrastructure.
- Do not remove feature-level `@wip` while sibling contracts remain unimplemented.
- Do not replace working functions or upstream-owned skeletons with raising stubs.

## C — Governing architecture and dependencies


Applicable headings: **Experts & Karma delivery architecture — planned delta**, **Awards, projections and transaction boundaries**, **Web delivery and notification reuse**, **Test strategy for this delta**. IA §11 governs presentation and browser certification.

S03 owns the ledger, numeric projection, historical Cedar adapter, shared HTML parser and `_breakdown.html`. S17 owns public-detail DTO/view/template/route and includes the shared breakdown. S12 owns:

`assert_karma_source_rows(html, expected: Mapping[str, int], total_test_id, expected_total)`

Reuse that helper; no second HTML parser or numerical UI projection. If scheduling requires earlier helper availability, parent may merge its ownership into S03 and replace dependency S12; no reverse dependency on S18.

This scenario adds dedicated proofs only. Upstream production interfaces already cover its behavior; no additional production method or template edit is necessary. Any discovered missing production behavior belongs to the owning S03/S17 contract and must be reconciled before execution.

## D — Tests to create and exact assertions


| Test | Assertions |
|---|---|
| `test_public_score_breakdown_with_cedar_sources_reconciles` | Real client GET `/experts/mrodriguez/` returns 200; shared helper requires exactly Released playbooks=5000, PIP contributions=1600, Consumption=1200, Learning=400 and displayed `expert-karma-total`=8200. Source sum equals total; formatted total is `8,200`. |
| `test_public_score_breakdown_with_category_subtotals_keeps_separate_sections` | Shared parser finds category section Design=7200 and Development=1000; category sum=8200; neither category appears in the source tbody; source section has exactly four source rows, excluding header/footer. |
| `test_public_score_breakdown_with_new_ledger_event_reads_live_totals` | After baseline GET, insert one legitimate historical test award of 100 PIP points in Development using S03’s ledger schema. Next GET shows PIP=1700, total=8300, Development=1100, Design=7200; stored paragraph remains unchanged. Oracle values are expectations, never projection input. |
| `test_public_score_breakdown_with_repeated_get_preserves_domain_state` | Snapshot real ledger rows and ExpertProfile persisted fields after fixture setup; authenticated and anonymous repeated GETs preserve both snapshots. Both responses reconcile to the same sources and total. No summary refresh call is needed. |
| `test_s18_behave_contract_with_exact_name_executes_without_skips` | Spawn existing acceptance runner against only `experts-view.feature`, explicitly `--tags=@experts`, exact anchored scenario name; structured result must show precisely one passed scenario, five passed steps, zero skipped/undefined/failed steps. This overrides default WIP exclusion without changing unrelated contracts. |
| `test_public_score_breakdown_with_required_viewport_stays_readable` | Seven parametrized actual production-page browser runs: correct four sources/total and separate categories; no document overflow or clipped numeric cells; source/category sections visible through normal scrolling; read column precedes rail below 768px. |

Backend checkpoint:

`pytest tests/integration/test_experts_public_score_breakdown.py -x`

Acceptance checkpoint:

`pytest tests/integration/test_experts_s18_behave.py -x`

Browser checkpoint:

`E2E_LIVE_SERVER_SCOPE=function pytest -c tests/e2e/pytest.ini -o addopts= -p no:playwright -p no:asyncio -p no:anyio tests/e2e/test_experts_public_score_breakdown.py -x`

Expected execution counts: four backend tests, one acceptance-wrapper test executing one actual scenario, seven browser cases. No zero-selection/skipped outcome certifies completion.

The wrapper uses `sys.executable manage.py behave --simple --tags=@experts --name '^EXPERTS-VIEW-02 Reconcile the public score-source breakdown$' docs/features/act-18-experts/experts-view.feature`, acceptance settings and a structured Behave report. It must fail loudly on runner failure or unexpected counts.

## E — Log story


No new production log-story rows: S18 introduces no service/controller action or decision branch. Ledger projection and public-detail request logging remain owned and proved by S03/S17. Dedicated reconciliation assertions must not introduce redundant logging helpers or production mutations.

`log_story_script: []`, `log_tests: []`; no S18 log-story command. This exemption applies only while the footprint remains proof-only.

## F — MCP


Not applicable. Public HTML inspection adds or changes no MCP tool, facade registration, REST receipt or transport. No T1/T2/T3 registration proof is required for S18.

## G — Agent proofs


Not applicable. SAO §17 concerns summary generation; S18 reads stored prose and live ledger totals. No model call, agent capability, PRF row or ScriptedLLM fixture is added.

## H — Mockup graduation and delivery graph


Consume S03’s graduation of `templates/mockups/experts/_breakdown.html` into `templates/experts/_breakdown.html`, and S17’s detail graduation into `templates/experts/detail.html`. Production keeps the shared shell, Bootstrap tokens, table caption, row headings, responsive wrapper and independent category section. S18 certifies those actual outputs; it does not duplicate template graduation.

Browser profiles: wide-low 1280×800; large-desktop 1920×1080; laptop 1512×982; tablet-portrait 768×1024; tablet-landscape 1024×768; phone 390×844; minimum-phone 360×800. Capture actual production-detail evidence for FOB-EXPERT-VIEW-1 with deployed/local commit and environment. Parent records reviewer/result/screenshots in the shared responsive evidence record; passing automated geometry alone is not human visual approval.

Proposed footprint, all test/catalog changes:





Graph activity identifiers refer to the live guidance bundle; the replay checkout has no local `.windsurf/workflows/FeatureFactory/BPE/` directory. Do not invent local activity files.

Full skeleton text follows. All paths below are relative to the verified replay repository root; no files were written.

**Create** `tests/integration/test_experts_public_score_breakdown.py`:

```python
"""S18 production score reconciliation proofs."""
from __future__ import annotations

import pytest
from django.test import Client

pytestmark = pytest.mark.django_db

def test_public_score_breakdown_with_cedar_sources_reconciles(client: Client) -> None:
    """Prove the baseline source breakdown through a real production GET.

    :param client: Real Django client. Example: Client().
    :return: None. Example: None after 5000+1600+1200+400=8200.
    :raises AssertionError: If status, exact source rows or total differs.
    """
    # Load S03 baseline; reuse S12 assert_karma_source_rows with expert-karma-total.
    raise NotImplementedError()

def test_public_score_breakdown_with_category_subtotals_keeps_separate_sections(client: Client) -> None:
    """Prove independent source and category dimensions in rendered HTML.

    :param client: Real Django client. Example: Client().
    :return: None. Example: None for Design=7200, Development=1000.
    :raises AssertionError: If categories enter source tbody or sums differ.
    """
    # Reuse find_by_test_id/element_text/_walk_elements; introduce no parser.
    raise NotImplementedError()

def test_public_score_breakdown_with_new_ledger_event_reads_live_totals(client: Client) -> None:
    """Prove fresh ledger data changes numbers without changing stored prose.

    :param client: Real Django client. Example: Client().
    :return: None. Example: None for PIP=1700 and total=8300.
    :raises AssertionError: If the second GET uses stale or fixture totals.
    """
    # Import baseline; GET; insert 100-point Development PIP test event; GET again.
    raise NotImplementedError()

def test_public_score_breakdown_with_repeated_get_preserves_domain_state(client: Client) -> None:
    """Prove public detail reads do not award or refresh summaries.

    :param client: Real Django client. Example: Client().
    :return: None. Example: None when ledger/profile snapshots remain equal.
    :raises AssertionError: If authenticated or guest GET changes domain rows.
    """
    # Snapshot after setup; authenticate with baseline Elena, then logout and repeat.
    raise NotImplementedError()
```

**Create** `tests/integration/test_experts_s18_behave.py`:

```python
"""Exact S18 living-spec runner proof."""
from __future__ import annotations

from pathlib import Path

def test_s18_behave_contract_with_exact_name_executes_without_skips(tmp_path: Path) -> None:
    """Execute only EXPERTS-VIEW-02 against the isolated acceptance database.

    :param tmp_path: Report directory. Example: Path("/tmp/pytest/s18").
    :return: None. Example: None for one scenario and five passed steps.
    :raises AssertionError: If subprocess fails, selects zero or skips a step.
    """
    # Explicit @experts overrides default not-@wip; inspect structured report.
    raise NotImplementedError()
```

**Append** imports and these uniquely owned bindings to S03’s planned `docs/features/steps/experts_steps.py`; retain its existing imports and shared baseline/open-path bindings:

```python
from behave import then
from behave.runner import Context

@then("score sources are Released playbooks 5000, PIP contributions 1600, Consumption 1200 and Learning 400")
def public_score_sources(context: Context) -> None:
    """Check the four exact source labels and values in the real response.

    :param context: Actual AT response context. Example: context.response.
    :return: None. Example: None after shared source helper succeeds.
    :raises AssertionError: If any source label/value is missing or duplicated.
    """
    raise NotImplementedError()

@then("the source rows sum to the displayed total 8200")
def public_score_source_sum(context: Context) -> None:
    """Reconcile source tbody values with expert-karma-total.

    :param context: Actual AT response context. Example: context.response.
    :return: None. Example: None for sum=8200 and formatted total 8,200.
    :raises AssertionError: If source sum and displayed total disagree.
    """
    raise NotImplementedError()

@then("category subtotals Design 7200 and Development 1000 are not mislabeled as source rows")
def public_score_category_separation(context: Context) -> None:
    """Check category values reside only in the independent category section.

    :param context: Actual AT response context. Example: context.response.
    :return: None. Example: None for the two correctly classified categories.
    :raises AssertionError: If category/source sections overlap or values differ.
    """
    raise NotImplementedError()
```

**Create** `tests/e2e/test_experts_public_score_breakdown.py`:

```python
"""S18 browser certification using the existing E2E lifecycle."""
from __future__ import annotations

import pytest
from playwright.sync_api import Page

@pytest.mark.parametrize(
    "viewport",
    [(1280, 800), (1920, 1080), (1512, 982), (768, 1024),
     (1024, 768), (390, 844), (360, 800)],
)
def test_public_score_breakdown_with_required_viewport_stays_readable(
    page: Page,
    live_server_url: str,
    transactional_db: None,
    viewport: tuple[int, int],
) -> None:
    """Certify actual detail geometry, legibility and reconciled numbers.

    :param page: Existing function-scoped page. Example: Chromium Page.
    :param live_server_url: Existing live-server URL. Example: "http://localhost:8081".
    :param transactional_db: Real transactional database fixture. Example: None.
    :param viewport: IA dimensions. Example: (390, 844).
    :return: None. Example: None for visible, separated, reconciled rows.
    :raises AssertionError: If content, geometry or responsive reading order fails.
    """
    # Load Cedar before browser request; open production URL; use stable test IDs.
    # Share reconciliation helper with page.content(); inspect actual cell geometry.
    raise NotImplementedError()
```

**Append** to `docs/features/CATALOG.md` during structural apply:

```markdown

## Parent convergence

Authoritative acceptance source: `docs/features/act-18-experts/experts-view.feature:16`; 1 expanded case(s), primary layer `at`. Dependencies: S12, S17. The full scenario includes all composed journey/UAT obligations assigned in the consolidated contract. Shared Make/catalog registration belongs only to S03.

## Canonical feature execution graph

```yaml
feature_execution_graph:
  feature_ref: EXPERTS-VIEW-02
  scenario_dependencies:
  - S12
  - S17
  nodes:
  - id: S18-N1-backend
    title: Prove shared production projection and read-only GET
    bpe: BPE-02
    depends_on: []
    footprint:
    - tests/integration/test_experts_public_score_breakdown.py
    tests:
    - test_public_score_breakdown_with_cedar_sources_reconciles
    - test_public_score_breakdown_with_category_subtotals_keeps_separate_sections
    - test_public_score_breakdown_with_new_ledger_event_reads_live_totals
    - test_public_score_breakdown_with_repeated_get_preserves_domain_state
    gate:
      command: pytest tests/integration/test_experts_public_score_breakdown.py -x
    guidance_bundle:
      activity: BPE/BPE-02-Implement_Backend.md
      rules:
      - do-test-first
      - do-not-mock-in-integration-tests
      - do-write-concise-methods
      - do-docstring-format
    notes: Proof-only; production implementation and log stories supplied by S03/S17.
  - id: S18-N2-acceptance
    title: Bind and execute the exact living specification
    bpe: BPE-04
    depends_on:
    - S18-N1-backend
    footprint:
    - docs/features/steps/experts_steps.py
    - tests/integration/test_experts_s18_behave.py
    tests:
    - test_s18_behave_contract_with_exact_name_executes_without_skips
    gate:
      command: make test-experts-s18-at
    guidance_bundle:
      activity: BPE/BPE-04-Implement_Feature_Acceptance_Tests.md
      rules:
      - do-test-first
      - do-not-mock-in-integration-tests
      - pytest
  - id: S18-N3-browser
    title: Certify real public breakdown at seven viewports
    bpe: BPE-05
    depends_on:
    - S18-N2-acceptance
    footprint:
    - tests/e2e/test_experts_public_score_breakdown.py
    tests:
    - test_public_score_breakdown_with_required_viewport_stays_readable
    gate:
      command: make test-experts-s18-browser
    guidance_bundle:
      activity: BPE/BPE-05-Implement_Journey_Certification_Tests.md
      rules:
      - do-test-first
      - do-semantic-versioning-on-ui-elements
      - pytest
  - id: S18-N4-dod
    title: Review complete reconciliation evidence
    bpe: BPE-06
    depends_on:
    - S18-N1-backend
    - S18-N2-acceptance
    - S18-N3-browser
    footprint: []
    gate:
      command: make test-experts-s18
    additional_required_gates:
    - S18-N3-browser
    human_gate:
    - Review production-detail screenshots at all seven IA profiles
    guidance_bundle:
      activity: BPE/BPE-06-Check_Definition_of_Done.md
      rules:
      - do-test-first
      - do-github-issues
      - do-follow-commit-convention
```

## Lessons Learned

Source and category numbers are independent dimensions of the same ledger: Maria’s 1000 Development points must remain part of PIP=1600 and total=8200. Existing mockups illustrate this correctly but read JSON, so they cannot prove production behavior. Shared parser/helper ownership prevents several later profile scenarios from creating incompatible reconciliation logic.

PIN-04/05 owns the combined issue/handoff/human GO gate. After GO, commit each graph slice with `Refs #N` and its authorized issue update; final verified slice uses `Closes #N`. No per-worker permission request, implementation, tests, commits or issue mutations were performed.
