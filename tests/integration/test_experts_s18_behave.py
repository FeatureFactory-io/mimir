"""Exact S18 living-spec runner proof."""

from __future__ import annotations

import re
from pathlib import Path

from tests.support.experts_acceptance import (
    _run_behave,
    _validate_acceptance_selection,
)

_FEATURE = Path("docs/features/act-18-experts/experts-view.feature")
_ACCEPTANCE_ID = "EXPERTS-VIEW-02"
_SCENARIO_NAME = f"{_ACCEPTANCE_ID} Reconcile the public score-source breakdown"


def test_s18_behave_contract_with_exact_name_executes_without_skips(
    tmp_path: Path,
) -> None:
    """Execute only EXPERTS-VIEW-02 against the isolated acceptance database.

    :param tmp_path: Report directory. Example: Path("/tmp/pytest/s18").
    :return: None. Example: None for one scenario and five passed steps.
    :raises AssertionError: If subprocess fails, selects zero or skips a step.
    """
    payload = _run_behave(
        (_FEATURE,), f"^{re.escape(_SCENARIO_NAME)}$", tmp_path / "s18-behave.json"
    )
    result = _validate_acceptance_selection(payload, _ACCEPTANCE_ID, 1)
    assert result.scenario_count == 1
    assert result.step_count == 5
    assert result.skipped_count == result.undefined_count == 0
    feature = result.output["features"][0]
    assert feature["location"].rpartition(":")[0] == _FEATURE.as_posix()
    selected = [
        element
        for element in feature["elements"]
        if element.get("type") == "scenario" and element.get("status") != "skipped"
    ]
    assert len(selected) == 1
    assert selected[0]["name"] == _SCENARIO_NAME
    assert selected[0]["location"] == f"{_FEATURE.as_posix()}:16"
    assert selected[0]["steps"][0]["name"] == "the CEDAR-RFP-01 baseline dataset"
