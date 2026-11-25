"""Require explicit, bounded full-suite CI with the measured immutable images."""

from pathlib import Path
from typing import Any

import yaml

_PATH = Path(__file__).resolve().parents[2] / ".github/workflows/build-and-deploy.yml"
_BROWSER = "411113550285.dkr.ecr.us-east-1.amazonaws.com/mimir@sha256:a74104c8fb4ff8a02dd053ee2584868d91dd4273f058b690faf0875684c5e368"
_POSTGRES = (
    "postgres@sha256:07abc3f43c9395b0bdbbab36bc25ddb0e8d83cd4fcafb5fb7d6abe14ff156dd8"
)


def _workflow() -> dict[str, Any]:
    """Read actual branch workflow without credentials or execution.

    :return: Actual YAML including the literal on key.
    :raises OSError: Workflow bytes cannot be read.
    """
    return yaml.load(_PATH.read_text(), Loader=yaml.BaseLoader)


def test_full_suite_with_dispatch_requires_explicit_closed_selector() -> None:
    """Default smoke stays core and unknown suite inputs fail before AWS.

    :return: None after default, shell validation and argument agree.
    :raises AssertionError: Full suite is implicit or selector enters shell code.
    """
    workflow = _workflow()
    option = workflow["on"]["workflow_dispatch"]["inputs"]["experts_suite"]
    assert option["default"] == "core" and option["options"] == ["core", "full"]
    job = workflow["jobs"]["experts-staging"]
    assert job["env"]["EXPERTS_SUITE"] == "${{ inputs.experts_suite }}"
    assert 'case "$EXPERTS_SUITE" in core|full)' in job["steps"][0]["run"]
    run = next(
        s["run"]
        for s in job["steps"]
        if s.get("name", "").startswith("Execute only owned")
    )
    assert '--suite "$EXPERTS_SUITE"' in run and "${{" not in run


def test_full_suite_with_fixed_measured_images_cannot_rebuild_or_pull_tags() -> None:
    """Keep the actual measured browser and database digests through execution.

    :return: None after fixed digest inputs and no image build step.
    :raises AssertionError: Registry writes or mutable selectors enter this job.
    """
    job = _workflow()["jobs"]["experts-staging"]
    assert job["env"]["BROWSER_IMAGE"] == _BROWSER
    assert job["env"]["POSTGRES_IMAGE"] == _POSTGRES
    assert all(not s.get("uses", "").startswith("docker/") for s in job["steps"])
    commands = "\n".join(s.get("run", "") for s in job["steps"])
    assert 'docker pull "$BROWSER_IMAGE"' in commands
    assert 'docker pull "$POSTGRES_IMAGE"' in commands
    assert "postgres:16" not in commands and "docker push" not in commands


def test_full_suite_with_eleven_bounded_cases_has_time_and_contract_coverage() -> None:
    """Allow eleven real720s lifecycles plus transfer and cleanup without skipping.

    :return: None after bounded job time and all pure control checks are selected.
    :raises AssertionError: Insufficient deadline or absent suite/privacy guards.
    """
    job = _workflow()["jobs"]["experts-staging"]
    assert (
        job["timeout-minutes"] == "${{ inputs.experts_suite == 'full' && 180 || 45 }}"
    )
    gate = next(
        s["run"]
        for s in job["steps"]
        if s.get("name") == "Verify fail-closed runner contracts"
    )
    for name in (
        "suite",
        "suite_workflow",
        "saga_contract",
        "saga_trace",
        "saga_guest",
        "saga_visual",
        "saga_summary_contract",
    ):
        assert f"test_experts_staging_{name}.py" in gate
