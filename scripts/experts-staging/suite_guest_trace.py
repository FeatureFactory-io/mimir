"""Seven finite actual guest trace chunks; every native trace setting is retained."""

from __future__ import annotations

import json
import os
from pathlib import Path

import saga_browser as shared
from saga_guest import VIEWPORTS
from saga_trace import redact_trace


def original_path(output: Path, width: int, height: int) -> Path:
    """Resolve only one exact required viewport's private original.

    :param output: Owned browser evidence root.
    :param width: Exact IA width.
    :param height: Exact IA height.
    :return: Closed untouched original trace path.
    :raises ValueError: Unknown viewport dimensions.
    """
    if (width, height) not in VIEWPORTS:
        raise ValueError("Exact guest IA viewport required.")
    return output / "private" / f"guest-public-{width}-{height}-trace-original.zip"


def finish_guest(output: Path, successful: bool) -> None:
    """Publish bounded derivatives of all seven actual viewport chunks.

    :param output: Actual closed context's acquisition root.
    :param successful: Whether every genuine guest action and screen succeeded.
    :return: None after safe publication or complete failed-media quarantine.
    :raises ValueError: Original bound, privacy, topology or provenance differs.
    """
    values = shared._PRIVATE_VALUES.get() or set()
    shared.write_result("private/captured-secrets.json", {"values": sorted(values)})
    os.chmod(output / "private/captured-secrets.json", 0o600)
    if not successful:
        shared.quarantine_media()
        return
    destination = output / "traces"
    destination.mkdir(mode=0o700)
    try:
        for width, height in VIEWPORTS:
            _publish_chunk(output, width, height, values)
    except Exception:
        shared.quarantine_media()
        raise


def _publish_chunk(output: Path, width: int, height: int, values: set[str]) -> None:
    """Retain original resources and explicit per-viewport derivative provenance.

    :param output: Owned root.
    :param width: Exact actual viewport width.
    :param height: Exact actual viewport height.
    :param values: Actual private observations retained only in memory.
    :return: None after all-member redaction and byte-identical image proof.
    :raises ValueError: Any chunk is unsafe or exceeds the retained finite bound.
    """
    stem = f"guest-public-{width}-{height}"
    original = original_path(output, width, height)
    result = redact_trace(original, output / "traces" / (stem + ".zip"), values)
    result.update(
        original_retention="private_until_verified_owned_cleanup",
        viewport={"width": width, "height": height},
    )
    target = output / "traces" / (stem + ".provenance.json")
    with target.open("x") as stream:
        json.dump(result, stream, indent=2)
