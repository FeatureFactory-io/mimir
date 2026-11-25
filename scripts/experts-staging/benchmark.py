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
)
from benchmark_metrics import (
    failure_reason,
    host_observations,
    parse_memory,
    require_headroom,
    validate_browser_failure,
)

_MIB = 1024 * 1024
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


def arguments() -> argparse.Namespace:
    """Parse only explicit prepared inputs and the bounded experiment choice.

    :return: Required absolute paths and web memory selection.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepared-output", type=Path, required=True)
    parser.add_argument("--web-memory-mib", type=int, choices=(384, 256), required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


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


def run_browser(root: Path, manifest: dict[str, Any], names: dict[str, str]) -> None:
    """Keep actual hardened browser lifecycle, adding only its numeric observer.
    :param root: Owned runtime and output root.
    :param manifest: Fixed immutable image and source identities.
    :param names: Exact allocated Docker resources.
    :return: None after real Chromium and actual bootstrap.verify_after pass.
    :raises Exception: Guard, real browser or actual post-browser DB readback fails.
    """
    remote.require_browser_reserve()
    command = remote.browser_arguments(root, manifest, names)
    if command[-1] != "/runtime/browser.py":
        raise ValueError("Actual browser command contract changed.")
    command[-1] = "/runtime/benchmark_observer.py"
    remote.docker(root, *command)
    remote.docker(root, "network", "connect", names["egress"], names["browser"])
    remote.docker(root, "start", names["browser"])
    remote.write_isolation_receipt(root, manifest, names)
    if remote.docker(root, "wait", names["browser"], timeout=600).strip() != "0":
        raise RuntimeError("Actual benchmark browser failed.")
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
    root: Path, manifest: dict[str, Any], names: dict[str, str], result: dict[str, Any]
) -> None:
    """Execute genuine owned lifecycle without image pulls or external DB inputs.

    :param root: Verified private root.
    :param manifest: Validated immutable candidate.
    :param names: Fresh exact resource names.
    :param result: Safe mutable phase/status receipt.
    :return: None only after actual HTTPS/browser/DB and measurement checks.
    :raises Exception: Any real lifecycle or measurement guard fails.
    """
    result["phase"] = "capacity"
    measured = remote.reserve_capacity(
        root, manifest, contract.validate_runtime_manifest(manifest)
    )
    remote.private_file(root / "output/capacity.json", json.dumps(measured, indent=2))
    result["phase"] = "database"
    remote.create_networks(root, manifest["nonce"], names)
    password = remote.start_database(
        root, manifest["nonce"], names, manifest["postgres_image"]
    )
    result["phase"] = "web"
    remote.write_app_runtime(root, manifest, password)
    remote.start_web(root, manifest, names)
    remote.wait_web(root, manifest, names)
    result["phase"] = "browser_and_real_state_readback"
    run_browser(root, manifest, names)
    result["status"] = "CORE_WORKLOAD_PASSED_MEASUREMENT_PENDING"


def failure(error: Exception) -> str:
    """Expose only a fixed exception class, never its private message or command.

    :param error: Actual failure.
    :return: Safe class whitelist value.
    """
    kind = type(error).__name__
    return kind if kind in _SAFE_EXCEPTIONS else "Exception"


def finish(
    root: Path, nonce: str, names: dict[str, str], output: Path, result: dict[str, Any]
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
    prepared: Path, web_memory: int, output: Path, result: dict[str, Any]
) -> None:
    """Prepare one experiment and keep owned cleanup on every actual failure path.

    :param prepared: Actual reviewed controller preparation.
    :param web_memory: Explicit384 default or256 experiment.
    :param output: Fresh absolute public destination.
    :param result: Curated public result under construction.
    :return: None when all actual checks and cleanup succeed.
    :raises Exception: Preparation fails before owned execution.
    """
    validate_host()
    repository = Path(__file__).resolve().parents[2]
    plan, source = validate_prepared(prepared, repository)
    nonce = uuid4().hex
    root = allocate_root(nonce)
    names = remote.resource_names(nonce)
    try:
        prepare_runtime(root, plan, source, nonce, web_memory, result)
        manifest = read_json(root / "runtime/run.json")
        with remote.runtime_deadline():
            workload(root, manifest, names, result)
    except Exception as error:  # noqa: BLE001 - sanitize every owned boundary failure.
        result.update(status="FAILED", exception_class=failure(error))
        remote.record_runtime_failure(root, error)
    finally:
        measure_and_finish(root, nonce, names, output, result)


def prepare_runtime(
    root: Path,
    plan: dict[str, Any],
    source: dict[str, Any],
    nonce: str,
    web_memory: int,
    result: dict[str, Any],
) -> None:
    """Install only reviewed controls and explicit experimental memory selection.

    :param root: Fresh private root.
    :param plan: Validated fixed candidate plan.
    :param source: Actual source manifest.
    :param nonce: Fresh invocation identity.
    :param web_memory:384 default or256 explicit experiment.
    :param result: Safe public result.
    :return: None after exact runtime setup and provenance are retained.
    :raises Exception: Runtime/cache/source guard fails.
    """
    select_envelope(web_memory, result)
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
        execute(options.prepared_output, options.web_memory_mib, output, result)
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
            result["memory"] = parse_memory(browser_text(observed), role, 512 * _MIB)
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
    root: Path, nonce: str, names: dict[str, str], output: Path, result: dict[str, Any]
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
        retain_measurements(root, nonce, names, result)
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
        finish(root, nonce, names, output, result)


def retain_measurements(
    root: Path, nonce: str, names: dict[str, str], result: dict[str, Any]
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
        return validate_browser_failure(read_json(path))
    except Exception as error:  # noqa: BLE001 - never expose diagnostic input text.
        return {
            "status": "REJECTED",
            "exception_class": failure(error),
            "reason": failure_reason(error),
        }


def select_envelope(web_memory: int, result: dict[str, Any]) -> None:
    """Change only this process's web cap, explicitly labeling the experiment.

    :param web_memory:384 default or256 explicit experiment.
    :param result: Safe public result.
    :return: None after unchanged CPU/pids/tmp and other role caps are preserved.
    :raises ValueError: An unsupported experiment is requested.
    """
    if type(web_memory) is not int or web_memory not in {384, 256}:
        raise ValueError("Only explicit reviewed memory experiments are allowed.")
    current = remote._LIMITS["web"]
    remote._LIMITS["web"] = (web_memory, *current[1:])
    result.update(
        web_memory_mib=web_memory,
        experiment="DEFAULT_384" if web_memory == 384 else "EXPERIMENT_256",
        envelope_mib={role: bounds[0] for role, bounds in remote._LIMITS.items()},
        host_reserve_mib=256,
        idle_guard_mib=1400,
    )


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


if __name__ == "__main__":
    main()
