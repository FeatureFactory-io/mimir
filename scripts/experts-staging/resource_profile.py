"""Closed measured resource proof and public receipt contracts; no host operations."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from benchmark_metrics import parse_events, require_headroom
from suite_contract import selected_case

MIB = 1024**2
PROOF_FILES = {
    "resource-proof-result.json": "5a01022824151a166000a32b0ad28bba1395b704e4244de3d639248a6b2b7556",
    "resource-proof-source.json": "2334ed1c714de49f4808651e4b0b69e7a44335c493906a5ca930def2cc5a7766",
}
SOURCE = "04c9432bce7eac5ec34a090bc5e8ec4fa06f409d"
RUNNER = "bf245630222dad6ae89d67f143343eb9863df4aa"
IMAGES = {
    "web": "411113550285.dkr.ecr.us-east-1.amazonaws.com/mimir@sha256:e7f6e2170fd6250a9b6c3f635ceb2b90d0dfbe81ed337c10180c0a903ca5e1ba",
    "browser": "411113550285.dkr.ecr.us-east-1.amazonaws.com/mimir@sha256:a74104c8fb4ff8a02dd053ee2584868d91dd4273f058b690faf0875684c5e368",
    "postgres": "postgres@sha256:07abc3f43c9395b0bdbbab36bc25ddb0e8d83cd4fcafb5fb7d6abe14ff156dd8",
}
CAPS = {"web": 384, "db": 192, "browser": 768}

_PARENT_NUMERIC = {
    "current_bytes",
    "peak_bytes",
    "limit_bytes",
    "swap_current_bytes",
    "swap_limit_bytes",
}


def selected(manifest: dict[str, Any]) -> bool:
    """Select only the explicit measured profile.

    :param manifest: Authenticated invocation.
    :return: True only for aggregate1024, False for the unchanged default.
    :raises ValueError: Selector is unknown.
    """
    value = manifest.get("resource_profile", "default")
    if not isinstance(value, str) or value not in {"default", "aggregate1024"}:
        raise ValueError("Unknown staged resource profile.")
    return value == "aggregate1024"


def validate_proof(result: bytes, source: bytes, manifest: dict[str, Any]) -> None:
    """Bind fixed successful CI bytes and semantics to the exact candidate.

    :param result: Original named result bytes.
    :param source: Original named source bytes.
    :param manifest: Actual immutable candidate image/source declaration.
    :return: None only after fixed measurement proof matches.
    :raises ValueError: Proof, images, source or successful measurement differs.
    """
    for raw, digest in zip((result, source), PROOF_FILES.values()):
        if hashlib.sha256(raw).hexdigest() != digest:
            raise ValueError("Exact immutable successful CI proof bytes required.")
    measured, identity = json.loads(result), json.loads(source)
    validate_images(manifest)
    proof_semantics(measured, identity)


def require_capacity(memory: int, disk: int, cached: bool) -> None:
    """Admit the fixed floor only for positively cached exact measured images.

    :param memory: Fresh available memory bytes.
    :param disk: Fresh free Docker-storage bytes.
    :param cached: Complete actual exact-image metadata proof.
    :return: None at1280MiB memory/1GiB storage with positive warm proof.
    :raises ValueError: Any typed input, cache identity or reserve differs.
    """
    if (
        type(memory) is not int
        or type(disk) is not int
        or cached is not True
        or memory < 1280 * MIB
        or disk < 1024 * MIB
    ):
        raise ValueError(
            "Measured profile requires exact warm images and fixed reserve."
        )


def validate_images(manifest: dict[str, Any]) -> None:
    """Reject reuse of the measured proof with any other app or image.

    :param manifest: Actual candidate source and immutable image references.
    :return: None only for the measured fixed tuple.
    :raises ValueError: Source, build or any image differs.
    """
    if (
        manifest.get("source_revision") != SOURCE
        or manifest.get("build_run_id") != "45516980492"
        or any(manifest.get(role + "_image") != image for role, image in IMAGES.items())
    ):
        raise ValueError("Measured profile is bound to its exact candidate images.")


def validate_files(directory: Path, manifest: dict[str, Any]) -> None:
    """Revalidate the transported original named proof before host mutation.

    :param directory: Owned preparation or runtime controls directory.
    :param manifest: Actual candidate and explicit profile.
    :return: None only for complete immutable proof.
    :raises ValueError: Missing, linked or oversized proof is unsafe.
    """
    paths = [directory / name for name in PROOF_FILES]
    if any(
        path.is_symlink() or not path.is_file() or path.stat().st_size > 262144
        for path in paths
    ):
        raise ValueError("Bounded regular immutable resource proof files required.")
    validate_proof(*(path.read_bytes() for path in paths), manifest)


def canonical(record: dict[str, Any]) -> bytes:
    """Serialize the closed safe projection in one exact byte representation.

    :param record: Validated projection.
    :return: Deterministic UTF8 JSON with a final newline.
    """
    return (json.dumps(record, sort_keys=True, indent=2) + "\n").encode()


def checked_memory(
    row: dict[str, Any], role: str, passing: bool = True
) -> dict[str, Any]:
    """Retain typed actual counters and reject exhaustion only for acceptance.

    :param row: Closed actual numeric memory projection.
    :param role: Fixed role with enforced cap.
    :param passing: Require a successful workload without exhaustion.
    :return: The closed safe actual projection, including failed numeric evidence.
    :raises ValueError: Shape, types, cap or required headroom differs.
    """
    memory_shape(row, role)
    checked_events(row["events"], passing)
    if passing:
        require_headroom(row)
    if role == "browser" and (
        type(row["driver_passed"]) is not bool or (passing and not row["driver_passed"])
    ):
        raise ValueError("Actual complete suite dispatch must pass.")
    return row


def checked_parent(row: dict[str, Any], passing: bool = True) -> None:
    """Validate actual simultaneous parent counters without hiding failed peaks.

    :param row: Closed actual kernel projection.
    :param passing: Require active keeper and measured positive headroom.
    :return: None after the safe actual projection validates.
    :raises ValueError: Schema, caps, swap, events or required headroom differ.
    """
    parent_shape(row)
    checked_events(row["events"], passing)
    if passing and (
        row["peak_bytes"] >= row["limit_bytes"]
        or not row["keeper_verified"]
        or not row["populated"]
    ):
        raise ValueError("Actual aggregate exhausted or lost its keeper.")


def receipt_payload(
    manifest: dict[str, Any], parent: Any, roles: dict[str, Any]
) -> dict[str, Any]:
    """Build the fixed non-secret actual measurement envelope.

    :param manifest: Authenticated source/case/owner/profile identity.
    :param parent: Actual parent counters, or None when unavailable.
    :param roles: Actual per-role counters or closed unavailable observations.
    :return: Public projection requiring validation before admission.
    """
    return {
        "format": "mimir-measured-resources-v1",
        "resource_profile": "aggregate1024",
        "source_revision": manifest["source_revision"],
        "control_revision": manifest["control_revision"],
        "nonce": manifest["nonce"],
        "case": selected_case(manifest).case,
        "suite_phase": selected_case(manifest).phase,
        "images": IMAGES,
        "proof_hashes": PROOF_FILES,
        "parent": parent,
        "roles": roles,
        "status": "FAILED",
        "full_saga_accepted": False,
    }


def checked_receipt(
    raw: bytes, manifest: dict[str, Any], passing: bool = True
) -> dict[str, Any]:
    """Admit only exact canonical bytes and the closed source/case-bound schema.

    :param raw: Actual receipt bytes, never merely a parsed projection.
    :param manifest: Authenticated declaration for this fresh lifecycle.
    :param passing: Require all measured roles and positive headroom.
    :return: Safe exact closed payload.
    :raises ValueError: Hidden data, schema, identity or measurement differs.
    """
    if not isinstance(raw, bytes) or len(raw) > 65536:
        raise ValueError("Bounded exact resource bytes required.")
    record = json.loads(raw)
    if not isinstance(record, dict) or record.get("full_saga_accepted") is not False:
        raise ValueError("Closed resource object cannot claim full Saga acceptance.")
    expected = receipt_payload(manifest, record.get("parent"), record.get("roles"))
    expected["status"] = record.get("status")
    if (
        canonical(record) != raw
        or record != expected
        or record["status"] not in {"FAILED", "VERIFIED"}
    ):
        raise ValueError("Canonical exact resource receipt required.")
    validate_images(manifest)
    checked_identity(record)
    validate_measurements(record, passing or record["status"] == "VERIFIED")
    return record


def validate_measurements(record: dict[str, Any], passing: bool) -> None:
    """Require all actual roles and the concurrent parent for successful acceptance.

    :param record: Closed source/case-bound projection.
    :param passing: Require complete successful real measurements.
    :return: None after safe typed observations validate.
    :raises ValueError: Any shape, actual failure or acceptance fact differs.
    """
    roles = record["roles"]
    if not isinstance(roles, dict) or set(roles) != set(CAPS):
        raise ValueError("All three explicit role observation slots required.")
    for role, row in roles.items():
        checked_role(row, role, passing)
    if record["parent"] is not None:
        checked_parent(record["parent"], passing)
    if passing and (record["status"] != "VERIFIED" or record["parent"] is None):
        raise ValueError("Complete actual resource proof required.")


def checked_events(events: dict[str, Any], passing: bool) -> None:
    """Validate closed finite kernel counters, retaining actual failed events.

    :param events: Actual memory.events dictionary.
    :param passing: Require zero max/OOM/kill events.
    :return: None after typed bounded event validation.
    :raises ValueError: Schema, integer bounds or required headroom differs.
    """
    if not isinstance(events, dict) or any(
        type(value) is not int or not 0 <= value < 2**64 for value in events.values()
    ):
        raise ValueError("Finite actual event counters required.")
    parse_events([f"{key} {value}" for key, value in events.items()])
    if passing and any(
        events.get(key, 0) for key in ("max", "oom", "oom_kill", "oom_group_kill")
    ):
        raise ValueError("Actual cgroup exhaustion prevents acceptance.")


def memory_shape(row: dict[str, Any], role: str) -> None:
    """Check only safe closed role types/caps, allowing numeric failed evidence.

    :param row: Actual memory observation.
    :param role: Fixed role.
    :return: None after closed bounded numerical validation.
    :raises ValueError: Schema, types or actual cap differs.
    """
    keys = {"role", "peak_bytes", "limit_bytes", "events"}
    if role == "browser":
        keys.add("driver_passed")
    if not isinstance(row, dict) or set(row) != keys or row.get("role") != role:
        raise ValueError("Closed actual role memory measurement required.")
    if any(
        type(row[key]) is not int or not 0 < row[key] < 2**64
        for key in ("peak_bytes", "limit_bytes")
    ):
        raise ValueError("Finite actual memory counters required.")
    if row["limit_bytes"] != CAPS[role] * MIB:
        raise ValueError("Actual enforced role memory cap differs.")


def parent_shape(row: dict[str, Any]) -> None:
    """Check the exact parent schema and finite actual hardcap/swap counters.

    :param row: Actual aggregate observation.
    :return: None after closed bounded values validate.
    :raises ValueError: Any key, type, enforced limit or swap differs.
    """
    if not isinstance(row, dict) or set(row) != _PARENT_NUMERIC | {
        "events",
        "populated",
        "keeper_verified",
    }:
        raise ValueError("Closed actual parent counters required.")
    if any(
        type(row[key]) is not int or not 0 <= row[key] < 2**64
        for key in _PARENT_NUMERIC
    ):
        raise ValueError("Finite actual parent counters required.")
    if (
        row["limit_bytes"] != 1024 * MIB
        or row["swap_current_bytes"] != 0
        or row["swap_limit_bytes"] != 0
        or not 0 <= row["current_bytes"] <= row["peak_bytes"]
        or row["peak_bytes"] <= 0
        or type(row["populated"]) is not bool
        or type(row["keeper_verified"]) is not bool
    ):
        raise ValueError("Actual parent hardcap/swap/keeper shape differs.")


def checked_role(row: dict[str, Any], role: str, passing: bool) -> None:
    """Validate exact actual Docker and ancestry flags without exporting raw state.

    :param row: Safe per-role observation or explicit unavailable slot.
    :param role: Fixed actual role.
    :param passing: Require success and complete membership.
    :return: None after closed numerical/boolean validation.
    :raises ValueError: Actual failures or unknown observations cannot pass.
    """
    if row == {"status": "UNAVAILABLE"} and not passing:
        return
    if (
        not isinstance(row, dict)
        or set(row) != {"memory", "oom_killed", "restarts", "member_verified"}
        or type(row["oom_killed"]) is not bool
        or type(row["restarts"]) is not int
        or not 0 <= row["restarts"] <= 2147483647
        or type(row["member_verified"]) is not bool
    ):
        raise ValueError("Closed actual Docker observations required.")
    if row["memory"] == {"status": "UNAVAILABLE"} and not passing:
        return
    checked_memory(row["memory"], role, passing)
    if passing and (row["oom_killed"] or row["restarts"] or not row["member_verified"]):
        raise ValueError("Actual Docker exhaustion or membership failure.")


def proof_semantics(measured: dict[str, Any], identity: dict[str, Any]) -> None:
    """Validate the successful immutable proof's actual source/profile semantics.

    :param measured: Original successful core benchmark result.
    :param identity: Original source/image declaration.
    :return: None only for the fixed measured tuple and all actual role counters.
    :raises ValueError: Any successful measurement fact differs.
    """
    if (
        identity["source_revision"] != SOURCE
        or identity["runner_revision"] != RUNNER
        or identity["images"] != IMAGES
        or measured["measurement"] != "SUCCESS"
        or measured["cleanup"] != "SUCCESS"
        or measured["export"] != "SUCCESS"
        or measured["private_root_removed"] is not True
        or measured["resource_profile"] != "aggregate1024"
        or measured["aggregate_members"] != {role: True for role in CAPS}
    ):
        raise ValueError("Successful source-bound aggregate measurement required.")
    proof_measurements(measured)


def proof_measurements(measured: dict[str, Any]) -> None:
    """Require all three real measurements and the exact tested resource envelope.

    :param measured: Original immutable successful benchmark result.
    :return: None only after actual measured headroom and fixed envelope validate.
    :raises ValueError: Profile envelope, roles or actual failures differ.
    """
    if (
        measured["envelope_mib"] != CAPS
        or measured["host_reserve_mib"] != 256
        or set(measured["observations"]["roles"]) != set(CAPS)
    ):
        raise ValueError("Complete measured fixed resource envelope required.")
    checked_parent(measured["aggregate"])
    for role, row in measured["observations"]["roles"].items():
        checked_memory(row["memory"], role)
        if row["docker"]["oom_killed"] is not False or row["docker"]["restarts"] != 0:
            raise ValueError("Measured role exhausted or restarted.")


def checked_identity(record: dict[str, Any]) -> None:
    """Require typed exact source/control and fresh ownership identity.

    :param record: Closed safe lifecycle resource projection.
    :return: None after exact source/nonce syntax validates.
    :raises ValueError: Source/owner identity differs.
    """
    if (
        not isinstance(record["nonce"], str)
        or not re.fullmatch(r"[a-f0-9]{32}", record["nonce"])
        or not isinstance(record["control_revision"], str)
        or not re.fullmatch(r"[a-f0-9]{40}", record["control_revision"])
    ):
        raise ValueError("Exact actual resource source/owner binding required.")


def prepared_identity(plan: dict[str, Any]) -> dict[str, Any]:
    """Bind prepare's actual web build to the only tested companion images.

    :param plan: Actual reviewed source/build/web identity.
    :return: Expected measured full immutable image tuple for proof validation.
    """
    return {
        **plan,
        **{role + "_image": image for role, image in IMAGES.items() if role != "web"},
    }


def bundle_proof(directory: Path, manifest: dict[str, Any]) -> dict[str, bytes]:
    """Bundle fixed named exact proof bytes only when explicitly selected.

    :param directory: Owned prepared case directory.
    :param manifest: Authenticated full runtime identity.
    :return: Exact validated proof members or unchanged empty default.
    :raises ValueError: Actual immutable proof differs.
    """
    if not selected(manifest):
        return {}
    validate_files(directory, manifest)
    return {name: (directory / name).read_bytes() for name in PROOF_FILES}
