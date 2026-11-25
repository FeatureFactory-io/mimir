"""Run the genuine suite dispatch and sample its own cgroup before PID1 exits."""

from __future__ import annotations

import json
import os
from pathlib import Path

import suite_browser
from benchmark_metrics import read_memory, require_headroom
from resource_profile import MIB, canonical, selected
from suite_contract import selected_case


def main() -> None:
    """Call the real suite and retain its original failure if sampling also fails.

    :return: None only after genuine dispatch and measurement pass.
    :raises Exception: Original dispatch failure remains the top-level exception.
    """
    manifest = json.loads(Path("/runtime/run.json").read_text())
    if not selected(manifest):
        raise ValueError("Measured observer requires explicit aggregate profile.")
    original: Exception | None = None
    try:
        suite_browser.main()
    except Exception as error:
        original = error
        raise
    finally:
        try:
            observe(manifest, original is None)
        except Exception as measurement_error:
            if original is not None:
                raise original from measurement_error
            raise


def observe(manifest: dict, passed: bool) -> None:
    """Write canonical private numeric evidence before the real process exits.

    :param manifest: Source/case/nonce-bound mounted invocation.
    :param passed: Actual unchanged suite dispatch outcome.
    :return: None after actual counters are retained and checked.
    :raises Exception: Unsafe output path, unavailable counters or exhaustion.
    """
    memory = read_memory(Path("/sys/fs/cgroup"), "browser", 768 * MIB)
    memory["driver_passed"] = passed
    row = {key: manifest[key] for key in ("nonce", "source_revision")}
    row.update(
        case=selected_case(manifest).case,
        suite_phase=selected_case(manifest).phase,
        memory=memory,
    )
    private = Path("/output/private")
    private.mkdir(mode=0o700, exist_ok=True)
    if private.is_symlink() or private.resolve() != private:
        raise ValueError("Actual owned private observation directory required.")
    descriptor = os.open(
        private / "resource-browser-memory.json",
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
    )
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(canonical(row))
    require_headroom(memory)


if __name__ == "__main__":
    main()
