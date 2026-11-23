# S47: KARMA-CATEGORY-01 Resolve primary-category ties

This plan uses [the consolidated contract](../pin-convergence-20261123-experts.md). Its shared interfaces, ownership decisions and verification-layer mapping govern this scenario. Commands in the graph below are the canonical execution gates; implementation and test bodies remain unimplemented.

```yaml
scenario: S47
acceptance_id: KARMA-CATEGORY-01
feature_file_path: docs/features/act-18-experts/karma-accrual.feature
feature_line: 141
primary_execution_layer: at
expanded_case_count: 2
dependencies:
- S03
system_dependencies: []
status: skeleton_applied_unimplemented
source_report_sha256:
- bfd83f7863833cc86593939a91e5cd8e5ef2e01f1b95e7566440b5779cd114a8
```

### A — Context map


| Verified source | Lines | Governing evidence |
|---|---:|---|
| `docs/features/act-18-experts/karma-accrual.feature` | 161–168 | Exactly two examples: TIE01→Development; TIE02→Design. |
| `test-data/experts/cedar-rfp-01.json` | 914–945, 1113 | Both users have 5,000+5,000; released counts break TIE01; alphabetical names break TIE02. Fallback public counts are explicitly separate. |
| `docs/architecture/SAO.md` | 3836–3853, 3883–3895 | Immutable historical category attribution; positive ledger projections; primary-category rule versus public fallback rule. |
| `methodology/models/playbook.py`; `methodology/models/playbook_version.py` | 24–60; 23–66 | Canonical lowercase categories; actual author/current status/category fields; multiple history rows belong to one playbook. |
| `mockups/experts_views.py`; `templates/mockups/experts/list.html` | 107–133; 13–19 | Prototype filters declared fixture categories, so it proves no resolver. Existing card badge/selectors provide browser presentation reference. |

Also inspected replay `AGENTS.md`, `CLAUDE.md`, orient roster, all three `/tmp` guidance files, journey:3126–3130, IA:1152–1192, real release service:490–567, acceptance hooks/config, log helper and existing browser fixtures.

### B — Do not do


- No second projection/resolver, award writer, schema migration or production fixture reader. S03 owns these interfaces.
- No release/PIP/live event hooks during historical fixture construction; do not earn another release award.
- No comparison against JSON `expected_primary_category` as production behavior.
- No version-history row count or released-award count as authored-playbook count.
- No visibility/public-evidence filter copied into the category tie rule.
- Preserve ledger event/category snapshots, baseline Cedar records and totals; projection is read-only.
- Do not conflate S08’s equal-total username leaderboard ordering with this category decision.
- No new MCP/agent capability, provider call, message, seed reset or deployment.

### C — Applicable architecture and count policy


Apply SAO **Services Layer**, **Experts & Karma delivery architecture — planned delta / Awards, projections and transaction boundaries**, **Test strategy for this delta**; IA §11 supplies existing presentation rules.

The governing interpretation is: sum immutable award-category snapshots; select maximum points; among those categories count distinct currently released `Playbook` PKs authored by that user in each playbook’s current stored category; choose the greatest count, then alphabetical category name. Count private released playbooks too. Ignore draft/active/disabled playbooks and other authors. One playbook with several `PlaybookVersion` rows counts once.

Journey:3126–3130 and SAO:3885 say “released playbooks,” while SAO:3891 and Cedar:1113 explicitly reserve **currently public released authored** counts for numeric fallback. Record the explicit field-level interpretation above in the parent’s reconciled plan/SAO before GO; it is derived policy, not an assertion that an existing resolver already implements it.

### D — Tests and exact assertions


| Planned test | Assertions |
|---|---|
| `test_primary_category_with_cedar_tie_expected_category` | Parameterize TIE01/TIE02; actual persisted ledger category totals each equal 5,000; total=10,000; actual distinct released counts match fixture; canonical resolver returns `development`/`design`; complete ledger snapshot unchanged. |
| `test_primary_category_with_policy_boundaries_expected_category` | Parameterized real ORM cases: points beat release count; private released counts; drafts/active/disabled and other authors do not; multiple versions count once; non-tied category cannot win by count; equal counts use alphabetical display name independent of insertion order; later playbook-category edit leaves award snapshots unchanged. |
| `test_category_tie_loader_with_unknown_variant_rejects` | ValueError before writes; baseline and ledger unchanged. |
| `test_primary_category_with_cedar_ties_log_story_happy` | Caplog proves canonical resolver’s entry→processing→branch→exit for both tie stages; no titles, email or tokens. |
| `test_karma_category_acceptance_with_exact_outline_two_examples` | Run real scoped Behave under acceptance settings; exactly two selected outline examples pass, with no selected skip/undefined/error. |
| `test_primary_category_with_cedar_tie_renders_correct_tab` | Real browser, each variant: user appears in resolved category with correct badge and 10,000; absent from other tied category; ORM ledger unchanged. |

AT bindings owned here only: `the isolated {variant} data`, `the user's primary playbook category is projected`, `the result is {category}`. Reuse S03’s existing baseline binding. Never import decorated step modules.

AT wrapper launches:
`manage.py behave --simple --tags=@experts --name=^KARMA-CATEGORY-01 --format=json --outfile=<tmp report> docs/features/act-18-experts/karma-accrual.feature`
with `DJANGO_SETTINGS_MODULE=mimir.settings.acceptance`.
The explicit tag selection overrides feature-level WIP for this named contract. Assert two matching expanded examples, not aggregate runner success alone.

### E — Log story


Reuse S03’s canonical resolver logging; no parallel log-producing resolver.

| Where | Beat | Trigger | Must include |
|---|---|---|---|
| Canonical primary-category resolver | entry | projection requested | numeric user ID, correlation ID |
| Same | processing | category totals projected | positive total, number of maximum-point candidates |
| Same | branch | TIE01 count decision | `reason=released_count`, selected category |
| Same | branch | TIE02 final decision | `reason=alphabetical`, selected category |
| Same | exit | resolved | selected category, unchanged projected total |

`assert_log_story` checks every row, including literal beat markers because its existing implementation matches supplied fragments rather than independently enforcing beat names.

Checkpoint:
`pytest tests/integration/test_experts_category_ties.py -x`

Log checkpoint:
`pytest tests/integration/test_experts_category_ties.py -k log_story -x`

### F — MCP tools


Not applicable. No tool registration, authorization forwarding or facade changes.

### G — Agent proofs


Not applicable. No SAO §17 capability change or PRF affected.

### H — Graduation and execution


No template graduation belongs to S47. Reuse S03 production route/template and shared `tests/support/experts_html.py` parser. Browser verification visits production `/experts/`, never `/mockups/`.

Proposed implementation footprint:

- CREATE `tests/support/experts_category_ties.py`
- CREATE `tests/integration/test_experts_category_ties.py`
- CREATE `tests/integration/test_experts_category_acceptance.py`
- CREATE `docs/features/steps/experts_category_steps.py`
- CREATE `tests/e2e/test_experts_category_ties.py`
- APPEND `docs/features/CATALOG.md` with three owned bindings.
- Parent APPEND reconciled policy in `docs/architecture/SAO.md`.
- S03-owned dependency files reused unchanged: `methodology/services/experts_service.py`, ledger models, `tests/support/experts_data.py`, `tests/support/experts_html.py`.

If certification reveals a resolver defect, amend S03’s existing method within the agreed shared footprint; do not add a competing method. Structural interface names must be normalized to S03’s final declaration before materialization.



Activity paths above are logical BPE bundle identifiers for parent normalization to its verified current Edda root; the replay’s advertised `.windsurf/.../BPE/` directory is absent.

Complete new skeleton text follows. Every body remains unimplemented. Existing S03 working methods are not replaced.

**CREATE `tests/support/experts_category_ties.py`**
```python
from __future__ import annotations
from dataclasses import dataclass
from typing import Literal
from django.contrib.auth.models import User
from methodology.models import Playbook
from tests.support.experts_data import CedarDataset

TieVariant = Literal["TIE01", "TIE02"]

@dataclass(frozen=True)
class CategoryTieDataset:
    baseline: CedarDataset
    variant: TieVariant
    user: User
    playbook_ids: tuple[int, ...]

def load_category_tie(variant: str) -> CategoryTieDataset:
    """Extend a fresh real Cedar baseline with one isolated variant.
    :param variant: TIE01 or TIE02; example: "TIE01".
    :return: Real ORM fixture references; example: arao plus one Development release.
    :raises ValueError: Unknown variant, before database writes.
    """
    # Validate; reuse S03 loader; construct historical rows without event hooks.
    raise NotImplementedError()

def _create_tie_playbook(user: User, category: str, ordinal: int) -> Playbook:
    """Create one authored released playbook and truthful history directly.
    :param user: Persisted variant author.
    :param category: Canonical category; example: "development".
    :param ordinal: Positive sequence for collision-free fictional names.
    :return: Released ORM playbook with one initial version.
    :raises ValueError: Invalid category, user or ordinal.
    """
    raise NotImplementedError()

def _create_tie_awards(user: User, variant: TieVariant) -> None:
    """Persist two stable historical category awards using S03 ledger schema.
    :param user: Persisted recipient.
    :param variant: Identity namespace; example: "TIE02".
    :return: None; two 5,000-point snapshots, total 10,000.
    :raises ValueError: Invalid persisted recipient or variant.
    """
    # Historical channel, explicit source, stable identities; no fabricated PIP.
    raise NotImplementedError()
```

**CREATE `tests/integration/test_experts_category_ties.py`**
```python
from __future__ import annotations
import pytest
from pytest import LogCaptureFixture

@pytest.mark.django_db
@pytest.mark.parametrize("variant,expected", [("TIE01", "development"), ("TIE02", "design")])
def test_primary_category_with_cedar_tie_expected_category(variant: str, expected: str) -> None:
    """Prove fixture arithmetic, canonical result and unchanged ledger.
    :param variant: Isolated real ORM variant.
    :param expected: Required canonical category.
    :return: None.
    :raises AssertionError: Wrong totals, counts, result or ledger mutation.
    """
    raise NotImplementedError()

@pytest.mark.django_db
@pytest.mark.parametrize("case", [
    "points_first", "private_released_counts", "nonreleased_excluded",
    "other_author_excluded", "versions_count_once", "nontied_count_excluded",
    "alphabetical_insertion_independent", "historical_category_preserved",
])
def test_primary_category_with_policy_boundaries_expected_category(case: str) -> None:
    """Exercise one governing boundary using real persisted records.
    :param case: Named policy boundary.
    :return: None.
    :raises AssertionError: Resolver violates the documented boundary.
    """
    raise NotImplementedError()

@pytest.mark.django_db
def test_category_tie_loader_with_unknown_variant_rejects() -> None:
    """Reject TIE99 before writes.
    :return: None.
    :raises AssertionError: Missing ValueError or changed baseline/ledger.
    """
    raise NotImplementedError()

@pytest.mark.django_db
def test_primary_category_with_cedar_ties_log_story_happy(caplog: LogCaptureFixture) -> None:
    """Assert both tie branches through S03 resolver and shared log helper.
    :param caplog: Actual production log capture.
    :return: None.
    :raises AssertionError: Missing declared beat or sensitive log content.
    """
    raise NotImplementedError()
```

**CREATE `docs/features/steps/experts_category_steps.py`**
```python
from behave import given, when, then
from behave.runner import Context

@given("the isolated {variant} data")
def isolated_category_data(context: Context, variant: str) -> None:
    """Build real isolated variant, preserving shared baseline references.
    :param context: Transactional Behave context.
    :param variant: TIE01 or TIE02.
    :return: None.
    :raises ValueError: Unknown variant.
    """
    raise NotImplementedError()

@when("the user's primary playbook category is projected")
def project_primary_category(context: Context) -> None:
    """Call S03 canonical projection and capture before/after ledger.
    :param context: Context containing CategoryTieDataset.
    :return: None.
    :raises RuntimeError: Variant was not prepared.
    """
    raise NotImplementedError()

@then("the result is {category}")
def category_result(context: Context, category: str) -> None:
    """Assert actual canonical result, 10,000 total and unchanged awards.
    :param context: Context containing actual projection.
    :param category: Expected display category; example: "Design".
    :return: None.
    :raises AssertionError: Category, arithmetic or snapshot differs.
    """
    raise NotImplementedError()
```

**CREATE `tests/integration/test_experts_category_acceptance.py`**
```python
from pathlib import Path

def test_karma_category_acceptance_with_exact_outline_two_examples(tmp_path: Path) -> None:
    """Run isolated acceptance subprocess and inspect its JSON execution report.
    :param tmp_path: Temporary report directory.
    :return: None; exactly two selected examples passed.
    :raises AssertionError: Bad exit, missing examples, selected skips or undefined steps.
    """
    raise NotImplementedError()
```

**CREATE `tests/e2e/test_experts_category_ties.py`**
```python
import pytest
from playwright.sync_api import Page

@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("variant,category", [("TIE01", "Development"), ("TIE02", "Design")])
def test_primary_category_with_cedar_tie_renders_correct_tab(
    page: Page, live_server_url: str, variant: str, category: str,
) -> None:
    """Verify actual production list placement and badge for the ORM variant.
    :param page: Existing function-scoped real browser fixture.
    :param live_server_url: Existing isolated live-server URL.
    :param variant: Fresh TIE01 or TIE02 dataset.
    :param category: Required displayed primary category.
    :return: None.
    :raises AssertionError: Wrong placement, badge, total or mutated ledger.
    """
    raise NotImplementedError()
```

## Parent convergence

Authoritative acceptance source: `docs/features/act-18-experts/karma-accrual.feature:141`; 2 expanded case(s), primary layer `at`. Dependencies: S03. The full scenario includes all composed journey/UAT obligations assigned in the consolidated contract. Shared Make/catalog registration belongs only to S03.

## Canonical feature execution graph

```yaml
feature_execution_graph:
  feature_ref: KARMA-CATEGORY-01
  scenario_id: S47
  dependencies:
  - S03
  nodes:
  - id: S47-backend
    title: Real ORM tie variants and canonical projection proofs
    bpe: BPE-02
    depends_on: []
    footprint:
    - tests/integration/test_experts_category_ties.py
    - tests/support/experts_category_ties.py
    tests:
    - test_primary_category_with_cedar_tie_expected_category
    - test_primary_category_with_policy_boundaries_expected_category
    - test_category_tie_loader_with_unknown_variant_rejects
    - test_primary_category_with_cedar_ties_log_story_happy
    gate:
      command: pytest tests/integration/test_experts_category_ties.py -x
      log_story_command: pytest tests/integration/test_experts_category_ties.py -k log_story -x
    guidance_bundle:
      activity: BPE/BPE-02-Implement_Backend.md
      rules:
      - do-skeletons-first
      - do-test-first
      - do-not-mock-in-integration-tests
      - do-assert-log-story
      - pytest
  - id: S47-at
    title: Execute both exact living-spec examples
    bpe: BPE-04
    depends_on:
    - S47-backend
    footprint:
    - docs/features/steps/experts_category_steps.py
    - tests/integration/test_experts_category_acceptance.py
    tests:
    - test_karma_category_acceptance_with_exact_outline_two_examples
    gate:
      command: make test-experts-s47-at
      expected_selected_examples: 2
      selected_skips_allowed: 0
    guidance_bundle:
      activity: BPE/BPE-04-Implement_Feature_Acceptance_Tests.md
      rules:
      - do-test-first
      - do-not-mock-in-integration-tests
      - pytest
  - id: S47-browser
    title: Show canonical category on the production list
    bpe: BPE-05
    depends_on:
    - S47-at
    footprint:
    - tests/e2e/test_experts_category_ties.py
    tests:
    - test_primary_category_with_cedar_tie_renders_correct_tab
    gate:
      command: make test-experts-s47-browser
      expected_cases: 2
    guidance_bundle:
      activity: BPE/BPE-05-Implement_Journey_Certification_Tests.md
      rules:
      - do-test-first
      - do-semantic-versioning-on-ui-elements
      - pytest
  - id: S47-dod
    title: Reconcile category policy and conjunctive evidence
    bpe: BPE-06
    depends_on:
    - S47-backend
    - S47-at
    - S47-browser
    footprint:
    - docs/architecture/SAO.md
    gate:
      command: make test-experts-s47
      required_passed_nodes:
      - S47-backend
      - S47-at
      - S47-browser
      zero_or_skipped_is_completion: false
    guidance_bundle:
      activity: BPE/BPE-06-Check_Definition_of_Done.md
      rules:
      - do-assert-log-story
      - do-small-increments
      - do-follow-commit-convention
      - pytest
  scenario_dependencies:
  - S03
```

## Lessons Learned

Prototype sorting consumes declared categories and cannot certify category derivation. Distinguish current released counts from public fallback counts and immutable award attribution. Keep the two category examples separate from TIE03/S08. Empty/WIP-filtered runs are structural evidence only.

After PIN-04 issue/handoff and PIN-05 GO: one backend-plus-log slice, one AT slice, one browser slice, then policy/DoD evidence; each commit references the issue and receives its required approved issue update. No writes, tests, commits or external mutations were performed by this worker.

## Structural application evidence

`docs/experts-replay/pin-evidence/S47.json` records positive scaffold selection and deliberate NotImplementedError. Existing callable ASTs were preserved. Browser collection is not interaction certification.
