"""Strict numeric cgroup-v2 observations; no Docker, application or cloud access."""

from __future__ import annotations

import re
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
