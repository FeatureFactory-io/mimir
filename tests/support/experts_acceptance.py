"""Exact living-spec runner contract; implemented only after PIN-05 GO."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from collections.abc import Mapping


@dataclass(frozen=True)
class AcceptanceResult:
    scenario_count: int
    step_count: int
    skipped_count: int
    undefined_count: int
    output: Mapping[str, object]


def run_exact_acceptance(
    feature_path: Path, acceptance_id: str, expected_cases: int
) -> AcceptanceResult:
    """Run the real scoped Behave command and inspect its actual JSON result.

    :param feature_path: Authoritative living-spec path. Example: experts-list.feature.
    :param acceptance_id: Exact selected ID. Example: EXPERTS-LIST-03.
    :param expected_cases: Expanded examples required. Example: 2.
    :return: Validated actual result with no skips or undefined steps.
    :raises AssertionError: Failed command, wrong selection, skip or undefined step.
    :raises ValueError: Invalid path, ID or count.
    """
    raise NotImplementedError()


def _validate_acceptance_selection(
    payload: object, acceptance_id: str, expected_cases: int
) -> AcceptanceResult:
    """Check real JSON scenario and step results, rejecting empty selections.

    :param payload: Parsed actual Behave JSON. Example: feature results.
    :param acceptance_id: Selected ID. Example: KARMA-MCP-01.
    :param expected_cases: Required examples. Example: 9.
    :return: Positive passed evidence. Example: nine passed scenarios.
    :raises AssertionError: Missing, failed, skipped, undefined or duplicate selected cases.
    """
    raise NotImplementedError()
