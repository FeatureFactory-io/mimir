# S26: GALDR-SUMMARY-04 Use a live numeric fallback without summary prose

This plan uses [the consolidated contract](../pin-convergence-20261123-experts.md). Its shared interfaces, ownership decisions and verification-layer mapping govern this scenario. Commands in the graph below are the canonical execution gates; implementation and test bodies remain unimplemented.

```yaml
scenario: S26
acceptance_id: GALDR-SUMMARY-04
feature_file_path: docs/features/act-18-experts/galdr-contribution-summary.feature
feature_line: 23
primary_execution_layer: at
expanded_case_count: 1
dependencies:
- S03
- S04
- S10
- S17
system_dependencies: []
status: converged_plan_unapplied
source_report_sha256:
- 7f710feb3c3efdd8e3c54540463149a977a8a73c725aa6e11ad8a3d8917c2ef0
```

## A — Context map


| Verified source | Lines | Relevance |
|---|---:|---|
| `docs/features/act-18-experts/galdr-contribution-summary.feature` | 29–33 | Exact Mike fallback acceptance contract. |
| `docs/architecture/SAO.md` | 3883–3905 | Independent live counts, GUI-only author copies, production routes. |
| `test-data/experts/cedar-rfp-01.json` | 419–457, 1104–1113 | Mike has `summary: null`, two public playbooks, 47 GUI copies within 470 author-consumption events; explicit channel/source filter. |
| `mockups/experts_views.py` | 38–58 | Prototype computes fallback from fixture fields; recipe only, unsuitable for production count calculations. |
| `templates/mockups/experts/detail.html` | 5–7 | Prototype distinguishes summary paragraph from numeric fallback; preserve distinction in production. |

Additional verified integration points: `accounts/views.py:285–317` owns the real authenticated profile; `tests/e2e/conftest.py:101–168` supplies function-scoped `page`, selectable function-scoped server and `live_server_url`. `pytest.ini` ignores E2E globally; `tests/e2e/pytest.ini` supplies separate browser settings/plugin exclusions.

Current state: Experts models, services, Cedar ORM adapter and production pages are not implemented. S03 owns `ExpertProfile.public_summary = TextField(blank=True, default="")`, normalizing JSON `null` to `""`; do not persist `None` into that nonnullable field. The current source contradicts the stale “baseline Mike has prose” instruction: Mike already has missing prose. Parent confirmed the actual source controls.

## B — Do-not-do list


- Do not add production counter, presenter, generator, fallback template or model implementations in S26.
- Do not derive copy counts from Karma points, all 470 consumption rows, `copy_count` JSON or event-identity parsing.
- Do not count private, draft, active or disabled playbooks as currently public released playbooks.
- Do not turn GET rendering into a receipt, award, summary generation or publication event.
- Do not fabricate prose, mutate the shared Cedar JSON, change score/category history or weaken existing profile authentication.
- Do not add tools, ToolExecutor, queue, broker, model adapter or provider rehearsal.
- Do not treat collection, skips, `@wip` exclusions or a prototype screenshot as completion.

## C — Governing architecture and ownership


Applicable SAO headings: **Awards, projections and transaction boundaries**; **Web delivery and notification reuse**; **Test strategy for this delta**; §17 **Privacy, bounds and failure policy**, **Observability and proof gates**.

Consume, without reimplementing:

- **S03:** real Cedar rows; immutable numeric projection fields `released_public_playbook_count` and `successful_gui_copy_count`; explicit `event_channel`; shared `tests/support/experts_html.py`.
- **S04:** shared card presenter and exact readable fallback formatting.
- **S10:** own-profile fallback production branch.
- **S17:** public-detail fallback production branch and public evidence filtering.
- **S23:** real `AgentInteraction` persistence, used here only to observe that GET requests create no generation records.

S23 is an evidence dependency, not a generation prerequisite for displaying missing-summary UI. If the parent removes this dependency, the plan must explicitly downgrade its no-generation claim to source inspection and unchanged profile evidence; it must not silently claim equivalent runtime evidence.

No external prerequisite, stub infrastructure or scope-removal proposal is needed.

## D — Tests to create and exact assertions


Create `tests/integration/test_experts_numeric_fallback.py`.

| Test | Required assertions |
|---|---|
| `test_numeric_fallback_with_cedar_mike_uses_live_counts` | Actual profile stores `""`; actual Mike author-consumption rows total 470; exact eligible source/channel subset totals 47; actual public/released authored playbooks total two. Real Development response contains Mike’s exact hint `2 released playbooks · 47 copies`. |
| `test_numeric_fallback_with_playbook_visibility_changes_refreshes_next_request` | Start 2/47; change an actual Mike playbook public→private; next response gives 1/47. Restore and test draft/active/disabled independently. Add nonqualifying playbooks and another author’s public/released book; Mike’s count does not increase. Restore/transition one real book to public/released; next response increases appropriately. No fixture oracle/count edits. |
| `test_numeric_fallback_with_ledger_changes_counts_only_gui_author_consumption` | Add one valid author-consumption/gui_copy stored row; next response 2/48. Add consumption/mcp-detail, consumption/export, historical channel and learning/gui_copy rows; count remains 48. Use actual canonical channel constants finalized by S03, not invented identity prefixes. Verify recipient isolation. |
| `test_numeric_fallback_with_missing_summary_is_consistent_across_surfaces` | Real list, public detail and Mike-authenticated own profile show matching numeric fallback; summary paragraph hooks are absent. Precreate Mike’s token before the observation window because the existing own-profile GET can create it. No `None` assignment to nonnullable profile field. |
| `test_numeric_fallback_with_repeated_gets_preserves_summary_and_generation_history` | Snapshot profile summary/refresh metadata and real `AgentInteraction` rows; request all three surfaces, mutate eligible numeric facts, request again. Numeric output refreshes; summary remains empty; refresh metadata and interaction rows unchanged. No generation entry/llm_call logging appears. GETs create no award rows. |
| `test_numeric_fallback_log_story_happy` | Real request with `X-Request-ID`; assert inherited S03/S04 beats through `assert_log_story`, actual counts and numeric-fallback branch; no prose/email/token bodies. |

Eligibility distinction: the author count filters `recipient=Mike`, `source_kind=consumption`, `event_channel=gui_copy`. Guest/self copies create no award rows under S36–S38; they cannot legitimately be represented as eligible author awards. Do not forge invalid guest/self author awards and claim the read query can reconstruct missing actor provenance. Reuse S36–S38 receipt proofs at integration convergence; S39/S42 certify successful MCP/export receipts that must not enter this GUI subset.

Create `tests/e2e/test_experts_numeric_fallback.py`:

- `test_numeric_fallback_with_reload_shows_updated_live_counts`: real Elena login, navigate Development, exact Mike hint, View profile, no public paragraph. Mutate actual ORM facts between browser requests and reload: fresh count appears. Test at 390×844 and 1280×800; visible hint remains readable and no invented prose appears.
- `test_numeric_fallback_with_own_profile_shows_no_expansion_control`: real Mike login, own profile fallback visible, no summary paragraph or Show more/Show less control for missing prose.

Append only distinct S26 bindings to `docs/features/steps/experts_summary_steps.py`; reuse Cedar, Hana background, Elena authentication/navigation and shared HTML parser. No duplicate generic Given/When registration.

Behavior checkpoint:

```bash
pytest tests/integration/test_experts_numeric_fallback.py -x
```

Log checkpoint:

```bash
pytest tests/integration/test_experts_numeric_fallback.py::test_numeric_fallback_log_story_happy -x
```

Exact AT checkpoint, explicitly overriding feature-level WIP selection:

```bash
DJANGO_SETTINGS_MODULE=mimir.settings.acceptance python manage.py behave --simple --tags=@experts --name='^GALDR-SUMMARY-04 Use a live numeric fallback without summary prose$' docs/features/act-18-experts/galdr-contribution-summary.feature
```

Browser checkpoint, separate process/configuration:

```bash
E2E_LIVE_SERVER_SCOPE=function pytest -c tests/e2e/pytest.ini -o addopts= -p no:playwright -p no:asyncio -p no:anyio tests/e2e/test_experts_numeric_fallback.py -x
```

Convergence gates: `make test-at-harness`, then `make test-at-experts` after WIP ownership is reconciled across all contracts. Exact S26 AT must run one scenario with all steps passed; browser/integration gates must collect and execute named tests without skips. These commands are proposed, not run.

## E — Log story


S26 adds no service/controller and therefore no new production logger.

Certify inherited logs in the same green slice as numeric behavior:

| Where, owned upstream | Beat | Trigger | Required fields |
|---|---|---|---|
| S03 Experts query entry | entry | Development GET | correlation_id, category=development |
| S03 projection completion | exit | Mike projection built | subject_id, released_public_playbook_count=2, successful_gui_copy_count=47 |
| S04 shared presenter | branch | Empty stored prose | subject_id, presentation=numeric_fallback |
| Existing Experts list view | exit | Successful render | correlation_id, status=200 |

Parent must reconcile the exact upstream `where` names before skeleton application. Do not create parallel log events merely to satisfy this table. Use INFO and the existing `tests/support/log_story.py:9–36` helper. An empty summary is a supported branch, not an error/reject story.

## F — MCP surface


Not applicable: S26 changes no MCP tool, schema, facade, authorization or registration. Therefore no new T1/T2/T3 tests. Receipt channels remain upstream implementation responsibilities.

## G — Agent proofs


No new PRF row or ScriptedLLM fixture: this is a model-free rendering certification. §17 expressly requires numeric fallback to read live projections without another completion.

The unchanged real `AgentInteraction` history and summary metadata test is an ordinary DB integration test, not an `agent_proof` test. S23/S27 retain the agent orchestration proofs and finite ScriptedLLM seams. No ToolExecutor is applicable to T-00.

## H — Graduation and execution graph


Graduate the missing-summary recipe from `/mockups/experts/` into existing S04/S10/S17-owned production branches. Verify `/experts/?category=development`, `/experts/mchen/` and `/auth/user/profile/`; never direct production links to mockups.

Preserve the exact middle dot and text. List hint may use the established visual clamp; numeric fallback is visibly distinct from a generated public paragraph. Public detail uses `expert-numeric-fallback`, not `expert-contribution-summary`. Own-profile fallback must not expose summary expansion controls. Shared production hooks should be finalized by their owners before S26 begins.



### Full skeleton text

Destination: **create** `tests/integration/test_experts_numeric_fallback.py`. All assertions above belong in future bodies; no implementation during PIN.

```python
"""S26 real-DB certification of live numeric contribution fallbacks."""

from __future__ import annotations

import pytest
from django.test import Client


@pytest.mark.django_db
def test_numeric_fallback_with_cedar_mike_uses_live_counts(client: Client) -> None:
    """Prove baseline counts from actual persisted rows.

    :param client: Real Django client. Example: Client().
    :return: None. Example: None after exact 2/47 and 470 assertions.
    :raises AssertionError: If source/channel rows or rendered hint disagree.
    """
    raise NotImplementedError()


@pytest.mark.django_db
def test_numeric_fallback_with_playbook_visibility_changes_refreshes_next_request(
    client: Client,
) -> None:
    """Prove current publication state changes the next request's count.

    :param client: Real Django client. Example: Client().
    :return: None. Example: None after 2/47, 1/47 and restoration checks.
    :raises AssertionError: If private/draft/active/disabled/other-author rows count.
    """
    raise NotImplementedError()


@pytest.mark.django_db
def test_numeric_fallback_with_ledger_changes_counts_only_gui_author_consumption(
    client: Client,
) -> None:
    """Prove recipient/source/channel isolation using actual inserted awards.

    :param client: Real Django client. Example: Client().
    :return: None. Example: None after 47 becomes 48 only for eligible GUI row.
    :raises AssertionError: If learning, MCP, export or other recipients inflate it.
    """
    raise NotImplementedError()


@pytest.mark.django_db
def test_numeric_fallback_with_missing_summary_is_consistent_across_surfaces(
    client: Client,
) -> None:
    """Prove list/detail/own-profile consume the same missing-summary facts.

    :param client: Real Django client. Example: Client().
    :return: None. Example: None after all three show exact numeric fallback.
    :raises AssertionError: If a public paragraph or expansion control is fabricated.
    """
    raise NotImplementedError()


@pytest.mark.django_db
def test_numeric_fallback_with_repeated_gets_preserves_summary_and_generation_history(
    client: Client,
) -> None:
    """Observe no summary refresh, interaction or award during fresh reads.

    :param client: Real Django client. Example: Client().
    :return: None. Example: None with updated counts and unchanged summary history.
    :raises AssertionError: If GET creates generation/award rows or stores prose.
    """
    raise NotImplementedError()


@pytest.mark.django_db
def test_numeric_fallback_log_story_happy(
    client: Client, caplog: pytest.LogCaptureFixture,
) -> None:
    """Assert inherited query/presenter logs with the shared story helper.

    :param client: Real Django client. Example: Client().
    :param caplog: Pytest log capture. Example: INFO capture for request s26.
    :return: None. Example: None after all declared INFO beats match.
    :raises AssertionError: If beats/counts/correlation are missing or PII is logged.
    """
    raise NotImplementedError()
```

Destination: **append**, without replacing existing S23/S24 bindings, `docs/features/steps/experts_summary_steps.py`.

```python
from behave import given, then, when
from behave.runner import Context


@given("Mike has no stored contribution summary")
def mike_has_no_stored_contribution_summary(context: Context) -> None:
    """Verify the shared baseline normalized Mike's null prose to empty storage.

    :param context: Shared Cedar AT context. Example: context.cedar_dataset.
    :return: None. Example: None with persisted public_summary == "".
    :raises AssertionError: If Mike is absent or stored prose is nonempty.
    """
    raise NotImplementedError()


@when("Elena opens the Development leaderboard")
def elena_opens_development_leaderboard(context: Context) -> None:
    """Use common Elena authentication and a real production Django GET.

    :param context: Shared AT context. Example: context.client.
    :return: None. Example: None with response for /experts/?category=development.
    :raises AssertionError: If the request does not return the actual leaderboard.
    """
    raise NotImplementedError()


@then(
    'Mike\'s hint is "{expected}" from live released-playbook and GUI-copy counts'
)
def mike_hint_matches_live_counts(context: Context, expected: str) -> None:
    """Compare the real card hint and independently persisted qualifying rows.

    :param context: AT response and shared Cedar context. Example: context.response.
    :param expected: Exact hint. Example: "2 released playbooks · 47 copies".
    :return: None. Example: None after exact rendered and row-count assertions.
    :raises AssertionError: If hint, qualifying counts or 47/470 distinction fails.
    """
    raise NotImplementedError()


@then("no public-summary paragraph is fabricated")
def no_public_summary_paragraph_is_fabricated(context: Context) -> None:
    """Inspect real public response and unchanged empty profile storage.

    :param context: Shared response context. Example: Mike's rendered card.
    :return: None. Example: None with no summary paragraph and empty storage.
    :raises AssertionError: If prose is rendered or persisted without a summary.
    """
    raise NotImplementedError()
```

Convergence must assign the Development-opening phrase one owner if another report proposes it; keep this implementation once and reuse it.

Destination: **create** `tests/e2e/test_experts_numeric_fallback.py`.

```python
"""S26 real-browser missing-summary certification."""

import pytest
from playwright.sync_api import Page


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("viewport", [(390, 844), (1280, 800)])
def test_numeric_fallback_with_reload_shows_updated_live_counts(
    page: Page, live_server_url: str, viewport: tuple[int, int],
) -> None:
    """Verify actual navigation, missing prose and fresh numeric rendering.

    :param page: Function-scoped real browser page. Example: Chromium Page.
    :param live_server_url: Existing live-server URL. Example: http://localhost:8081.
    :param viewport: Width/height pixels. Example: (390, 844).
    :return: None. Example: None after visible 2/47 then changed count on reload.
    :raises AssertionError: If fallback is stale, unreadable or fabricates prose.
    """
    raise NotImplementedError()


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
def test_numeric_fallback_with_own_profile_shows_no_expansion_control(
    page: Page, live_server_url: str,
) -> None:
    """Authenticate Mike through the real login and inspect his own profile.

    :param page: Function-scoped browser page. Example: Chromium Page.
    :param live_server_url: Existing server URL. Example: http://localhost:8081.
    :return: None. Example: None after numeric fallback and absent expansion.
    :raises AssertionError: If own profile invents summary text or expansion state.
    """
    raise NotImplementedError()
```

No new helper architecture is required: load Cedar through `load_cedar_baseline()`, obtain users/playbooks from its shared mappings and parse response HTML with S03’s `find_by_test_id`/`element_text`.

Proposed implementation footprint: the three certification files above plus the parent-owned scenario plan. Production footprint remains empty. Serialize append access to shared summary steps with S23–S29. Sequential commits after PIN-05 GO: backend certification including log assertions; exact AT binding; browser certification; final DoD evidence. Each uses `Refs #N`; final closure uses the verified final SHA and `Closes #N`.

## Parent convergence

Authoritative acceptance source: `docs/features/act-18-experts/galdr-contribution-summary.feature:23`; 1 expanded case(s), primary layer `at`. Dependencies: S03, S04, S10, S17. The full scenario includes all composed journey/UAT obligations assigned in the consolidated contract. Shared Make/catalog registration belongs only to S03.

## Canonical feature execution graph

```yaml
feature_execution_graph:
  feature_ref: GALDR-SUMMARY-04
  scenario_id: S26
  external_dependencies:
  - S03
  - S04
  - S10
  - S17
  - S23
  nodes:
  - id: S26-N1
    title: Certify real projections and missing-summary presentation
    bpe: BPE-02
    depends_on: []
    footprint:
    - tests/integration/test_experts_numeric_fallback.py
    tests:
    - test_numeric_fallback_with_cedar_mike_uses_live_counts
    - test_numeric_fallback_with_playbook_visibility_changes_refreshes_next_request
    - test_numeric_fallback_with_ledger_changes_counts_only_gui_author_consumption
    - test_numeric_fallback_with_missing_summary_is_consistent_across_surfaces
    - test_numeric_fallback_with_repeated_gets_preserves_summary_and_generation_history
    - test_numeric_fallback_log_story_happy
    log_story_rows:
    - upstream-S03-query:entry
    - upstream-S03-projection:exit
    - upstream-S04-presenter:branch
    - upstream-list-view:exit
    gate:
      command: pytest tests/integration/test_experts_numeric_fallback.py -x
      log_story_command: pytest tests/integration/test_experts_numeric_fallback.py::test_numeric_fallback_log_story_happy
        -x
    guidance_bundle:
      activity: BPE/BPE-02-Implement_Backend.md
      rules:
      - do-test-first
      - do-not-mock-in-integration-tests
      - do-assert-log-story
      - do-docstring-format
    notes: Tests only; upstream owners fill production behavior.
  - id: S26-N2
    title: Bind exact numeric-fallback acceptance contract
    bpe: BPE-04
    depends_on:
    - S26-N1
    footprint:
    - docs/features/steps/experts_summary_steps.py
    tests:
    - GALDR-SUMMARY-04
    gate:
      command: make test-experts-s26-at
    guidance_bundle:
      activity: BPE/BPE-04-Implement_Feature_Acceptance_Tests.md
      rules:
      - do-test-first
      - do-not-mock-in-integration-tests
      - pytest
    notes: Reuse common steps/parser; require one executed scenario, no skips.
  - id: S26-N3
    title: Certify production fallback in real browser
    bpe: BPE-05
    depends_on:
    - S26-N2
    footprint:
    - tests/e2e/test_experts_numeric_fallback.py
    tests:
    - test_numeric_fallback_with_reload_shows_updated_live_counts
    - test_numeric_fallback_with_own_profile_shows_no_expansion_control
    gate:
      command: make test-experts-s26-browser
    guidance_bundle:
      activity: BPE/BPE-05-Implement_Journey_Certification_Tests.md
      rules:
      - do-test-first
      - do-semantic-versioning-on-ui-elements
      - pytest
  - id: S26-N4
    title: Reconcile evidence and Definition of Done
    bpe: BPE-06
    depends_on:
    - S26-N1
    - S26-N2
    - S26-N3
    footprint: []
    gate:
      command: make test-experts-s26
      log_story_command: pytest tests/integration/test_experts_numeric_fallback.py::test_numeric_fallback_log_story_happy
        -x
      acceptance_command: DJANGO_SETTINGS_MODULE=mimir.settings.acceptance python manage.py behave --simple --tags=@experts
        --name='^GALDR-SUMMARY-04 Use a live numeric fallback without summary prose$' docs/features/act-18-experts/galdr-contribution-summary.feature
      browser_command: E2E_LIVE_SERVER_SCOPE=function pytest -c tests/e2e/pytest.ini -o addopts= -p no:playwright
        -p no:asyncio -p no:anyio tests/e2e/test_experts_numeric_fallback.py -x
      convergence_commands:
      - make test-at-harness
      - make test-at-experts
    guidance_bundle:
      activity: BPE/BPE-06-Check_Definition_of_Done.md
      rules:
      - do-assert-log-story
      - do-github-issues
      - do-follow-commit-convention
  scenario_dependencies:
  - S03
  - S04
  - S10
  - S17
```

## Lessons Learned

The stale prose-baseline instruction was contradicted by the actual Cedar source and resolved in favor of that source. The important distinction is 47 eligible GUI-copy author awards within 470 total author-consumption awards; a fixture-backed prototype can display the correct sentence while proving none of the live filtering behavior. S26 should expose mistakes through persisted-row mutations and fresh requests, while leaving counter/presenter ownership upstream. No files, tests, commits or external changes were performed.
