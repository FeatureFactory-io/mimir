from __future__ import annotations

"""Exact S18 living-spec runner proof."""
from pathlib import Path


def test_s18_behave_contract_with_exact_name_executes_without_skips(
    tmp_path: Path,
) -> None:
    """Execute only EXPERTS-VIEW-02 against the isolated acceptance database.

    :param tmp_path: Report directory. Example: Path("/tmp/pytest/s18").
    :return: None. Example: None for one scenario and five passed steps.
    :raises AssertionError: If subprocess fails, selects zero or skips a step.
    """
    raise NotImplementedError()
