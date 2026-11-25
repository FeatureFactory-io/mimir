"""Strict numeric cgroup-v2 observations; no Docker, application or cloud access."""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import traceback
from pathlib import Path
from typing import Any

_EVENT_KEYS = {
    "low",
    "high",
    "max",
    "oom",
    "oom_kill",
    "oom_group_kill",
    "sock_throttled",
}
_REQUIRED_EVENTS = {"low", "high", "max", "oom", "oom_kill"}


_SAFE_CLASSES = {
    "ValueError",
    "RuntimeError",
    "TimeoutError",
    "OSError",
    "FileNotFoundError",
    "PermissionError",
    "JSONDecodeError",
    "AssertionError",
    "TypeError",
    "Error",
    "TargetClosedError",
    "Exception",
}
_BROWSER_FUNCTIONS = {
    "loaded_fonts",
    "capture",
    "assert_public_body",
    "capture_observation",
    "write_json",
    "capture_guest",
    "assert_design_names",
    "real_guest_clipboard",
    "observe_receipts",
    "prepare_real_clipboard",
    "restrict_requests",
    "main",
    "run_readiness",
    "perform_readiness",
}
DEFAULT_BROWSER_MEMORY_MIB = 512
BROWSER_MEMORY_CHOICES = (512, 768)
MAX_DIAGNOSTIC_BYTES = 16 * 1024
_REASONS = {
    "Unsupported diagnostic browser memory choice.": "BROWSER_MEMORY_CHOICE_REJECTED",
    "Selected CI caps plus host reserve exceed fresh available memory.": "CI_ENVELOPE_RESERVE_REJECTED",
    "Selected browser plus host reserve exceed fresh available memory.": "CI_BROWSER_RESERVE_REJECTED",
    "Browser diagnostic bytes are not canonical.": "BROWSER_DIAGNOSTIC_BYTES_REJECTED",
    "Browser diagnostic bytes exceed the fixed bound.": "BROWSER_DIAGNOSTIC_SIZE_REJECTED",
    "Unknown evidence directory.": "EXPORT_DIRECTORY_REJECTED",
    "Unknown or linked evidence file.": "EXPORT_MEMBER_REJECTED",
    "Linked evidence cannot be exported.": "EXPORT_LINK_REJECTED",
    "An actual public evidence directory is required.": "EXPORT_ROOT_REJECTED",
    "Evidence exceeds the fixed public export bound.": "EXPORT_SIZE_REJECTED",
    "The host result cannot originate from a container.": "EXPORT_HOST_RESULT_REJECTED",
    "An actual unlinked public destination is required.": "EXPORT_DESTINATION_REJECTED",
    "Actual role measurement is incomplete.": "ROLE_MEASUREMENT_INCOMPLETE",
    "All three role observations are required.": "ROLE_OBSERVATIONS_INCOMPLETE",
    "Actual workload exhausted the measured memory envelope.": "MEMORY_HEADROOM_REJECTED",
    "Actual cgroup peak/limit differs from the approved cap.": "CGROUP_PEAK_OR_LIMIT_REJECTED",
    "Missing cgroup-v2 memory counters.": "CGROUP_COUNTERS_MISSING",
    "Unexpected or duplicated cgroup memory event.": "CGROUP_EVENT_REJECTED",
    "Missing required cgroup-v2 memory events.": "CGROUP_EVENTS_MISSING",
    "A finite unsigned kernel counter is required.": "CGROUP_COUNTER_REJECTED",
    "Typed expected container role and memory cap required.": "CGROUP_ROLE_OR_CAP_REJECTED",
    "Bounded actual cgroup counters required.": "CGROUP_INPUT_REJECTED",
    "An absolute unlinked actual input file is required.": "INPUT_PATH_REJECTED",
    "Input must be an unlinked bounded regular file.": "INPUT_FILE_REJECTED",
    "Unexpected browser metric fields.": "BROWSER_METRIC_FIELDS_REJECTED",
    "Typed browser observation required.": "BROWSER_METRIC_TYPES_REJECTED",
    "Only actual numeric browser counters are accepted.": "BROWSER_COUNTER_TYPES_REJECTED",
    "Actual Docker observation fields differ.": "DOCKER_FIELDS_REJECTED",
    "Actual Docker limits or hardening failed.": "DOCKER_LIMITS_REJECTED",
    "Actual Docker privilege guard failed.": "DOCKER_PRIVILEGES_REJECTED",
    "Actual browser exited unsuccessfully.": "BROWSER_EXIT_REJECTED",
    "Actual application/database stopped unexpectedly.": "SERVICE_EXIT_REJECTED",
    "The actual browser driver did not pass.": "BROWSER_DRIVER_REJECTED",
    "Browser diagnostic fields are invalid.": "BROWSER_DIAGNOSTIC_REJECTED",
    "Browser source frame is invalid.": "BROWSER_FRAME_REJECTED",
}
_REASON_ENUMS = set(_REASONS.values()) | {
    "UNCLASSIFIED",
    "FILE_UNAVAILABLE",
    "PERMISSION_DENIED",
    "JSON_INVALID",
    "OBSERVATION_REJECTED",
}
_DOCKER_NUMBERS = {
    "exit_code",
    "restarts",
    "memory_bytes",
    "swap_bytes",
    "nano_cpus",
    "pids",
}
_DOCKER_BOOLEANS = {"oom_killed", "running", "read_only"}


def parse_memory(text: str, role: str, limit_bytes: int) -> dict[str, Any]:
    """Validate one actual finite cgroup-v2 observation.

    :param text: Peak, maximum and memory.events lines from one container.
    :param role: Explicit web, db or browser role.
    :param limit_bytes: Expected actual Docker memory limit.
    :return: Numeric measurement, never a guessed peak.
    :raises ValueError: Missing, malformed or inconsistent cgroup observations.
    """
    if role not in {"web", "db", "browser"} or type(limit_bytes) is not int:
        raise ValueError("Typed expected container role and memory cap required.")
    if not isinstance(text, str) or len(text) > 4096:
        raise ValueError("Bounded actual cgroup counters required.")
    lines = text.splitlines()
    if len(lines) < 2:
        raise ValueError("Missing cgroup-v2 memory counters.")
    peak, maximum = (unsigned_integer(value) for value in lines[:2])
    if not 0 < peak <= maximum == limit_bytes:
        raise ValueError("Actual cgroup peak/limit differs from the approved cap.")
    events = parse_events(lines[2:])
    return {"role": role, "peak_bytes": peak, "limit_bytes": maximum, "events": events}


def unsigned_integer(value: str) -> int:
    """Accept only bounded unsigned decimal kernel counters.

    :param value: Exact numeric line, e.g. ``1024``.
    :return: Nonnegative integer.
    :raises ValueError: Unlimited, negative, oversized or nonnumeric input.
    """
    if not re.fullmatch(r"[0-9]{1,20}", value):
        raise ValueError("A finite unsigned kernel counter is required.")
    return int(value)


def parse_events(lines: list[str]) -> dict[str, int]:
    """Reject missing, duplicated or unknown kernel event records.

    :param lines: Actual memory.events lines.
    :return: Exact known numeric counters.
    :raises ValueError: Any event record is malformed or incomplete.
    """
    result = {}
    for line in lines:
        parts = line.split()
        if len(parts) != 2 or parts[0] not in _EVENT_KEYS or parts[0] in result:
            raise ValueError("Unexpected or duplicated cgroup memory event.")
        result[parts[0]] = unsigned_integer(parts[1])
    if not _REQUIRED_EVENTS <= result.keys():
        raise ValueError("Missing required cgroup-v2 memory events.")
    return result


def read_memory(group: Path, role: str, limit_bytes: int) -> dict[str, Any]:
    """Read actual kernel counters before the container process exits.

    :param group: The container's own cgroup-v2 directory.
    :param role: Explicit browser, db or web role.
    :param limit_bytes: Approved process memory cap in bytes.
    :return: Strict measured counters.
    :raises OSError: Kernel counters are unavailable; no fallback is invented.
    :raises ValueError: Kernel counters are invalid.
    """
    values = [
        (group / name).read_text().strip()
        for name in ("memory.peak", "memory.max", "memory.events")
    ]
    return parse_memory("\n".join(values), role, limit_bytes)


def require_headroom(record: dict[str, Any]) -> None:
    """Reject exhaustion or OOM while retaining original measured counters.

    :param record: Validated numeric cgroup measurement.
    :return: None after positive headroom and zero exhaustion events.
    :raises ValueError: A cap was reached or an OOM event occurred.
    """
    if record["peak_bytes"] >= record["limit_bytes"] or any(
        record["events"].get(key, 0)
        for key in ("max", "oom", "oom_kill", "oom_group_kill")
    ):
        raise ValueError("Actual workload exhausted the measured memory envelope.")


def failure_reason(error: Exception) -> str:
    """Classify closed known errors without exporting arbitrary exception text.

    :param error: Actual failed guard.
    :return: Fixed reason enum, including unclassified fallback.
    """
    if isinstance(error, FileNotFoundError):
        return "FILE_UNAVAILABLE"
    if isinstance(error, PermissionError):
        return "PERMISSION_DENIED"
    if type(error).__name__ == "JSONDecodeError":
        return "JSON_INVALID"
    if type(error) in {ValueError, RuntimeError} and len(error.args) == 1:
        value = error.args[0]
        if isinstance(value, str):
            return _REASONS.get(value, "UNCLASSIFIED")
    return "UNCLASSIFIED"


def host_observations(measured: dict[str, Any]) -> dict[str, Any]:
    """Retain only checked numeric role observations in the independent host result.

    :param measured: Actual role measurements before cleanup.
    :return: Closed numeric/boolean fields and fixed rejection classifications.
    """
    roles = measured.get("roles", {})
    if not isinstance(roles, dict):
        return {"reason": "OBSERVATION_REJECTED"}
    return {
        "roles": {
            role: host_role(roles.get(role, {}), role)
            for role in ("db", "web", "browser")
        },
        "sum_of_individual_peaks_is_not_simultaneous": True,
    }


def browser_failure(error: Exception, source: Path) -> dict[str, Any]:
    """Capture only whitelisted actual browser source function/line traceback frames.

    :param error: Genuine browser exception.
    :param source: Exact reviewed browser.py path.
    :return: Safe class and bounded known frames, never messages or locals.
    """
    kind = type(error).__name__
    ranges = browser_ranges(source)
    frames = [
        {"function": item.name, "line": item.lineno}
        for item in traceback.extract_tb(error.__traceback__)
        if Path(item.filename).resolve() == source.resolve()
        and item.name in ranges
        and ranges[item.name][0] <= item.lineno <= ranges[item.name][1]
    ]
    return {
        "status": "FAILED",
        "exception_class": kind if kind in _SAFE_CLASSES else "Exception",
        "source_frames": frames[-20:],
        "private_output_exported": False,
    }


def validate_browser_failure(record: dict[str, Any]) -> dict[str, Any]:
    """Reject forged or extended browser diagnostics before host publication.

    :param record: Parsed original observer diagnostic.
    :return: Independently validated closed diagnostic.
    :raises ValueError: Extra fields, unknown frames or invalid class/line values.
    """
    expected = {"status", "exception_class", "source_frames", "private_output_exported"}
    if (
        not isinstance(record, dict)
        or set(record) != expected
        or record["status"] != "FAILED"
        or not isinstance(record["exception_class"], str)
        or record["exception_class"] not in _SAFE_CLASSES
        or record["private_output_exported"] is not False
        or not isinstance(record["source_frames"], list)
        or len(record["source_frames"]) > 20
    ):
        raise ValueError("Browser diagnostic fields are invalid.")
    frames = [validate_browser_frame(row) for row in record["source_frames"]]
    return {
        "status": "FAILED",
        "exception_class": record["exception_class"],
        "source_frames": frames,
        "private_output_exported": False,
    }


def validate_browser_frame(row: dict[str, Any]) -> dict[str, Any]:
    """Admit only a known browser function and bounded positive source line.

    :param row: Original frame object.
    :return: Safe known function and numeric line.
    :raises ValueError: Unknown function, extra fields or invalid line.
    """
    if (
        not isinstance(row, dict)
        or set(row) != {"function", "line"}
        or not isinstance(row["function"], str)
        or row["function"] not in _BROWSER_FUNCTIONS
        or type(row["line"]) is not int
        or not 0 < row["line"] <= 1000
    ):
        raise ValueError("Browser source frame is invalid.")
    ranges = browser_ranges(Path(__file__).with_name("browser.py"))
    if (
        row["function"] not in ranges
        or not ranges[row["function"]][0] <= row["line"] <= ranges[row["function"]][1]
    ):
        raise ValueError("Browser source frame is invalid.")
    return {"function": row["function"], "line": row["line"]}


def host_role(row: dict[str, Any], role: str) -> dict[str, Any]:
    """Project one role onto strict safe numeric and fixed-class observations.

    :param row: Actual curated measurement or failed-measurement object.
    :param role: Fixed driver-selected role.
    :return: Safe copy with no arbitrary strings, fields or exception prose.
    """
    if not isinstance(row, dict):
        return {"measurement_reason": "OBSERVATION_REJECTED"}
    result = {}
    for key in ("measurement_exception", "measurement_reason"):
        value = row.get(key)
        if isinstance(value, str):
            allowed = _SAFE_CLASSES if key == "measurement_exception" else _REASON_ENUMS
            result[key] = value if value in allowed else "UNCLASSIFIED"
    if "docker" in row:
        result["docker"] = host_docker(row["docker"])
    if "memory" in row:
        try:
            result["memory"] = host_memory(row["memory"], role)
        except (ValueError, TypeError, KeyError):
            result["measurement_reason"] = "OBSERVATION_REJECTED"
    return result


def host_docker(row: dict[str, Any]) -> dict[str, Any]:
    """Omit all Docker strings and retain only bounded actual numeric/boolean state.

    :param row: Curated actual Docker inspection.
    :return: Actual typed safe fields; invalid or missing fields are never guessed.
    """
    if not isinstance(row, dict):
        return {}
    numbers = {
        key: row[key]
        for key in _DOCKER_NUMBERS
        if type(row.get(key)) is int and 0 <= row[key] < 2**64
    }
    booleans = {key: row[key] for key in _DOCKER_BOOLEANS if type(row.get(key)) is bool}
    return {**numbers, **booleans}


def host_memory(row: dict[str, Any], role: str) -> dict[str, Any]:
    """Independently revalidate already-parsed counters before host publication.

    :param row: Actual parsed metric record.
    :param role: Fixed expected role.
    :return: Strict role, finite counters and closed event names.
    :raises ValueError: Types, role or event keys differ.
    """
    if (
        not isinstance(row, dict)
        or row.get("role") != role
        or not isinstance(row.get("events"), dict)
    ):
        raise ValueError("Bounded actual cgroup counters required.")
    values = [row.get("peak_bytes"), row.get("limit_bytes"), *row["events"].values()]
    if any(type(value) is not int for value in values):
        raise ValueError("Only actual numeric browser counters are accepted.")
    events = "\n".join(f"{key} {value}" for key, value in row["events"].items())
    text = f"{row['peak_bytes']}\n{row['limit_bytes']}\n{events}"
    result = parse_memory(text, role, row["limit_bytes"])
    if type(row.get("driver_passed")) is bool:
        result["driver_passed"] = row["driver_passed"]
    return result


def browser_ranges(source: Path) -> dict[str, tuple[int, int]]:
    """Read exact reviewed browser function line ranges without importing Playwright.

    :param source: Actual reviewed browser.py source file.
    :return: Only known function names and actual bounded line ranges.
    :raises OSError: Actual source cannot be read; never guess a source frame.
    """
    tree = ast.parse(source.read_text())
    return {
        node.name: (node.lineno, node.end_lineno)
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name in _BROWSER_FUNCTIONS
        and node.end_lineno is not None
    }


def browser_diagnostic_bytes(record: dict[str, Any]) -> bytes:
    """Serialize only the exact closed schema into one canonical byte representation.

    :param record: Original safe observer failure projection.
    :return: ASCII JSON with sorted keys, fixed separators and one final newline.
    :raises ValueError: The original schema, class or source frame is invalid.
    """
    closed = validate_browser_failure(record)
    text = json.dumps(closed, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
    return (text + "\n").encode("ascii")


def parse_browser_diagnostic(data: bytes) -> dict[str, Any]:
    """Require exact canonical raw bytes, rejecting hidden or overwritten JSON data.

    :param data: Original observer file bytes, never a parsed projection alone.
    :return: Closed safe diagnostic only when every original byte is admitted.
    :raises ValueError: Oversized, invalid, duplicated or noncanonical JSON bytes.
    """
    if type(data) is not bytes or not 0 < len(data) <= MAX_DIAGNOSTIC_BYTES:
        raise ValueError("Browser diagnostic bytes exceed the fixed bound.")
    closed = validate_browser_failure(json.loads(data))
    if data != browser_diagnostic_bytes(closed):
        raise ValueError("Browser diagnostic bytes are not canonical.")
    return closed


def write_browser_diagnostic(path: Path, record: dict[str, Any]) -> None:
    """Write the actual observer's canonical bytes exclusively with private mode.

    :param path: New exact observer receipt destination.
    :param record: Closed failure record with no messages, args or locals.
    :return: None after the same canonical bytes required by export are written.
    :raises OSError: Existing destination or unsafe write.
    :raises ValueError: Diagnostic is invalid before any bytes are written.
    """
    data = browser_diagnostic_bytes(record)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(data)


def browser_memory_bytes(memory_mib: int) -> int:
    """Accept only default512 or explicit768 for the disposable CI experiment.

    :param memory_mib: Typed explicit diagnostic choice, never idle policy.
    :return: Exact enforced memory cap in bytes.
    :raises ValueError: Wrong type or unsupported cap.
    """
    if type(memory_mib) is not int or memory_mib not in BROWSER_MEMORY_CHOICES:
        raise ValueError("Unsupported diagnostic browser memory choice.")
    return memory_mib * 1024 * 1024


def observer_memory_choice(argv: list[str] | None = None) -> int:
    """Parse the observer's explicit closed cap without reading ambient environment.

    :param argv: Explicit unit arguments or actual observer process argv.
    :return: Default512 or explicit768, checked against the enforced cgroup later.
    :raises SystemExit: Unknown, missing or unsupported CLI arguments.
    """
    parser = argparse.ArgumentParser(description="Disposable CI browser observer")
    parser.add_argument(
        "--browser-memory-mib",
        type=int,
        choices=BROWSER_MEMORY_CHOICES,
        default=DEFAULT_BROWSER_MEMORY_MIB,
    )
    return parser.parse_args(argv).browser_memory_mib
