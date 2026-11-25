"""Safety boundary for the disposable benchmark workflow variant."""

from pathlib import Path
from typing import Any

import yaml

_WORKFLOW = (
    Path(__file__).resolve().parents[2] / ".github/workflows/build-and-deploy.yml"
)
_NORMAL_ONLY = (
    "test_workflow_with_normal_defaults_has_no_implicit_companion_dispatch",
    "test_workflow_with_untrusted_selectors_uses_environment_and_guards_before_aws",
)
_IMAGES = (
    "411113550285.dkr.ecr.us-east-1.amazonaws.com/mimir@sha256:e7f6e2170fd6250a9b6c3f635ceb2b90d0dfbe81ed337c10180c0a903ca5e1ba",
    "411113550285.dkr.ecr.us-east-1.amazonaws.com/mimir@sha256:a74104c8fb4ff8a02dd053ee2584868d91dd4273f058b690faf0875684c5e368",
    "postgres@sha256:07abc3f43c9395b0bdbbab36bc25ddb0e8d83cd4fcafb5fb7d6abe14ff156dd8",
)


def _workflow() -> dict[str, Any]:
    """Read this branch's real workflow without changing its YAML semantics.

    :return: Actual workflow mapping, including the literal on key.
    :raises OSError: The exact workflow cannot be read.
    """
    return yaml.load(_WORKFLOW.read_text(), Loader=yaml.BaseLoader)


def test_benchmark_validation_with_diagnostic_workflow_selects_applicable_guards() -> (
    None
):
    """Require replacement workflow checks while retaining runtime guard coverage.

    :return: None after the diagnostic branch selects its applicable contracts.
    :raises AssertionError: Runtime guards disappear or workflow checks are omitted.
    """
    steps = _workflow()["jobs"]["benchmark"]["steps"]
    gate = next(
        step["run"] for step in steps if step.get("name", "").startswith("Validate")
    )
    for name in ("runner_contract", "runner_config", "benchmark", "benchmark_workflow"):
        assert f"test_experts_staging_{name}.py" in gate
    assert "-k" in gate and all("not " + name in gate for name in _NORMAL_ONLY)


def test_benchmark_images_with_fixed_candidate_pull_only_reviewed_digests() -> None:
    """Bind the workload to the three already-built immutable images.

    :return: None after exactly the reviewed images are pulled.
    :raises AssertionError: A tag, arbitrary input or image mutation enters the job.
    """
    commands = "\n".join(
        step.get("run", "") for step in _workflow()["jobs"]["benchmark"]["steps"]
    )
    images = tuple(
        line.strip().split()[2]
        for line in commands.splitlines()
        if line.strip().startswith("docker pull ")
    )
    assert images == _IMAGES
    assert "docker build" not in commands and "docker push" not in commands


def test_benchmark_permissions_with_registry_access_exclude_deployment_actions() -> (
    None
):
    """Keep registry connection separate from deployment authority in the job.

    :return: None after permissions and action capabilities match the review.
    :raises AssertionError: An added action or job permission broadens the work.
    """
    workflow = _workflow()
    expected = {"contents": "read", "actions": "read"}
    assert workflow["permissions"] == expected
    job = workflow["jobs"]["benchmark"]
    assert job.get("permissions", expected) == expected
    uses = {step["uses"] for step in job["steps"] if "uses" in step}
    assert uses == {
        "actions/checkout@v4",
        "actions/setup-python@v5",
        "actions/download-artifact@v4",
        "actions/upload-artifact@v4",
        "aws-actions/configure-aws-credentials@v4",
        "aws-actions/amazon-ecr-login@v2",
    }


def test_benchmark_proof_with_fixed_build_receipt_binds_candidate_source() -> None:
    """Require the actual successful candidate build before workload execution.

    :return: None after fixed source, build and receipt identities agree.
    :raises AssertionError: Candidate identity can be redirected by a caller.
    """
    workflow = _workflow()
    assert set(workflow["on"]["workflow_dispatch"]["inputs"]) == {
        "web_memory_mib",
        "browser_memory_mib",
    }
    job = workflow["jobs"]["benchmark"]
    assert job["env"]["CANDIDATE_SHA"] == "04c9432bce7eac5ec34a090bc5e8ec4fa06f409d"
    assert job["env"]["CANDIDATE_RUN_ID"] == "45516980492"
    receipt = next(
        step["with"]
        for step in job["steps"]
        if step.get("uses") == "actions/download-artifact@v4"
    )
    assert receipt["run-id"] == "45516980492"
    assert receipt["name"] == "candidate-image-identities-45516980492"
    prepare = next(
        step["run"]
        for step in job["steps"]
        if step.get("name") == "Verify build identity and exact candidate source"
    )
    assert '--revision "$CANDIDATE_SHA"' in prepare
    assert '--run-id "$CANDIDATE_RUN_ID"' in prepare


def test_benchmark_browser_experiment_with_dispatch_requires_closed_credential_free_choice() -> (
    None
):
    """Require a closed CI-only browser experiment without expanding deployment.

    :return: None after choice, shell admission and clean process arguments agree.
    :raises AssertionError: Arbitrary memory or inherited credentials can enter.
    """
    workflow = _workflow()
    option = workflow["on"]["workflow_dispatch"]["inputs"]["browser_memory_mib"]
    assert option["default"] == "512"
    assert option["options"] == ["512", "768"]
    step = next(
        s
        for s in workflow["jobs"]["benchmark"]["steps"]
        if s.get("name")
        == "Run the genuine owned workload without the job credential environment"
    )
    assert (
        step["env"]["EXPERIMENT_BROWSER_MEMORY_MIB"]
        == "${{ inputs.browser_memory_mib }}"
    )
    command = step["run"]
    assert 'case "$EXPERIMENT_BROWSER_MEMORY_MIB" in 512|768)' in command
    assert '--browser-memory-mib "$EXPERIMENT_BROWSER_MEMORY_MIB"' in command
    assert "sudo /usr/bin/env -i /usr/bin/python3" in command
    assert "${{" not in command
