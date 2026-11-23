"""Run and verify one exact living specification with the real Django client."""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory

logger = logging.getLogger(__name__)
_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
_FEATURE_ROOT = _REPOSITORY_ROOT / "docs" / "features"
_ACCEPTANCE_ID = re.compile(r"[A-Z]+(?:-[A-Z0-9]+)*-[0-9]+")
_RUN_TIMEOUT_SECONDS = 120


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
    feature = _local_feature_path(feature_path)
    pattern = _selection_pattern(acceptance_id)
    if type(expected_cases) is not int or expected_cases < 1:
        raise ValueError("Expected acceptance cases must be a positive integer.")

    logger.info(
        "Experts AT | entry | contract=%s cases=%s", acceptance_id, expected_cases
    )
    with TemporaryDirectory(prefix="mimir-experts-acceptance-") as report_dir:
        payload = _run_behave(feature, pattern, Path(report_dir) / "results.json")
    result = _validate_acceptance_selection(payload, acceptance_id, expected_cases)
    logger.info(
        "Experts AT | exit | contract=%s passed=%s steps=%s",
        acceptance_id,
        result.scenario_count,
        result.step_count,
    )
    return result


def _local_feature_path(feature_path: Path) -> Path:
    """Resolve to a repo-relative spec within the acceptance feature directory."""
    if not isinstance(feature_path, Path):
        raise ValueError("Acceptance requires a feature Path.")  # noqa: TRY004
    try:
        local_path = (_REPOSITORY_ROOT / feature_path).resolve(strict=True)
    except (OSError, RuntimeError, ValueError) as error:
        raise ValueError(
            f"Acceptance feature does not resolve: {feature_path}"
        ) from error
    if (
        not local_path.is_relative_to(_FEATURE_ROOT)
        or local_path.suffix != ".feature"
        or not local_path.is_file()
    ):
        raise ValueError(
            "Acceptance feature must be a local docs/features .feature file."
        )
    return local_path.relative_to(_REPOSITORY_ROOT)


def _selection_pattern(acceptance_id: str) -> str:
    """Select an ID token at the start of a scenario or expanded outline name."""
    if not isinstance(acceptance_id, str) or not _ACCEPTANCE_ID.fullmatch(
        acceptance_id
    ):
        raise ValueError("An exact acceptance ID is required, such as EXPERTS-LIST-03.")
    return rf"^{acceptance_id}(?=\s|$)"


def _run_behave(feature_path: Path, pattern: str, report_path: Path) -> object:
    """Execute Behave against its own database and read the formatter output."""
    command = [
        sys.executable,
        "manage.py",
        "behave",
        "--simple",
        # An exact name can opt into WIP without enabling any neighboring scenario.
        "--tags=@wip or not @wip",
        f"--name={pattern}",
        "--format=json",
        f"--outfile={report_path}",
        str(feature_path),
    ]
    env = dict(
        os.environ,
        DATABASE_URL="",
        DJANGO_SETTINGS_MODULE="mimir.settings.acceptance",
        MIMIR_ENV="test",
    )
    try:
        completed = subprocess.run(
            command,
            cwd=_REPOSITORY_ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=_RUN_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise AssertionError(
            f"Unable to execute Behave for {pattern}: {error}"
        ) from error
    assert completed.returncode == 0, (
        f"Behave exited {completed.returncode} for {pattern}.\n"
        f"{completed.stdout}\n{completed.stderr}"
    )
    try:
        return json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise AssertionError(
            f"Behave did not produce a readable JSON report for {pattern}."
        ) from error


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
    assert (
        isinstance(payload, list) and len(payload) == 1
    ), "Expected one Behave feature report."
    feature = payload[0]
    assert isinstance(feature, dict), "Malformed Behave feature report."
    scenarios = _selected_scenarios(feature, _selection_pattern(acceptance_id))
    assert (
        scenarios and len(scenarios) == expected_cases
    ), f"{acceptance_id}: expected {expected_cases} selected cases, got {len(scenarios)}."
    step_count = sum(_passed_step_count(case) for case in scenarios.values())
    return AcceptanceResult(len(scenarios), step_count, 0, 0, {"features": payload})


def _selected_scenarios(
    feature: Mapping[str, object], pattern: str
) -> dict[str, Mapping[str, object]]:
    """Find exact-name cases and reject duplicate or accidentally executed neighbors."""
    elements = feature.get("elements")
    assert isinstance(elements, list), "Missing Behave feature elements."
    selected = {}
    for element in elements:
        assert isinstance(element, dict), "Malformed Behave feature element."
        if element.get("type") != "scenario":
            continue
        name = element.get("name")
        assert isinstance(name, str) and name, "Behave scenario has no name."
        if not re.match(pattern, name):
            assert (
                element.get("status") == "skipped"
            ), f"Unexpected executed scenario: {name}"
            continue
        assert name not in selected, f"Duplicate selected scenario: {name}"
        selected[name] = element
    return selected


def _passed_step_count(case: Mapping[str, object]) -> int:
    """Require a passing case with a positive number of passing steps."""
    name = case["name"]
    assert (
        case.get("status") == "passed"
    ), f"{name}: scenario status {case.get('status')!r}"
    steps = case.get("steps")
    assert isinstance(steps, list) and steps, f"{name}: no executed steps."
    for step in steps:
        assert isinstance(step, dict), f"{name}: malformed step."
        result = step.get("result")
        assert (
            isinstance(result, dict) and result.get("status") == "passed"
        ), f"{name}: step {step.get('name')!r} did not pass: {result!r}"
    return len(steps)
