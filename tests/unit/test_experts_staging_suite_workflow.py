"""Require explicit, bounded full-suite CI with the measured immutable images."""

import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
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


def test_full_or_measured_with_browser_import_preflight_precedes_host_execution() -> (
    None
):
    job = _workflow()["jobs"]["experts-staging"]
    names = [step.get("name", "") for step in job["steps"]]
    name = "Verify immutable browser imports before any host execution"
    step = next(step for step in job["steps"] if step.get("name") == name)
    assert (
        step["if"]
        == "inputs.experts_suite == 'full' || inputs.experts_resource_profile == 'aggregate960'"
    )
    assert names.index(
        "Record actual immutable image sizes before any host pull"
    ) < names.index(name)
    assert names.index(name) < next(
        i for i, value in enumerate(names) if value.startswith("Execute only owned")
    )
    assert "probe_browser_imports.py" in step["run"]
    assert '--suite "$EXPERTS_SUITE"' in step["run"]


@pytest.fixture
def probe(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    runtime = _PATH.parents[2] / "scripts/experts-staging"
    monkeypatch.syspath_prepend(str(runtime))
    spec = importlib.util.spec_from_file_location(
        "ci_browser_probe", runtime / "probe_browser_imports.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_import_probe_with_actual_browser_vector_preserves_env_and_script_semantics(
    probe: ModuleType, tmp_path: Path
) -> None:
    manifest = {
        "nonce": "c" * 32,
        "browser_image": _BROWSER,
        "suite_phase": "nomination",
        "saga_case": "nomination",
    }
    actual = probe.remote.browser_arguments(
        tmp_path, manifest, probe.remote.resource_names(manifest["nonce"])
    )
    command = probe.probe_arguments(tmp_path, actual)
    env = [actual[i + 1] for i, value in enumerate(actual) if value == "-e"]
    assert [command[i + 1] for i, value in enumerate(command) if value == "-e"] == env
    assert command[command.index("--network") + 1] == "none"
    assert (
        "--read-only" in command
        and "--cap-drop" in command
        and "--pull=never" in command
    )
    assert (
        command.count("--mount") == 1
        and "readonly" in command[command.index("--mount") + 1]
    )
    code = command[-1]
    assert 'sys.path[0] = "/runtime"' in code
    assert "sys.path.insert" not in code and "sys.path.append" not in code
    assert "django.setup" not in code and "run_module" not in code
    assert "resource_observer" in code and "suite_browser" in code


def test_import_probe_with_unknown_credentials_or_entrypoint_rejects(
    probe: ModuleType, tmp_path: Path
) -> None:
    with pytest.raises(ValueError):
        probe.probe_arguments(
            tmp_path,
            [
                "--entrypoint",
                "python",
                "-e",
                "AWS_SECRET_ACCESS_KEY=PRIVATE",
                _BROWSER,
                "/runtime/resource_observer.py",
            ],
        )
    with pytest.raises(ValueError):
        probe.probe_arguments(
            tmp_path, ["--entrypoint", "python", _BROWSER, "/runtime/unknown.py"]
        )


def test_unpack_probe_with_real_committed_bundle_admits_only_shipped_bytes(
    probe: ModuleType, tmp_path: Path
) -> None:
    repository = _PATH.parents[2]
    source = probe.controller.source_manifest(
        repository, "04c9432bce7eac5ec34a090bc5e8ec4fa06f409d"
    )
    (tmp_path / "source.json").write_text(json.dumps(source))
    manifest = {
        "nonce": "c" * 32,
        "browser_image": _BROWSER,
        "resource_profile": "default",
        "source_revision": source["source_revision"],
    }
    bundle, digest = probe.controller.make_bundle(tmp_path, manifest)
    target = tmp_path / "runtime"
    probe.unpack_bundle(bundle, digest, target, manifest)
    assert {path.name for path in target.iterdir()} == set(
        probe.controller.bundle_members(manifest)
    )
    for name, expected in manifest["control_files"].items():
        assert hashlib.sha256((target / name).read_bytes()).hexdigest() == expected
    assert not (target / "tests").exists()


def test_import_probe_with_old_missing_candidate_environment_rejects(
    probe: ModuleType, tmp_path: Path
) -> None:
    actual = probe.remote.browser_arguments(
        tmp_path,
        {
            "nonce": "c" * 32,
            "browser_image": _BROWSER,
            "suite_phase": "nomination",
            "saga_case": "nomination",
        },
        probe.remote.resource_names("c" * 32),
    )
    index = actual.index("PYTHONPATH=/runtime:/app")
    del actual[index - 1 : index + 1]
    with pytest.raises(ValueError):
        probe.probe_arguments(tmp_path, actual)


def test_import_protocol_with_known_failure_retains_closed_phase_not_message(
    probe: ModuleType,
) -> None:
    record = {
        "status": "failed",
        "phase": "import_suite_browser",
        "classification": "missing_candidate_tests",
    }
    result = subprocess.CompletedProcess(
        [], 1, json.dumps(record).encode(), b"PRIVATE_CANARY"
    )
    assert probe.probe_result(result) == record
    for changes in (
        {"message": "PRIVATE_CANARY"},
        {"phase": "PRIVATE_CANARY"},
        {"classification": "PRIVATE_CANARY"},
    ):
        invalid = {**record, **changes}
        result = subprocess.CompletedProcess([], 1, json.dumps(invalid).encode(), b"")
        with pytest.raises(ValueError):
            probe.probe_result(result)
    assert "settings.configured" in probe._PROBE


def test_import_probe_with_timeout_only_cleans_exact_owned_container(
    probe: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = []

    def run(command, **kwargs):
        calls.append((command, kwargs))
        if command[:2] == ["docker", "run"]:
            raise subprocess.TimeoutExpired(command, 90, output=b"PRIVATE_CANARY")
        if command[:3] == ["docker", "container", "inspect"]:
            identity = calls[0][0][calls[0][0].index("--label") + 1].split("=", 1)[1]
            return subprocess.CompletedProcess(
                command,
                0,
                json.dumps({"mimir.ci.browser-import": identity}).encode(),
                b"",
            )
        return subprocess.CompletedProcess(command, 0, b"", b"")

    monkeypatch.setattr(probe.subprocess, "run", run)
    actual = probe.remote.browser_arguments(
        tmp_path,
        {
            "nonce": "c" * 32,
            "browser_image": _BROWSER,
            "suite_phase": "nomination",
            "saga_case": "nomination",
        },
        probe.remote.resource_names("c" * 32),
    )
    assert probe.run_probe(tmp_path, actual) == {
        "status": "failed",
        "phase": "container_execution",
        "classification": "timeout",
    }
    command = calls[0][0]
    name = command[command.index("--name") + 1]
    assert name.startswith("experts-ci-import-")
    assert calls[-1][0] == ["docker", "rm", "--force", name]
    assert all(
        options["timeout"] <= 90 and options["capture_output"] for _, options in calls
    )


def test_probe_preparation_with_real_source_preserves_parent_bundle(
    probe: ModuleType, tmp_path: Path
) -> None:
    source = probe.controller.source_manifest(
        _PATH.parents[2], "04c9432bce7eac5ec34a090bc5e8ec4fa06f409d"
    )
    (tmp_path / "source.json").write_text(json.dumps(source))
    (tmp_path / "runtime-bundle.tar.gz").write_bytes(b"PRESERVE_PARENT_BUNDLE")
    manifest = {
        "nonce": "c" * 32,
        "browser_image": _BROWSER,
        "resource_profile": "default",
        "source_revision": source["source_revision"],
    }
    destination, bundle, digest = probe.prepare_bundle(tmp_path, manifest)
    assert destination == tmp_path / "ci-browser-import-probe"
    assert (
        bundle.parent == destination
        and hashlib.sha256(bundle.read_bytes()).hexdigest() == digest
    )
    assert json.loads((destination / "manifest.json").read_text()) == manifest
    assert (
        tmp_path / "runtime-bundle.tar.gz"
    ).read_bytes() == b"PRESERVE_PARENT_BUNDLE"
    with pytest.raises(FileExistsError):
        probe.prepare_bundle(tmp_path, manifest)


def test_probe_child_with_missing_runtime_emits_only_closed_facts(
    probe: ModuleType, tmp_path: Path
) -> None:
    result = subprocess.run(
        [sys.executable, "-I", "-c", probe._PROBE],
        cwd=tmp_path,
        capture_output=True,
        timeout=10,
        check=False,
    )
    assert probe.probe_result(result) == {
        "status": "failed",
        "phase": "runtime_contract",
        "classification": "missing_module",
    }
    assert not result.stderr
    assert b"Traceback" not in result.stdout and b"No module named" not in result.stdout


def test_cleanup_probe_with_wrong_owner_never_removes_container(
    probe: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = []

    def run(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(
            command, 0, b'{"mimir.ci.browser-import":"OTHER_OWNER"}', b""
        )

    monkeypatch.setattr(probe.subprocess, "run", run)
    with pytest.raises(ValueError):
        probe.cleanup_probe("c" * 32)
    assert len(calls) == 1 and calls[0][:3] == ["docker", "container", "inspect"]
