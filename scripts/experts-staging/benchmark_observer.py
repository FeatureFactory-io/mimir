"""Observe the unchanged real browser driver's cgroup immediately before exit."""

from __future__ import annotations

import json
import os
from pathlib import Path

import browser
from benchmark_metrics import read_memory, require_headroom

_LIMIT_BYTES = 512 * 1024 * 1024


def main() -> None:
    """Run actual browser.main and retain its failure while measuring before exit.

    :return: None only when the genuine driver and measured headroom pass.
    :raises Exception: Original browser failure, or unavailable/unsafe counters.
    """
    passed = False
    try:
        browser.main()
        passed = True
    finally:
        observe(passed)


def observe(driver_passed: bool) -> None:
    """Save only actual numeric kernel counters, without environment or diagnostics.

    :param driver_passed: Whether unchanged browser.main returned normally.
    :return: None after measured positive headroom, preserving failed-driver status.
    :raises Exception: Missing metrics or actual memory exhaustion.
    """
    record = read_memory(Path("/sys/fs/cgroup"), "browser", _LIMIT_BYTES)
    record["driver_passed"] = driver_passed
    path = Path("/output/browser-memory.json")
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w") as stream:
        json.dump(record, stream, indent=2)
    require_headroom(record)


if __name__ == "__main__":
    main()
