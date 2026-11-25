"""Disposable Linux candidate measurement; no cloud operations or staging verdict."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
from pathlib import Path
from typing import Any
from uuid import uuid4

import aggregate
import contract
import remote
from benchmark_contract import (
    BUILD,
    IMAGES,
    RUNTIME_FILES,
    SOURCE,
    publish_owner,
    read_json,
    rejected_export_shapes,
    reviewed_bytes,
    safe_export,
    validate_cache,
    validate_prepared,
    validated_diagnostic_bytes,
)
from benchmark_metrics import (
    BROWSER_MEMORY_CHOICES,
    DEFAULT_BROWSER_MEMORY_MIB,
    browser_memory_bytes,
    failure_reason,
    host_observations,
    parse_browser_diagnostic,
    parse_memory,
    require_headroom,
)

_MIB = 1024 * 1024
_HOST_RESERVE_MIB = 256
_MEMORY_PROBE = "cat /sys/fs/cgroup/memory.peak /sys/fs/cgroup/memory.max /sys/fs/cgroup/memory.events"
_STATE_FIELDS = {
    "oom_killed": ".State.OOMKilled",
    "exit_code": ".State.ExitCode",
    "running": ".State.Running",
    "restarts": ".RestartCount",
    "memory_bytes": ".HostConfig.Memory",
    "swap_bytes": ".HostConfig.MemorySwap",
    "nano_cpus": ".HostConfig.NanoCpus",
    "pids": ".HostConfig.PidsLimit",
    "read_only": ".HostConfig.ReadonlyRootfs",
    "cap_drop": ".HostConfig.CapDrop",
    "security_options": ".HostConfig.SecurityOpt",
}
_SAFE_EXCEPTIONS = {
    "ValueError",
    "RuntimeError",
    "TimeoutError",
    "OSError",
    "FileNotFoundError",
    "PermissionError",
    "JSONDecodeError",
    "AssertionError",
}


def arguments(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse only explicit prepared inputs and the bounded experiment choice.

    :param argv: Explicit tests or actual CLI arguments.
    :return: Required paths and explicit diagnostic memory selections.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepared-output", type=Path, required=True)
    parser.add_argument("--web-memory-mib", type=int, choices=(384, 256), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--browser-memory-mib",
        type=int,
        choices=BROWSER_MEMORY_CHOICES,
        default=DEFAULT_BROWSER_MEMORY_MIB,
    )
    parser.add_argument(
        "--resource-profile", choices=("default", "aggregate1024"), default="default"
    )
    return parser.parse_args(argv)


def validate_host() -> None:
    """Require clean root Linux/amd64 execution with observable cgroup v2.

    :return: None after bounded host preconditions pass.
    :raises ValueError: Wrong host, inherited environment or missing cgroup v2.
    """
    if (
        platform.system() != "Linux"
        or platform.machine() not in {"x86_64", "amd64"}
        or os.getuid() != 0
    ):
        raise ValueError("Disposable root Linux/amd64 runner required.")
    if set(os.environ) - {"LC_CTYPE"}:
        raise ValueError("Run with env -i; no inherited credentials or configuration.")
    if not Path("/sys/fs/cgroup/cgroup.controllers").is_file():
        raise ValueError("Actual cgroup-v2 measurements are required.")


def allocate_root(nonce: str) -> Path:
    """Allocate one fresh private directory and positively bound owner marker.

    :param nonce: Fresh cryptographic invocation identity.
    :return: Verified exclusive private root.
    :raises Exception: Existing paths or failed ownership guards.
    """
    contract.owner_record(nonce)
    root = Path("/var/tmp") / f"mimir-experts-{nonce}"
    root.mkdir(mode=0o700, exist_ok=False)
    remote.private_file(root / "controller-owner.json", json.dumps({"nonce": nonce}))
    remote.verify_root(root, nonce)
    return root


def copy_runtime(root: Path, source: dict[str, Any]) -> dict[str, str]:
    """Copy and hash only explicitly reviewed runtime files outside /app.

    :param root: Positively owned private directory.
    :param source: Actual validated application manifest.
    :return: Exact runtime/source hashes for public provenance.
    :raises ValueError: Runtime member is linked or exceeds the fixed size bound.
    """
    runtime = root / "runtime"
    runtime.mkdir(mode=0o700)
    hashes = {}
    for name in RUNTIME_FILES:
        path = Path(__file__).resolve().parent / name
        if (
            path.resolve() != path
            or path.stat().st_nlink != 1
            or path.stat().st_size > 2 * _MIB
        ):
            raise ValueError("Unsafe or oversized reviewed runtime member.")
        data = reviewed_bytes(Path(__file__).resolve().parents[2], path)
        remote.private_file(runtime / name, data.decode())
        hashes[name] = hashlib.sha256(data).hexdigest()
    remote.private_file(runtime / "source.json", json.dumps(source, sort_keys=True))
    hashes["source.json"] = hashlib.sha256(
        (runtime / "source.json").read_bytes()
    ).hexdigest()
    return hashes


def manifest_for(root: Path, plan: dict[str, Any], nonce: str) -> dict[str, Any]:
    """Derive a fixed runtime manifest from positively proven local cached images.
    :param root: Private Docker credential directory.
    :param plan: Validated controller preparation.
    :param nonce: Newly allocated identity, separate from source preparation.
    :return: Exact whitelisted runtime declaration.
    :raises ValueError: Cached identity or contract fails.
    """
    manifest = {
        key: plan[key]
        for key in (
            "account",
            "source_revision",
            "build_run_id",
            "bucket",
            "fixture_sha256",
        )
    }
    receipt_keys = ("source_revision", "run_id", "web_image", "web_digest", "platforms")
    manifest["build_receipt"] = {
        key: plan["build_receipt"][key] for key in receipt_keys
    }
    manifest.update(
        {"nonce": nonce, **{f"{role}_image": image for role, image in IMAGES.items()}}
    )
    manifest["image_sizes"] = validate_cache(
        remote.inspect_cached_images(root, manifest)
    )
    contract.validate_runtime_manifest(manifest)
    return manifest


def run_browser(
    root: Path,
    manifest: dict[str, Any],
    names: dict[str, str],
    owner: aggregate.Owner | None = None,
    result: dict[str, Any] | None = None,
) -> None:
    """Run the genuine browser and real database readback under the chosen profile.

    :param root: Private source/output root.
    :param manifest: Immutable source/image selectors.
    :param names: Exact owned resources.
    :param owner: Explicit parent or unchanged defaultNone.
    :param result: Independent safe HOST receipt.
    :return: None after actual browser and post-browser state checks.
    :raises Exception: Actual browser or ownership/readback failure.
    """
    start_observed_browser(root, manifest, names, owner, result)
    if remote.docker(root, "wait", names["browser"], timeout=600).strip() != "0":
        raise RuntimeError("Actual benchmark browser failed.")
    post_browser_readback(root, names, owner)


def container_state(root: Path, name: str, role: str) -> dict[str, Any]:
    """Read curated real Docker state without exporting any environment/config.

    :param root: Private invocation configuration.
    :param name: Exact positively owned container name.
    :param role: Explicit web, db or browser role.
    :return: Safe numeric/boolean bounds and runtime observations.
    :raises Exception: Actual Docker inspection fails.
    """
    template = (
        "{"
        + ",".join(
            f'"{key}":{{{{json {field}}}}}' for key, field in _STATE_FIELDS.items()
        )
        + "}"
    )
    row = json.loads(
        remote.docker(root, "container", "inspect", "--format", template, name)
    )
    if set(row) != set(_STATE_FIELDS):
        raise ValueError("Actual Docker observation fields differ.")
    return {"role": role, **row}


def memory_records(root: Path, nonce: str, names: dict[str, str]) -> dict[str, Any]:
    """Retain actual partial counters and safe missing-measurement classifications.

    :param root: Owned evidence root.
    :param nonce: Exact owner identity for every observation.
    :param names: Exact allocated container names.
    :return: Actual observations, including explicit failed/absent measurement.
    :raises OSError: Safe numeric receipt cannot be recorded.
    """
    records = {}
    for role in ("db", "web", "browser"):
        try:
            records[role] = capture_role(root, nonce, names[role], role)
        except Exception as error:  # noqa: BLE001 - safe classification.
            records[role] = {
                "measurement_exception": failure(error),
                "measurement_reason": failure_reason(error),
            }
    result = {"roles": records, "sum_of_individual_peaks_is_not_simultaneous": True}
    return result


def browser_text(record: dict[str, Any]) -> str:
    """Revalidate exported observer numbers instead of trusting its JSON shape.

    :param record: Actual observer result.
    :return: Numeric observation text for the shared strict parser.
    :raises ValueError: The observer shape or types are unsafe.
    """
    if (
        set(record) != {"role", "peak_bytes", "limit_bytes", "events", "driver_passed"}
        or record["role"] != "browser"
    ):
        raise ValueError("Unexpected browser metric fields.")
    if type(record["driver_passed"]) is not bool or not isinstance(
        record["events"], dict
    ):
        raise ValueError("Typed browser observation required.")
    values = [record["peak_bytes"], record["limit_bytes"], *record["events"].values()]
    if any(type(value) is not int for value in values):
        raise ValueError("Only actual numeric browser counters are accepted.")
    return "\n".join(
        [
            str(record["peak_bytes"]),
            str(record["limit_bytes"]),
            *(f"{key} {value}" for key, value in record["events"].items()),
        ]
    )


def workload(
    root: Path,
    manifest: dict[str, Any],
    names: dict[str, str],
    result: dict[str, Any],
    owner: aggregate.Owner | None = None,
) -> None:
    """Keep old initial guards and actual app/DB/browser work unchanged by default.

    :param root: Verified private invocation.
    :param manifest: Immutable candidate identity.
    :param names: Exact resources.
    :param result: Safe actual phase/measurement state.
    :param owner: Explicit CI parent or unchanged defaultNone.
    :return: None after genuine core and readback completion.
    :raises Exception: Any actual capacity, source or workload guard fails.
    """
    result["phase"] = "capacity"
    measured = remote.reserve_capacity(
        root, manifest, contract.validate_runtime_manifest(manifest)
    )
    require_ci_capacity(measured["available_memory_bytes"])
    remote.private_file(root / "output/capacity.json", json.dumps(measured, indent=2))
    password = provision_database(root, manifest, names, owner, result)
    provision_web(root, manifest, names, password, owner, result)
    result["phase"] = "browser_and_real_state_readback"
    run_browser(root, manifest, names, owner, result)
    result["status"] = "CORE_WORKLOAD_PASSED_MEASUREMENT_PENDING"


def failure(error: Exception) -> str:
    """Expose only a fixed exception class, never its private message or command.

    :param error: Actual failure.
    :return: Safe class whitelist value.
    """
    kind = type(error).__name__
    return kind if kind in _SAFE_EXCEPTIONS else "Exception"


def finish(
    root: Path,
    nonce: str,
    names: dict[str, str],
    output: Path,
    result: dict[str, Any],
    owner: aggregate.Owner | None = None,
) -> None:
    """Always clean exact labeled resources, then export checked public evidence.

    :param root: Positively owned private directory.
    :param nonce: Exact invocation identity.
    :param names: Only this invocation's names.
    :param output: Fresh actual public destination.
    :param result: Safe mutable status and cleanup receipt.
    :return: None after cleanup/export/removal; errors remain explicit in result.
    """
    try:
        remote.cleanup(root, nonce, names)
        cleanup_aggregate(owner, root, names)
        result["cleanup"] = "SUCCESS"
    except Exception as error:  # noqa: BLE001 - sanitize every owned boundary failure.
        result.update(
            status="FAILED", cleanup="FAILED", cleanup_exception=failure(error)
        )
    export_public(root, output, result)
    if result.get("cleanup") == "SUCCESS" and result.get("export") == "SUCCESS":
        remote.verify_root(root, nonce)
        shutil.rmtree(root)
        result["private_root_removed"] = True


def execute(
    prepared: Path,
    web_memory: int,
    output: Path,
    result: dict[str, Any],
    browser_memory: int = 512,
    resource_profile: str = "default",
) -> None:
    """Prepare an explicit selected experiment without changing default resource policy.

    :param prepared: Exact controller source preparation.
    :param web_memory: Existing web memory choice.
    :param output: Fresh public evidence directory.
    :param result: Safe HOST receipt.
    :param browser_memory: Existing closed browser memory choice.
    :param resource_profile: Default or fixed aggregate1024 CI-only preset.
    :return: None after real execution and cleanup.
    :raises Exception: Preparation fails before owned execution.
    """
    validate_host()
    preparation = validate_prepared(prepared, Path(__file__).resolve().parents[2])
    nonce = uuid4().hex
    root = allocate_root(nonce)
    choices = (web_memory, browser_memory, resource_profile)
    execute_allocated(root, nonce, preparation, choices, output, result)


def execute_allocated(
    root: Path,
    nonce: str,
    preparation: tuple[dict[str, Any], dict[str, Any]],
    choices: tuple[int, int, str],
    output: Path,
    result: dict[str, Any],
) -> None:
    """Retain positive owner state even if unit creation fails halfway through.
    :param root: Private allocated root.
    :param nonce: Fresh source owner.
    :param preparation: Validated plan and actual source map.
    :param choices: Explicit web/browser/profile selection.
    :param output: Fresh public destination.
    :param result: Independent safe HOST state.
    :return: None after genuine workload and settlement.
    """
    owner = None
    names = remote.resource_names(nonce)
    try:
        owner = initialize_runtime(root, preparation, choices, result)
        if owner is not None:
            result["aggregate_operation"] = "START_PARENT_AND_KEEPER"
            aggregate.start(owner)
        run_owned_workload(root, names, result, owner)
    except Exception as error:  # noqa: BLE001 - retain safe failure class.
        record_owned_failure(root, owner, error, result)
    finally:
        measure_and_finish(root, nonce, names, output, result, owner)


def initialize_runtime(
    root: Path,
    preparation: tuple[dict[str, Any], dict[str, Any]],
    choices: tuple[int, int, str],
    result: dict[str, Any],
) -> aggregate.Owner | None:
    """Bind a planned aggregate owner before its first actual unit operation.

    :param root: Exclusive private root.
    :param preparation: Validated plan/source maps.
    :param choices: Web/browser/profile choices.
    :param result: Safe actual selection metadata.
    :return: Explicit aggregate owner or None for unchanged defaults.
    :raises Exception: Profile, cache or source binding fails.
    """
    web, browser, profile = choices
    enabled = aggregate.validate_profile(profile, web, browser)
    plan, source = preparation
    prepare_runtime(
        root, plan, source, root.name[len("mimir-experts-") :], web, result, browser
    )
    result["resource_profile"] = profile
    if not enabled:
        return None
    return plan_aggregate(root, plan, result)


def prepare_runtime(
    root: Path,
    plan: dict[str, Any],
    source: dict[str, Any],
    nonce: str,
    web_memory: int,
    result: dict[str, Any],
    browser_memory: int = 512,
) -> None:
    """Install only reviewed controls and explicit experimental memory selection.

    :param root: Fresh private root.
    :param plan: Validated fixed candidate plan.
    :param source: Actual source manifest.
    :param nonce: Fresh invocation identity.
    :param web_memory:384 default or256 explicit experiment.
    :param result: Safe public result.
    :param browser_memory:512 default or768 CI-only experiment.
    :return: None after exact runtime setup and provenance are retained.
    :raises Exception: Runtime/cache/source guard fails.
    """
    select_envelope(web_memory, result, browser_memory)
    remote.create_directories(root)
    os.environ["DOCKER_CONFIG"] = str(root / "docker-config")
    hashes = copy_runtime(root, source)
    manifest = manifest_for(root, plan, nonce)
    remote.private_file(root / "runtime/run.json", json.dumps(manifest))
    write_provenance(root, plan, hashes, nonce)


def main() -> None:
    """Publish safe results with nonzero status for every failed benchmark.
    :return: None after real core measurement; staging/UAT remain unaccepted.
    :raises SystemExit:1 on validation, execution, cleanup or export failure.
    """
    options = arguments()
    output = options.output
    if not output.is_absolute() or output.resolve() != output:
        raise ValueError("An absolute new unlinked public destination is required.")
    output.mkdir(mode=0o700, exist_ok=False)
    result = {
        "status": "FAILED",
        "phase": "preparation",
        "cleanup": "NOT_ALLOCATED",
        "private_root_removed": False,
        "staging_accepted": False,
        "uat_accepted": False,
    }
    try:
        execute_cli(options, output, result)
    except Exception as error:  # noqa: BLE001 - safe classification.
        result.update(status="FAILED", exception_class=failure(error))
    publish_result(output, result)
    keys = ("status", "cleanup", "staging_accepted", "uat_accepted")
    print(json.dumps({key: result[key] for key in keys}), flush=True)
    if result["status"] == "FAILED":
        raise SystemExit(1)


def validate_container_state(row: dict[str, Any]) -> None:
    """Require unchanged real Docker hardening and zero OOM/restarts.
    :param row: Curated actual container inspection.
    :return: None after limits, state and isolation match.
    :raises ValueError: Actual runtime differs from its approved envelope.
    """
    role = row["role"]
    memory, cpus, pids, _ = remote._LIMITS[role]
    expected = {
        "oom_killed": False,
        "restarts": 0,
        "memory_bytes": memory * _MIB,
        "swap_bytes": memory * _MIB,
        "nano_cpus": int(float(cpus) * 10**9),
        "pids": pids,
        "read_only": True,
        "cap_drop": ["ALL"],
    }
    if any(
        row[key] != value or type(row[key]) is not type(value)
        for key, value in expected.items()
    ):
        raise ValueError("Actual Docker limits or hardening failed.")
    if "no-new-privileges" not in row["security_options"]:
        raise ValueError("Actual Docker privilege guard failed.")
    if role == "browser":
        if row["running"] is not False or row["exit_code"] != 0:
            raise ValueError("Actual browser exited unsuccessfully.")
    elif row["running"] is not True:
        raise ValueError("Actual application/database stopped unexpectedly.")


def capture_role(root: Path, nonce: str, name: str, role: str) -> dict[str, Any]:
    """Inspect one exact labeled container before its cgroup is removed.

    :param root: Private runtime root.
    :param nonce: Positive owner label.
    :param name: Exact allocated container.
    :param role: Explicit bounded role.
    :return: Actual state plus counters or fixed missing-measurement class.
    :raises Exception: Container ownership/state cannot be established.
    """
    remote.assert_resource(root, "container", name, nonce)
    result = {"docker": container_state(root, name, role)}
    try:
        if role == "browser":
            observed = read_json(root / "output/browser-memory.json")
            result["memory"] = parse_memory(
                browser_text(observed),
                role,
                browser_memory_bytes(remote._LIMITS["browser"][0]),
            )
            result["memory"]["driver_passed"] = observed["driver_passed"]
        else:
            text = remote.docker(
                root, "exec", name, "sh", "-c", _MEMORY_PROBE, timeout=20
            )
            result["memory"] = parse_memory(text, role, remote._LIMITS[role][0] * _MIB)
    except Exception as error:  # noqa: BLE001 - retain safe state.
        result["measurement_exception"] = failure(error)
        result["measurement_reason"] = failure_reason(error)
    return result


def validate_measurements(result: dict[str, Any]) -> None:
    """Reject incomplete measurement and require actual driver/state/headroom pass.

    :param result: Recorded actual role observations.
    :return: None only for all three genuine complete role measurements.
    :raises ValueError: Missing counters, cap exhaustion or failed real lifecycle.
    """
    records = result["roles"]
    if set(records) != {"db", "web", "browser"}:
        raise ValueError("All three role observations are required.")
    for role, row in records.items():
        if set(row) != {"memory", "docker"} or row["memory"]["role"] != role:
            raise ValueError("Actual role measurement is incomplete.")
        require_headroom(row["memory"])
        validate_container_state(row["docker"])
    if records["browser"]["memory"]["driver_passed"] is not True:
        raise ValueError("The actual browser driver did not pass.")


def measure_and_finish(
    root: Path,
    nonce: str,
    names: dict[str, str],
    output: Path,
    result: dict[str, Any],
    owner: aggregate.Owner | None = None,
) -> None:
    """Measure before cleanup even on failure, then settle exact owned resources.

    :param root: Owned runtime directory.
    :param nonce: Positive owner identity.
    :param names: Only owned resource names.
    :param output: Safe public export directory.
    :param result: Original phase/failure receipt, preserving safe observations.
    :return: None with actual metric, cleanup and export status.
    """
    try:
        retain_measurements(root, nonce, names, result, owner)
    except Exception as error:  # noqa: BLE001 - fixed enum and class only.
        if result["status"] != "FAILED":
            result["phase"] = "measurement"
        result.update(
            status="FAILED",
            measurement="FAILED",
            measurement_exception=failure(error),
            measurement_reason=failure_reason(error),
        )
    finally:
        finish(root, nonce, names, output, result, owner)


def retain_measurements(
    root: Path,
    nonce: str,
    names: dict[str, str],
    result: dict[str, Any],
    owner: aggregate.Owner | None = None,
) -> None:
    """Put sanitized numeric observations in HOST result before any exporter check.

    :param root: Owned private root.
    :param nonce: Positive owner identity.
    :param names: Exact allocated resources.
    :param result: Curated independent host result.
    :return: None after actual complete measurements pass.
    :raises Exception: Counters, receipt writing or actual runtime checks fail.
    """
    result["browser_diagnostic"] = read_browser_diagnostic(root)
    measured = memory_records(root, nonce, names)
    result["observations"] = host_observations(measured)
    remote.private_file(
        root / "output/benchmark-memory.json", json.dumps(measured, indent=2)
    )
    retain_aggregate_observation(owner, result)
    validate_measurements(measured)
    result["measurement"] = "SUCCESS"
    if result["status"] == "CORE_WORKLOAD_PASSED_MEASUREMENT_PENDING":
        result.update(
            status="MEASURED_CORE_ONLY_NOT_STAGING_ACCEPTANCE", phase="completed"
        )


def read_browser_diagnostic(root: Path) -> dict[str, Any]:
    """Independently validate observer frames even when the bulk exporter rejects.

    :param root: Actual private owned root.
    :return: Validated closed failure diagnostic or fixed unavailable reason.
    """
    path = root / "output/browser-diagnostic.json"
    if not path.exists() and not path.is_symlink():
        return {"status": "NOT_RECORDED"}
    try:
        return parse_browser_diagnostic(validated_diagnostic_bytes(path))
    except Exception as error:  # noqa: BLE001 - never expose diagnostic input text.
        return {
            "status": "REJECTED",
            "exception_class": failure(error),
            "reason": failure_reason(error),
        }


def select_envelope(
    web_memory: int, result: dict[str, Any], browser_memory: int = 512
) -> None:
    """Change only local CI memory choices while preserving primary defaults.

    :param web_memory:384 default or256 explicit diagnostic experiment.
    :param result: Safe public result.
    :param browser_memory:512 default or768 explicit diagnostic experiment.
    :return: None after all CPU/pid/tmp/DB limits and reserve stay preserved.
    :raises ValueError: An unsupported or wrongly typed choice is requested.
    """
    if type(web_memory) is not int or web_memory not in {384, 256}:
        raise ValueError("Only explicit reviewed memory experiments are allowed.")
    browser_memory_bytes(browser_memory)
    for role, memory in (("web", web_memory), ("browser", browser_memory)):
        remote._LIMITS[role] = (memory, *remote._LIMITS[role][1:])
    record_envelope(web_memory, browser_memory, result)


def write_provenance(
    root: Path, plan: dict[str, Any], hashes: dict[str, str], nonce: str
) -> None:
    """Retain exact committed controls, candidate and source manifest identities.

    :param root: Private owned root.
    :param plan: Validated prepared source/runner plan.
    :param hashes: Exact copied runtime byte hashes.
    :param nonce: Fresh runtime identity.
    :return: None after safe public provenance is written.
    :raises Exception: Driver/control bytes differ from reviewed Git source.
    """
    repository = Path(__file__).resolve().parents[2]
    for name in ("benchmark.py", "benchmark_contract.py"):
        data = reviewed_bytes(repository, Path(__file__).resolve().parent / name)
        hashes[name] = hashlib.sha256(data).hexdigest()
    provenance = {
        "source_revision": SOURCE,
        "build_run_id": BUILD,
        "runner_revision": plan["runner_revision"],
        "runtime_sha256": hashes,
        "images": IMAGES,
        "nonce": nonce,
    }
    remote.private_file(
        root / "output/benchmark-source.json", json.dumps(provenance, indent=2)
    )


def publish_result(output: Path, result: dict[str, Any]) -> None:
    """Publish safe cleanup/failure status and transfer only checked public files.

    :param output: Fresh invocation-owned public directory.
    :param result: Safe result, never private exception messages.
    :return: None after upload ownership succeeds or a safe failure is retained.
    :raises OSError: Result cannot be written safely.
    """
    path = output / "benchmark-result.json"
    remote.private_file(path, json.dumps(result, indent=2))
    try:
        publish_owner(output)
    except Exception as error:  # noqa: BLE001 - retain safe publication failure.
        result.update(
            status="FAILED",
            public_ownership="FAILED",
            publication_exception=failure(error),
        )
        if path.resolve() != path or path.stat().st_nlink != 1:
            raise ValueError("Result file became linked during publication.") from None
        descriptor = os.open(path, os.O_WRONLY | os.O_TRUNC | os.O_NOFOLLOW)
        with os.fdopen(descriptor, "w") as stream:
            json.dump(result, stream, indent=2)


def export_public(root: Path, output: Path, result: dict[str, Any]) -> None:
    """Keep bulk export fail-closed while retaining only fixed failure/shape enums.

    :param root: Owned runtime and original evidence directory.
    :param output: Fresh independent HOST publication directory.
    :param result: Safe HOST result, including numeric observations.
    :return: None with explicit actual export success or safe rejection metadata.
    """
    try:
        result["evidence"] = safe_export(root / "output", output)
        result["export"] = "SUCCESS"
    except Exception as error:  # noqa: BLE001 - sanitize every owned boundary failure.
        result.update(
            status="FAILED",
            export="FAILED",
            export_exception=failure(error),
            export_reason=failure_reason(error),
        )
        result["export_rejected_shapes"] = rejected_export_shapes(root / "output")


def record_envelope(
    web_memory: int, browser_memory: int, result: dict[str, Any]
) -> None:
    """Label the selected CI envelope explicitly, without adopting it for idle.

    :param web_memory: Validated local web cap.
    :param browser_memory: Validated local browser cap.
    :param result: Safe HOST result.
    :return: None after fixed experiment metadata and unchanged reserves are saved.
    """
    result.update(
        web_memory_mib=web_memory,
        browser_memory_mib=browser_memory,
        experiment="DEFAULT_384" if web_memory == 384 else "EXPERIMENT_256",
        browser_experiment=(
            "DEFAULT_512" if browser_memory == 512 else "CI_EXPERIMENT_768"
        ),
        scope="DISPOSABLE_CI_ONLY",
        envelope_mib={role: bounds[0] for role, bounds in remote._LIMITS.items()},
        host_reserve_mib=_HOST_RESERVE_MIB,
        idle_guard_mib=1400,
        ci_initial_required_memory_mib=ci_memory_requirement() // _MIB,
        ci_live_browser_reserve_mib=browser_memory + _HOST_RESERVE_MIB,
    )


def observed_browser_arguments(
    root: Path,
    manifest: dict[str, Any],
    names: dict[str, str],
    parent: str | None = None,
) -> list[str]:
    """Bind the same closed cap to actual Docker limits and observer verification.

    :param root: Owned private runtime.
    :param manifest: Fixed immutable image/source selectors.
    :param names: Exact owned container/network identities.
    :return: Original hardened command with only the observer entrypoint/choice.
    :raises ValueError: Browser cap or actual command contract is unexpected.
    """
    memory = remote._LIMITS["browser"][0]
    browser_memory_bytes(memory)
    command = remote.browser_arguments(root, manifest, names, parent)
    if command[-1] != "/runtime/browser.py":
        raise ValueError("Actual browser command contract changed.")
    command[-1] = "/runtime/benchmark_observer.py"
    return [*command, "--browser-memory-mib", str(memory)]


def require_ci_capacity(available_bytes: int) -> None:
    """Keep the original floor and add sufficient reserve for the larger CI choice.

    :param available_bytes: Actual fresh capacity from the unchanged remote guard.
    :return: None if selected caps plus256MiB and the original floor both fit.
    :raises ValueError: Typed fresh capacity cannot safely fit the experiment.
    """
    required = ci_memory_requirement()
    if type(available_bytes) is not int or available_bytes < required:
        raise ValueError(
            "Selected CI caps plus host reserve exceed fresh available memory."
        )


def require_ci_browser_reserve(memory_mib: int) -> None:
    """Retain the old live guard and also reserve256MiB beyond the chosen browser.

    :param memory_mib: Explicit512 or768 CI-only cap.
    :return: None after both actual live capacity checks pass.
    :raises ValueError: Fresh memory cannot safely fit browser plus reserve.
    """
    remote.require_browser_reserve()
    available = (
        int(
            next(
                line.split()[1]
                for line in Path("/proc/meminfo").read_text().splitlines()
                if line.startswith("MemAvailable:")
            )
        )
        * 1024
    )
    if available < browser_memory_bytes(memory_mib) + _HOST_RESERVE_MIB * _MIB:
        raise ValueError(
            "Selected browser plus host reserve exceed fresh available memory."
        )


def run_owned_workload(
    root: Path,
    names: dict[str, str],
    result: dict[str, Any],
    owner: aggregate.Owner | None = None,
) -> None:
    """Keep the unchanged bounded real lifecycle within its normal cleanup window.

    :param root: Positive private runtime root.
    :param names: Exact owned resource identities.
    :param result: Safe phase/result receipt.
    :return: None after actual workload completion.
    :raises Exception: Real source, resource, browser or state verification fails.
    """
    manifest = read_json(root / "runtime/run.json")
    with remote.runtime_deadline():
        workload(root, manifest, names, result, owner)


def execute_cli(
    options: argparse.Namespace, output: Path, result: dict[str, Any]
) -> None:
    """Forward only parsed closed CI choices to the actual owned experiment.

    :param options: Actual validated argparse result.
    :param output: Fresh public directory.
    :param result: Safe HOST receipt.
    :return: None after the actual selected experiment and settlement.
    :raises Exception: The genuine execution fails.
    """
    execute(
        options.prepared_output,
        options.web_memory_mib,
        output,
        result,
        options.browser_memory_mib,
        options.resource_profile,
    )


def ci_memory_requirement() -> int:
    """Compute selected CI ceilings plus the preserved host reserve and floor.

    :return: Exact initial required bytes, never below the primary1400MiB floor.
    """
    selected = sum(bounds[0] for bounds in remote._LIMITS.values())
    return max(contract.MIN_AVAILABLE_MEMORY, (selected + _HOST_RESERVE_MIB) * _MIB)


def verify_aggregate_member(
    owner: aggregate.Owner | None,
    root: Path,
    names: dict[str, str],
    role: str,
    result: dict[str, Any] | None,
) -> None:
    """Verify actual parent, labels, enforced limits and host PID after each start.

    :param owner: Explicit owner or unchanged default.
    :param root: Private Docker configuration.
    :param names: Exact resources.
    :param role: One fixed container role.
    :param result: Safe independent HOST receipt.
    :return: None after actual membership proof.
    :raises Exception: Actual identity or enforced ancestry differs.
    """
    if owner is None:
        return
    remote.assert_resource(root, "container", names[role], owner.nonce)
    row = aggregate_container_row(root, names[role])
    aggregate.verify_member(owner, role, row)
    if result is not None:
        result.setdefault("aggregate_members", {})[role] = True


def retain_aggregate_observation(
    owner: aggregate.Owner | None, result: dict[str, Any]
) -> None:
    """Keep typed actual parent metrics in HOST state before acceptance/export.

    :param owner: Explicit positively owned parent, or defaultNone.
    :param result: Independent safe HOST result.
    :return: None only after exact aggregate measurement and member proof pass.
    :raises Exception: Any live identity, member, cap or headroom proof fails.
    """
    if owner is None:
        return
    result["aggregate"] = aggregate.observe(owner)
    aggregate.require_headroom(result["aggregate"])
    if not result["aggregate"]["keeper_verified"] or result.get(
        "aggregate_members"
    ) != {"db": True, "web": True, "browser": True}:
        raise ValueError("Aggregate complete membership proof is missing.")


def cleanup_aggregate(
    owner: aggregate.Owner | None, root: Path, names: dict[str, str]
) -> None:
    """Confirm Docker absence before stopping either exact owned transient unit.

    :param owner: Explicit parent owner or defaultNone.
    :param root: Private Docker config.
    :param names: Exact invocation names.
    :return: None only after both owned units and kernel parent are gone.
    :raises Exception: Inventory, ownership or parent cleanup fails.
    """
    if owner is None:
        return
    existing = remote.docker(
        root, "container", "ls", "--all", "--format", "{{.Names}}", timeout=20
    ).splitlines()
    remaining = [
        names[role] for role in ("db", "web", "browser") if names[role] in existing
    ]
    aggregate.cleanup(owner, remaining)


def plan_aggregate(
    root: Path, plan: dict[str, Any], result: dict[str, Any]
) -> aggregate.Owner:
    """Bind the actual supported driver and source before transient unit creation.

    :param root: Exclusive private root.
    :param plan: Validated control source identity.
    :param result: Independent HOST receipt.
    :return: Explicit private aggregate owner.
    :raises ValueError: Actual Docker driver/version is unsupported.
    """
    result["aggregate_limit_bytes"] = aggregate.LIMIT_BYTES
    row = json.loads(
        remote.docker(
            root,
            "info",
            "--format",
            '{"driver":{{json .CgroupDriver}},"version":{{json .CgroupVersion}}}',
        )
    )
    aggregate.require_driver(row)
    return aggregate.plan(
        root, root.name[len("mimir-experts-") :], plan["runner_revision"]
    )


def aggregate_container_row(root: Path, name: str) -> dict[str, Any]:
    """Read only explicit non-secret Docker identity/limit fields.

    :param root: Private Docker configuration.
    :param name: Exact owned container name.
    :return: Actual curated observation; never Config.Env or raw inspect.
    """
    fields = {
        "id": ".Id",
        "pid": ".State.Pid",
        "running": ".State.Running",
        "parent": ".HostConfig.CgroupParent",
        "memory": ".HostConfig.Memory",
        "swap": ".HostConfig.MemorySwap",
        "owner": 'index .Config.Labels "io.featurefactory.experts.owner"',
        "fixture": 'index .Config.Labels "io.featurefactory.experts.fixture"',
        "readonly": ".HostConfig.ReadonlyRootfs",
        "cap_drop": ".HostConfig.CapDrop",
        "security": ".HostConfig.SecurityOpt",
        "restarts": ".RestartCount",
    }
    template = (
        "{"
        + ",".join(f'"{key}":{{{{json ({value})}}}}' for key, value in fields.items())
        + "}"
    )
    return json.loads(
        remote.docker(root, "container", "inspect", "--format", template, name)
    )


def start_observed_browser(
    root: Path,
    manifest: dict[str, Any],
    names: dict[str, str],
    owner: aggregate.Owner | None,
    result: dict[str, Any] | None,
) -> None:
    """Start only the real hardened observer after the correct live budget guard.

    :param root: Private runtime.
    :param manifest: Fixed image/source identity.
    :param names: Exact allocated resources.
    :param owner: Explicit aggregate parent or defaultNone.
    :param result: Independent HOST state.
    :return: None after actual browser PID parent proof.
    """
    if owner is None:
        require_ci_browser_reserve(remote._LIMITS["browser"][0])
    else:
        aggregate.guard(owner)
    parent = aggregate.parent_name(owner.nonce) if owner is not None else None
    remote.docker(root, *observed_browser_arguments(root, manifest, names, parent))
    remote.docker(root, "network", "connect", names["egress"], names["browser"])
    remote.docker(root, "start", names["browser"])
    verify_aggregate_member(owner, root, names, "browser", result)
    remote.write_isolation_receipt(root, manifest, names)


def provision_database(
    root: Path,
    manifest: dict[str, Any],
    names: dict[str, str],
    owner: aggregate.Owner | None,
    result: dict[str, Any],
) -> str:
    """Preserve actual fresh PG initialization and prove its selected parent.

    :param root: Private invocation.
    :param manifest: Fixed PG image/source identity.
    :param names: Exact resource names.
    :param owner: Explicit aggregate parent or defaultNone.
    :param result: Safe HOST state.
    :return: Actual dedicated app password, never exported.
    """
    result["phase"] = "database"
    remote.create_networks(root, manifest["nonce"], names)
    parent = aggregate.parent_name(owner.nonce) if owner is not None else None
    if owner is not None:
        aggregate.guard(owner)
    password = remote.start_database(
        root, manifest["nonce"], names, manifest["postgres_image"], parent
    )
    verify_aggregate_member(owner, root, names, "db", result)
    return password


def provision_web(
    root: Path,
    manifest: dict[str, Any],
    names: dict[str, str],
    password: str,
    owner: aggregate.Owner | None,
    result: dict[str, Any],
) -> None:
    """Preserve real TLS/source/bootstrap and positively prove actual web ancestry.

    :param root: Private invocation.
    :param manifest: Fixed candidate selectors.
    :param names: Exact resources.
    :param password: Private owned database password.
    :param owner: Explicit aggregate parent or defaultNone.
    :param result: Safe HOST state.
    :return: None after genuine HTTPS health succeeds.
    """
    result["phase"] = "web"
    remote.write_app_runtime(root, manifest, password)
    parent = aggregate.parent_name(owner.nonce) if owner is not None else None
    if owner is not None:
        aggregate.guard(owner)
    remote.start_web(root, manifest, names, parent)
    verify_aggregate_member(owner, root, names, "web", result)
    remote.wait_web(root, manifest, names)


def post_browser_readback(
    root: Path, names: dict[str, str], owner: aggregate.Owner | None
) -> None:
    """Run the unchanged real owned DB readback after browser completion.

    :param root: Private runtime.
    :param names: Exact known resources.
    :param owner: Explicit aggregate or defaultNone.
    :return: None only after actual bootstrap.verify_after succeeds.
    :raises Exception: Reserve or real readback fails.
    """
    if owner is not None:
        aggregate.guard(owner)
    remote.docker(
        root,
        "exec",
        names["web"],
        "python",
        "manage.py",
        "shell",
        "--no-imports",
        "-c",
        "from bootstrap import verify_after; verify_after()",
    )


def record_owned_failure(
    root: Path, owner: aggregate.Owner | None, error: Exception, result: dict[str, Any]
) -> None:
    """Preserve original failed status even if private diagnostic validation fails.

    :param root: Positively owned private root.
    :param owner: Explicit aggregate or defaultNone.
    :param error: Actual original failure; its message/args are never exported.
    :param result: Independent safe HOST state.
    :return: None after fixed failure classification is retained.
    """
    result.update(status="FAILED", exception_class=failure(error))
    if owner is not None:
        try:
            result["aggregate_failure"] = aggregate.failure_receipt(owner)
        except (ValueError, TypeError, OSError):
            result["aggregate_failure"] = {
                "operation": "PRIVATE_EVIDENCE_REJECTED",
                "manager_error": "UNCLASSIFIED",
            }
    remote.record_runtime_failure(root, error)


if __name__ == "__main__":
    main()
