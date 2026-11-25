"""Bounded real capture readiness, paired native frames and private failed originals."""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
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
    page.wait_for_function(
        "!document.getAnimations().some(a=>a.playState==='running' && a.effect?.getTiming().iterations!==Infinity)"
    )
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
    folder, destination = _capture_paths(output, original)
    descriptor, record = _open_rejection(output / "capture-rejections.json", case)
    try:
        digest = _original_digest(original)
        if record["rejected_captures"] >= 128:
            raise ValueError("Bounded rejection count exceeded.")
        if not folder.exists():
            folder.mkdir(mode=0o700)
        _checked_directory(folder)
        if descriptor is None:
            descriptor = _open_regular(
                output / "capture-rejections.json",
                os.O_RDWR | os.O_CREAT | os.O_EXCL,
                16384,
            )
        _regular_descriptor(descriptor, 16384)
        original.rename(destination)
        os.chmod(destination, 0o600)
        updated = {
            "case": case,
            "rejected_captures": record["rejected_captures"] + 1,
            "rejected_capture_sha256": [*record["rejected_capture_sha256"], digest],
            "blank_originals_private": True,
        }
        _regular_descriptor(descriptor, 16384)
        _write_rejection(descriptor, updated)
    finally:
        if descriptor is not None:
            os.close(descriptor)


def _write_rejection(descriptor: int, record: dict[str, Any]) -> None:
    """Write all safe receipt bytes only through the positively checked opened inode.

    :param descriptor: Held actual regular/unlinked owned receipt descriptor.
    :param record: Rebuilt closed safe current-case schema.
    :return: None after complete actual byte persistence.
    :raises OSError: Actual bounded receipt write cannot complete.
    """
    payload = json.dumps(record, indent=2).encode()
    _regular_descriptor(descriptor, 16384)
    os.lseek(descriptor, 0, os.SEEK_SET)
    os.ftruncate(descriptor, 0)
    position = 0
    while position < len(payload):
        written = os.write(descriptor, payload[position:])
        if written <= 0:
            raise OSError("Actual bounded rejection receipt write did not advance.")
        position += written
    os.fsync(descriptor)


def _capture_paths(output: Path, original: Path) -> tuple[Path, Path]:
    """Validate every observed directory before any receipt or original access.

    :param output: Actual owned evidence root.
    :param original: Actual original beneath its screenshots directory.
    :return: Checked private folder and absent exact destination.
    :raises ValueError: Any observed alias, foreign owner or prior destination.
    """
    for directory in (output, output / "private", original.parent):
        _checked_directory(directory)
    if original.parent != output / "screenshots":
        raise ValueError(
            "Original acquisition must belong to the owned screenshot root."
        )
    folder = output / "private/rejected-captures"
    if folder.exists() or folder.is_symlink():
        _checked_directory(folder)
    destination = folder / original.name
    if destination.exists() or destination.is_symlink():
        raise ValueError("Rejected original acquisition cannot be replaced.")
    return folder, destination


def _checked_directory(path: Path) -> None:
    """Observe an actual unaliased owned directory with a NoFollow descriptor.

    :param path: Exact absolute owned directory.
    :return: None after ownership/type/alias checks.
    :raises ValueError: Observed link, type or ownership differs.
    """
    if not path.is_absolute() or path.resolve() != path:
        raise ValueError("Actual unaliased owned capture directory required.")
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    except OSError as error:
        raise ValueError(
            "Actual unaliased owned capture directory required."
        ) from error
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid():
            raise ValueError("Actual owned capture directory required.")
    finally:
        os.close(descriptor)


def _open_regular(path: Path, flags: int, bound: int) -> int:
    """Open only a positively owned regular unlinked bounded actual file.

    :param path: Exact observed canonical owned file path.
    :param flags: Fixed caller-owned read/write/create flags without truncation.
    :param bound: Fixed finite file-byte budget.
    :return: Verified descriptor, closed by its exact caller.
    :raises ValueError: Alias, ownership, size or hardlink differs before any read.
    """
    if path.resolve() != path:
        raise ValueError("Actual unaliased capture file required.")
    try:
        descriptor = os.open(path, flags | os.O_NOFOLLOW, 0o600)
    except OSError as error:
        raise ValueError("Actual regular capture file required.") from error
    try:
        _regular_descriptor(descriptor, bound)
    except ValueError:
        os.close(descriptor)
        raise
    return descriptor


def _regular_descriptor(descriptor: int, bound: int) -> None:
    """Check the actual opened inode before reading or destructive operations.

    :param descriptor: Actual NoFollow opened descriptor.
    :param bound: Fixed maximum actual bytes.
    :return: None after positive ownership/type/link-count/bounds checks.
    :raises ValueError: Actual opened inode is unsafe.
    """
    info = os.fstat(descriptor)
    if (
        not stat.S_ISREG(info.st_mode)
        or info.st_nlink != 1
        or info.st_uid != os.getuid()
        or not 0 <= info.st_size <= bound
    ):
        raise ValueError("Owned regular unlinked bounded capture file required.")


def _open_rejection(path: Path, case: str) -> tuple[int | None, dict[str, Any]]:
    """Read only the current case's exact closed safe rejection schema.

    :param path: Exact owned receipt path.
    :param case: Current true source case.
    :return: Held verified descriptor plus closed data, or fresh closed data.
    :raises ValueError: Topology, parsing, case, fields, count or hashes differ.
    """
    if case not in {
        "nomination",
        "copy-maria",
        "copy-guest",
        "copy-self",
        "summary-acceptance",
    }:
        raise ValueError("Exact true capture case required.")
    if not path.exists() and not path.is_symlink():
        return None, {
            "case": case,
            "rejected_captures": 0,
            "rejected_capture_sha256": [],
            "blank_originals_private": True,
        }
    descriptor = _open_regular(path, os.O_RDWR, 16384)
    try:
        record = json.loads(os.read(descriptor, 16385))
        _rejection_schema(record, case)
    except (ValueError, TypeError):
        os.close(descriptor)
        raise
    return descriptor, record


def _rejection_schema(record: Any, case: str) -> None:
    """Reject unknown content rather than preserving it in a public receipt.

    :param record: Parsed actual owned receipt.
    :param case: Exact current source case.
    :return: None only for the closed matching case/count/hash schema.
    :raises ValueError: Unknown fields, untyped values or mixed-case data.
    """
    keys = {
        "case",
        "rejected_captures",
        "rejected_capture_sha256",
        "blank_originals_private",
    }
    if (
        not isinstance(record, dict)
        or set(record) != keys
        or record["case"] != case
        or record["blank_originals_private"] is not True
    ):
        raise ValueError("Exact current closed rejection schema required.")
    hashes = record["rejected_capture_sha256"]
    if (
        not isinstance(hashes, list)
        or type(record["rejected_captures"]) is not int
        or not 0 <= record["rejected_captures"] <= 128
        or len(hashes) != record["rejected_captures"]
        or any(
            not isinstance(value, str) or not re.fullmatch(r"[a-f0-9]{64}", value)
            for value in hashes
        )
    ):
        raise ValueError("Exact bounded rejection count/hash list required.")


def _original_digest(path: Path) -> str:
    """Hash the actual owned original through a validated descriptor.

    :param path: Canonical actual capture path.
    :return: Exact original SHA without editing any pixels.
    :raises ValueError: Topology or byte budget differs before reading.
    """
    descriptor = _open_regular(path, os.O_RDONLY, 8 * 1024**2)
    digest = hashlib.sha256()
    try:
        while block := os.read(descriptor, 8192):
            digest.update(block)
    finally:
        os.close(descriptor)
    return digest.hexdigest()
