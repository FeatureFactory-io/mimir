"""Paired real guest viewport acquisitions; never modify application DOM or styles."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from playwright.sync_api import Page

from suite_capture import wait_for_paint

_STEPS = frozenset(
    {
        "G01-design",
        "G01-detail",
        "G02-list-hover",
        "G02-list-keyboard",
        "G02-detail-hover",
        "G02-detail-keyboard",
    }
)


def capture_viewport(page: Page, output: Path, step: str) -> dict[str, Any]:
    """Acquire actual native viewport pixels at only six reviewed guest states.

    :param page: Genuine actual guest document after its original full-page capture.
    :param output: Existing owned exact-viewport acquisition directory.
    :param step: Source-controlled guest step.
    :return: Actual viewport metadata, or empty for a non-selected capture step.
    :raises ValueError: An existing acquisition would be overwritten.
    """
    if step not in _STEPS:
        return {}
    name = step + "-viewport.png"
    target = output / name
    if target.exists() or target.is_symlink():
        raise ValueError("Original native viewport capture cannot be replaced.")
    page.wait_for_function(
        "!document.getAnimations().some(a=>a.playState==='running' && a.effect?.getTiming().iterations!==Infinity)"
    )
    wait_for_paint(page)
    scroll = page.evaluate("scrollY")
    geometry = _geometry(page)
    page.screenshot(path=str(target), full_page=False)
    assert page.evaluate("scrollY") == scroll
    record = {
        "case": "guest-public",
        "step": step,
        "viewport": page.viewport_size,
        "capture_kind": "native_viewport",
        "capture_scroll_y": scroll,
        "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
        "document_width": page.evaluate("document.documentElement.scrollWidth"),
        **geometry,
    }
    with (output / (name + ".json")).open("x") as stream:
        json.dump(record, stream, indent=2)
    return record


def _geometry(page: Page) -> dict[str, Any]:
    """Read genuine navbar and optional tooltip boxes without changing any state.

    :param page: Actual current native browser state.
    :return: Actual numeric geometry and safe tooltip presence.
    """
    tooltip = page.get_by_role("tooltip")
    return {
        "navbar_geometry": page.get_by_test_id("realm-navbar").bounding_box(),
        "tooltip_geometry": tooltip.bounding_box() if tooltip.count() else None,
    }
