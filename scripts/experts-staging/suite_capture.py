"""Bounded real capture readiness, paired native frames and private failed originals."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from playwright.sync_api import Locator, Page

from suite_pixels import png_nonuniform


def wait_for_paint(page: Page) -> None:
    """Wait for three real stable rendered geometry frames without UI mutation.

    :param page: Actual native browser document at its genuine interaction state.
    :return: None after actual viewport/scroll/body geometry and fonts settle.
    :raises AssertionError: The browser does not reach stable paint readiness.
    """
    stable = page.evaluate("""async () => {
        await document.fonts.ready;
        let previous='', stable=0;
        const deadline=performance.now()+1500;
        while(performance.now()<deadline){
            await new Promise(requestAnimationFrame);
            const box=document.body.getBoundingClientRect();
            const now=JSON.stringify([scrollY,innerWidth,innerHeight,box.x,box.y,box.width,box.height]);
            stable=now===previous?stable+1:0;previous=now;
            if(stable>=3)return true;
        }
        return false;
    }""")
    assert stable, "Actual rendered capture geometry did not settle."


def acquire_pair(
    page: Page,
    output: Path,
    case: str,
    step: str,
    fonts: list[str],
    mask: list[Locator],
) -> bool:
    """Acquire original document and native viewport with actual pixel admission.

    :param page: Actual settled source application.
    :param output: Exclusive owned output root.
    :param case: True fixed UAT case.
    :param step: Fixed source step plus attempt1or2.
    :param fonts: Actual loaded font observations.
    :param mask: Existing privacy-only native screenshot masks.
    :return: True only when both actual acquisitions are nonuniform.
    :raises ValueError: Corrupt or aliased acquisition.
    """
    valid = True
    original = page.evaluate("({x:scrollX,y:scrollY})")
    try:
        for full_page in (False, True):
            if (
                full_page
                and not page.get_by_test_id("finalize-confirm-modal").is_visible()
            ):
                page.evaluate("window.scrollTo({top:0,left:0,behavior:'instant'})")
            wait_for_paint(page)
            valid = (
                _acquire_frame(page, output, case, step, fonts, mask, full_page)
                and valid
            )
    finally:
        page.evaluate(
            "position=>window.scrollTo({left:position.x,top:position.y,behavior:'instant'})",
            original,
        )
        wait_for_paint(page)
    return valid


def _acquire_frame(
    page: Page,
    output: Path,
    case: str,
    step: str,
    fonts: list[str],
    mask: list[Locator],
    full_page: bool,
) -> bool:
    """Retain exactly one actual nonuniform frame or its untouched private rejection.

    :param page: Genuine current page.
    :param output: Owned output root.
    :param case: Fixed true case.
    :param step: Fixed source step and attempt.
    :param fonts: Actual loaded font observations.
    :param mask: Existing privacy masks.
    :param full_page: Actual acquisition kind.
    :return: Whether actual pixels pass nonuniform admission.
    :raises ValueError: Existing or malformed acquisition.
    """
    stem = f"saga-{case}-{step}" + ("" if full_page else "-viewport")
    target = output / "screenshots" / (stem + ".png")
    if target.exists() or target.is_symlink():
        raise ValueError("Actual acquired pixels cannot be overwritten.")
    page.screenshot(path=str(target), full_page=full_page, mask=mask)
    if not png_nonuniform(target):
        quarantine_blank(output, target, case)
        return False
    _record(page, output, case, step, fonts, stem, full_page, target)
    return True


def _record(
    page: Page,
    output: Path,
    case: str,
    step: str,
    fonts: list[str],
    stem: str,
    full_page: bool,
    target: Path,
) -> None:
    """Retain actual pixel/viewport/scroll facts without rewriting image bytes.

    :param page: Actual current native page.
    :param output: Owned output root.
    :param case: True lane.
    :param step: Actual source-owned step/attempt.
    :param fonts: Actual observed loaded fonts.
    :param stem: Exact source-owned acquisition basename.
    :param full_page: Whether the acquired image is the whole actual document.
    :param target: Original actual PNG file.
    :return: None after exclusive typed metadata creation.
    """
    record = {
        "case": case,
        "step": step,
        "path": urlsplit(page.url).path,
        "viewport": page.viewport_size,
        "fonts": fonts,
        "secure_context": True,
        "capture_kind": "full_document" if full_page else "native_viewport",
        "capture_scroll_y": page.evaluate("scrollY"),
        "pixels_nonuniform": True,
        "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
    }
    with (output / (stem + ".json")).open("x") as stream:
        json.dump(record, stream, indent=2)


def quarantine_blank(output: Path, original: Path, case: str) -> None:
    """Preserve a rejected actual acquisition privately with a safe original hash.

    :param output: Owned invocation output.
    :param original: Actual uniform PNG, never modified.
    :param case: True source case.
    :return: None after private original retention and safe rejection receipt.
    :raises ValueError: A prior original or unsafe receipt would be replaced.
    """
    folder = output / "private/rejected-captures"
    folder.mkdir(mode=0o700, exist_ok=True)
    destination = folder / original.name
    if destination.exists() or destination.is_symlink():
        raise ValueError("Rejected original acquisition cannot be replaced.")
    digest = hashlib.sha256(original.read_bytes()).hexdigest()
    original.rename(destination)
    os.chmod(destination, 0o600)
    receipt = output / "capture-rejections.json"
    if receipt.is_symlink():
        raise ValueError("Actual rejection receipt cannot be aliased.")
    record: dict[str, Any] = (
        json.loads(receipt.read_text())
        if receipt.exists()
        else {
            "case": case,
            "rejected_captures": 0,
            "rejected_capture_sha256": [],
            "blank_originals_private": True,
        }
    )
    record["rejected_captures"] += 1
    record["rejected_capture_sha256"].append(digest)
    receipt.write_text(json.dumps(record, indent=2))
