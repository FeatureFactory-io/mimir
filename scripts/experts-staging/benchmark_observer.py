"""Observe the unchanged real browser driver's cgroup immediately before exit."""

from __future__ import annotations

import json
import os
from pathlib import Path

import browser
from benchmark_metrics import (
    browser_failure,
    browser_memory_bytes,
    observer_memory_choice,
    read_memory,
    require_headroom,
    write_browser_diagnostic,
)


def main() -> None:
    """Run actual browser.main and retain its failure while measuring before exit.

    :return: None only when the genuine driver and measured headroom pass.
    :raises Exception: Original browser failure, or unavailable/unsafe counters.
    """
    memory_mib = observer_memory_choice()
    passed = False
    try:
        browser.main()
        passed = True
    except Exception as error:
        write_diagnostic(error)
        raise
    finally:
        observe(passed, memory_mib)


def observe(driver_passed: bool, memory_mib: int = 512) -> None:
    """Save only actual numeric kernel counters, without environment or diagnostics.

    :param driver_passed: Whether unchanged browser.main returned normally.
    :param memory_mib: Exact explicit CI choice, also enforced by Docker.
    :return: None after measured positive headroom, preserving failed-driver status.
    :raises Exception: Missing metrics or actual memory exhaustion.
    """
    record = read_memory(
        Path("/sys/fs/cgroup"), "browser", browser_memory_bytes(memory_mib)
    )
    record["driver_passed"] = driver_passed
    path = Path("/output/browser-memory.json")
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w") as stream:
        json.dump(record, stream, indent=2)
    require_headroom(record)


def write_diagnostic(
    error: Exception, destination: Path = Path("/output/browser-diagnostic.json")
) -> None:
    """Retain only fixed exception class and reviewed browser source frames.

    :param error: Actual browser.main exception, never its message or arguments.
    :param destination: Explicit owned test path or unchanged runtime receipt path.
    :return: None after one exclusive safe observer receipt exists.
    :raises OSError: Diagnostic cannot be recorded safely.
    """
    record = browser_failure(error, Path(browser.__file__))
    write_browser_diagnostic(destination, record)


if __name__ == "__main__":
    main()
