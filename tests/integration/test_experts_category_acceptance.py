from __future__ import annotations

from pathlib import Path

from tests.support.experts_acceptance import run_exact_acceptance

_FEATURE = Path("docs/features/act-18-experts/karma-accrual.feature")
_ACCEPTANCE_ID = "KARMA-CATEGORY-01"
_EXAMPLES = (("TIE01", "Development"), ("TIE02", "Design"))
_STEPS_PER_EXAMPLE = 4


def test_karma_category_acceptance_with_exact_outline_two_examples() -> None:
    """Require both actual tie examples and every declared step to pass.

    :return: None. Example: two selected cases with four passing steps each.
    :raises AssertionError: For incomplete execution or a different outline case.
    """
    result = run_exact_acceptance(_FEATURE, _ACCEPTANCE_ID, len(_EXAMPLES))

    assert result.scenario_count == len(_EXAMPLES)
    assert result.step_count == len(_EXAMPLES) * _STEPS_PER_EXAMPLE
    assert result.skipped_count == result.undefined_count == 0
    features = result.output["features"]
    assert isinstance(features, list) and len(features) == 1
    executed_steps = [
        tuple(step["name"] for step in case["steps"])
        for case in features[0]["elements"]
        if case["type"] == "scenario" and case["status"] == "passed"
    ]
    assert executed_steps == [
        (
            "the CEDAR-RFP-01 baseline dataset",
            f"the isolated {variant} data",
            "the user's primary playbook category is projected",
            f"the result is {category}",
        )
        for variant, category in _EXAMPLES
    ]
