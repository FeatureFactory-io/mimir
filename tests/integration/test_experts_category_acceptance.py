from __future__ import annotations

from pathlib import Path


def test_karma_category_acceptance_with_exact_outline_two_examples(
    tmp_path: Path,
) -> None:
    """Run isolated acceptance subprocess and inspect its JSON execution report.
    :param tmp_path: Temporary report directory.
    :return: None; exactly two selected examples passed.
    :raises AssertionError: Bad exit, missing examples, selected skips or undefined steps.
    """
    raise NotImplementedError()
