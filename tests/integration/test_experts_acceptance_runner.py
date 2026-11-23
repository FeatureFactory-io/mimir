"""One real living-spec runner, with all 43 exact server contracts."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.support.experts_acceptance import (
    _validate_acceptance_selection,
    run_exact_acceptance,
)

_RANKING_FEATURE = Path("docs/features/act-18-experts/experts-list.feature")
_RANKING_ID = "EXPERTS-LIST-03"
_PASSING_CASE = {
    "type": "scenario",
    "name": f"{_RANKING_ID} Ranks contributors",
    "status": "passed",
    "steps": [{"result": {"status": "passed"}}],
}


@pytest.mark.parametrize(
    "scenario,feature_path,acceptance_id,expected_cases",
    [
        (
            "S01",
            "docs/features/act-18-experts/experts-list.feature",
            "EXPERTS-LIST-01",
            1,
        ),
        (
            "S02",
            "docs/features/act-18-experts/experts-list.feature",
            "EXPERTS-LIST-02",
            1,
        ),
        (
            "S03",
            "docs/features/act-18-experts/experts-list.feature",
            "EXPERTS-LIST-03",
            1,
        ),
        (
            "S04",
            "docs/features/act-18-experts/experts-list.feature",
            "EXPERTS-LIST-04",
            1,
        ),
        (
            "S05",
            "docs/features/act-18-experts/experts-list.feature",
            "EXPERTS-LIST-05",
            1,
        ),
        (
            "S06",
            "docs/features/act-18-experts/experts-list.feature",
            "EXPERTS-LIST-06",
            1,
        ),
        (
            "S07",
            "docs/features/act-18-experts/experts-list.feature",
            "EXPERTS-LIST-07",
            1,
        ),
        (
            "S08",
            "docs/features/act-18-experts/experts-list.feature",
            "EXPERTS-LIST-08",
            1,
        ),
        (
            "S09",
            "docs/features/act-18-experts/experts-list.feature",
            "EXPERTS-LIST-09",
            1,
        ),
        (
            "S10",
            "docs/features/act-18-experts/experts-profile.feature",
            "EXPERTS-PROFILE-01",
            1,
        ),
        (
            "S12",
            "docs/features/act-18-experts/experts-profile.feature",
            "EXPERTS-PROFILE-03",
            1,
        ),
        (
            "S13",
            "docs/features/act-18-experts/experts-profile.feature",
            "EXPERTS-PROFILE-04",
            1,
        ),
        (
            "S14",
            "docs/features/act-18-experts/experts-reach-out.feature",
            "EXPERTS-REACH-01",
            1,
        ),
        (
            "S16",
            "docs/features/act-18-experts/experts-reach-out.feature",
            "EXPERTS-REACH-03",
            1,
        ),
        (
            "S17",
            "docs/features/act-18-experts/experts-view.feature",
            "EXPERTS-VIEW-01",
            1,
        ),
        (
            "S18",
            "docs/features/act-18-experts/experts-view.feature",
            "EXPERTS-VIEW-02",
            1,
        ),
        (
            "S19",
            "docs/features/act-18-experts/experts-view.feature",
            "EXPERTS-VIEW-03",
            1,
        ),
        (
            "S20",
            "docs/features/act-18-experts/experts-view.feature",
            "EXPERTS-VIEW-04",
            1,
        ),
        (
            "S21",
            "docs/features/act-18-experts/experts-view.feature",
            "EXPERTS-VIEW-05",
            2,
        ),
        (
            "S22",
            "docs/features/act-18-experts/experts-view.feature",
            "EXPERTS-VIEW-06",
            1,
        ),
        (
            "S23",
            "docs/features/act-18-experts/galdr-contribution-summary.feature",
            "GALDR-SUMMARY-01",
            1,
        ),
        (
            "S25",
            "docs/features/act-18-experts/galdr-contribution-summary.feature",
            "GALDR-SUMMARY-03",
            1,
        ),
        (
            "S26",
            "docs/features/act-18-experts/galdr-contribution-summary.feature",
            "GALDR-SUMMARY-04",
            1,
        ),
        (
            "S27",
            "docs/features/act-18-experts/galdr-contribution-summary.feature",
            "GALDR-SUMMARY-05",
            1,
        ),
        (
            "S28",
            "docs/features/act-18-experts/galdr-contribution-summary.feature",
            "GALDR-SUMMARY-06",
            1,
        ),
        (
            "S29",
            "docs/features/act-18-experts/galdr-contribution-summary.feature",
            "GALDR-SUMMARY-07",
            1,
        ),
        (
            "S30",
            "docs/features/act-18-experts/karma-accrual.feature",
            "KARMA-RELEASE-01",
            1,
        ),
        (
            "S31",
            "docs/features/act-18-experts/karma-accrual.feature",
            "KARMA-RELEASE-02",
            1,
        ),
        (
            "S32",
            "docs/features/act-18-experts/karma-accrual.feature",
            "KARMA-PIP-01",
            3,
        ),
        (
            "S33",
            "docs/features/act-18-experts/karma-accrual.feature",
            "KARMA-PIP-02",
            20,
        ),
        (
            "S34",
            "docs/features/act-18-experts/karma-accrual.feature",
            "KARMA-PIP-03",
            1,
        ),
        (
            "S35",
            "docs/features/act-18-experts/karma-accrual.feature",
            "KARMA-PIP-04",
            1,
        ),
        (
            "S39",
            "docs/features/act-18-experts/karma-accrual.feature",
            "KARMA-MCP-01",
            9,
        ),
        (
            "S40",
            "docs/features/act-18-experts/karma-accrual.feature",
            "KARMA-MCP-03",
            10,
        ),
        (
            "S41",
            "docs/features/act-18-experts/karma-accrual.feature",
            "KARMA-MCP-02",
            1,
        ),
        (
            "S42",
            "docs/features/act-18-experts/karma-accrual.feature",
            "KARMA-EXPORT-01",
            1,
        ),
        (
            "S43",
            "docs/features/act-18-experts/karma-accrual.feature",
            "KARMA-EXPORT-02",
            1,
        ),
        (
            "S44",
            "docs/features/act-18-experts/karma-accrual.feature",
            "KARMA-EXPORT-03",
            1,
        ),
        (
            "S45",
            "docs/features/act-18-experts/karma-accrual.feature",
            "KARMA-EVENT-01",
            1,
        ),
        (
            "S46",
            "docs/features/act-18-experts/karma-accrual.feature",
            "KARMA-EVENT-02",
            1,
        ),
        (
            "S47",
            "docs/features/act-18-experts/karma-accrual.feature",
            "KARMA-CATEGORY-01",
            2,
        ),
        (
            "S48",
            "docs/features/act-0-auth/experts-navigation.feature",
            "FOB-NAV-EXPERTS-01",
            1,
        ),
        (
            "S49",
            "docs/features/act-0-auth/experts-navigation.feature",
            "FOB-NAV-EXPERTS-02",
            1,
        ),
    ],
    ids=[
        "S01",
        "S02",
        "S03",
        "S04",
        "S05",
        "S06",
        "S07",
        "S08",
        "S09",
        "S10",
        "S12",
        "S13",
        "S14",
        "S16",
        "S17",
        "S18",
        "S19",
        "S20",
        "S21",
        "S22",
        "S23",
        "S25",
        "S26",
        "S27",
        "S28",
        "S29",
        "S30",
        "S31",
        "S32",
        "S33",
        "S34",
        "S35",
        "S39",
        "S40",
        "S41",
        "S42",
        "S43",
        "S44",
        "S45",
        "S46",
        "S47",
        "S48",
        "S49",
    ],
)
def test_exact_experts_acceptance_with_declared_contract_runs_all_examples(
    scenario: str, feature_path: str, acceptance_id: str, expected_cases: int
) -> None:
    """Require actual scoped Behave execution with the declared expanded case count.

    :param scenario: PIN scenario. Example: S39.
    :param feature_path: Sole authoritative source. Example: karma-accrual.feature.
    :param acceptance_id: Exact selected contract. Example: KARMA-MCP-01.
    :param expected_cases: Required examples. Example: 9.
    :return: None on actual complete acceptance. Example: None.
    :raises AssertionError: Any failed, skipped, undefined or absent selected case/step.
    """
    result = run_exact_acceptance(Path(feature_path), acceptance_id, expected_cases)

    assert result.scenario_count == expected_cases, scenario
    assert result.step_count >= expected_cases, scenario
    assert result.skipped_count == result.undefined_count == 0, scenario
    if acceptance_id == _RANKING_ID:
        assert result.step_count == 9, scenario


@pytest.mark.parametrize(
    "path,acceptance_id,count",
    [
        (Path("/tmp/experts-list.feature"), _RANKING_ID, 1),
        (Path("docs/features/absent.feature"), _RANKING_ID, 1),
        (Path("Makefile"), _RANKING_ID, 1),
        (_RANKING_FEATURE, "EXPERTS-LIST-03|.*", 1),
        (_RANKING_FEATURE, " EXPERTS-LIST-03", 1),
        (_RANKING_FEATURE, _RANKING_ID, 0),
        (_RANKING_FEATURE, _RANKING_ID, True),
    ],
    ids=["outside", "missing", "suffix", "regex", "whitespace", "zero", "boolean"],
)
def test_run_exact_acceptance_with_invalid_contract_rejects(
    path: Path, acceptance_id: str, count: int
) -> None:
    """Reject malformed arguments before attempting to execute Behave."""
    with pytest.raises(ValueError):
        run_exact_acceptance(path, acceptance_id, count)


def test_validate_acceptance_selection_with_outline_and_filtered_neighbors_counts_cases() -> (
    None
):
    """Accept unique passed outline cases and ignore name-filtered JSON entries."""
    elements = [
        {"type": "background", "steps": [{}]},
        {**_PASSING_CASE, "name": f"{_RANKING_ID} Ranks @1.1"},
        {**_PASSING_CASE, "name": f"{_RANKING_ID} Ranks @1.2"},
        {
            **_PASSING_CASE,
            "name": f"{_RANKING_ID}0 Different ID",
            "status": "skipped",
            "steps": [{}],
        },
    ]

    result = _validate_acceptance_selection([{"elements": elements}], _RANKING_ID, 2)

    assert result.scenario_count == result.step_count == 2
    assert result.skipped_count == result.undefined_count == 0


@pytest.mark.parametrize(
    "elements,count",
    [
        ([], 1),
        ([_PASSING_CASE], 2),
        ([_PASSING_CASE, _PASSING_CASE], 2),
        ([{**_PASSING_CASE, "status": "skipped"}], 1),
        ([{**_PASSING_CASE, "status": "failed"}], 1),
        ([{**_PASSING_CASE, "steps": []}], 1),
        ([{**_PASSING_CASE, "steps": [{}]}], 1),
        ([{**_PASSING_CASE, "steps": [{"result": {"status": "undefined"}}]}], 1),
        ([{**_PASSING_CASE, "steps": [{"result": {"status": "skipped"}}]}], 1),
        ([{**_PASSING_CASE, "name": f"{_RANKING_ID}0 Different ID"}], 1),
        ([_PASSING_CASE, {**_PASSING_CASE, "name": f"{_RANKING_ID}0 Different ID"}], 1),
    ],
    ids=[
        "empty",
        "wrong-count",
        "duplicate",
        "skipped-case",
        "failed-case",
        "empty-steps",
        "missing-step-result",
        "undefined-step",
        "skipped-step",
        "wrong-id",
        "unexpected-extra-case",
    ],
)
def test_validate_acceptance_selection_with_incomplete_execution_rejects(
    elements: list[dict[str, object]], count: int
) -> None:
    """Require positive passing results for every selected case and step."""
    with pytest.raises(AssertionError):
        _validate_acceptance_selection([{"elements": elements}], _RANKING_ID, count)
