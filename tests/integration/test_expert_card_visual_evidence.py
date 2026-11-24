"""Validate observed implementation evidence for the complete Experts card matrix."""

from __future__ import annotations

import hashlib
import itertools
import json
import os
import re
import struct
from pathlib import Path
from typing import Any
from zipfile import ZipFile

_REPO = Path(__file__).resolve().parents[2]
_MANIFEST = _REPO / "docs/ux/experts-card-implementation-evidence.json"
_APPROVED_INDEX = _REPO / "docs/ux/experts-responsive-evidence.json"
_LIST_SCREEN = "FOB-EXPERTS-LIST+FIND-1"
_ICON_FONT_PREFIX = "Font Awesome "
_DETAIL_SCREEN = "FOB-EXPERT-VIEW-1"
_VIEWPORTS = {
    "wide-low": (1280, 800),
    "large-desktop": (1920, 1080),
    "laptop": (1512, 982),
    "tablet-portrait": (768, 1024),
    "tablet-landscape": (1024, 768),
    "phone": (390, 844),
    "minimum-phone": (360, 800),
}
_VARIANTS = {
    "normal": ("design", "authenticated", 5, "leaderboard"),
    "long_identity_and_prose": ("design", "authenticated", 5, "leaderboard"),
    "missing_summary": ("development", "authenticated", 2, "missing-summary"),
    "guest": ("design", "guest", 5, "guest-list"),
}
_REQUIRED_SOURCE_FILES = {
    "docs/ux/IA_guidelines.md",
    "docs/ux/experts-responsive-evidence.json",
    "methodology/expert_views.py",
    "methodology/services/expert_card_presentation.py",
    "static/css/design-system.css",
    "static/css/mimir-app.css",
    "static/js/product_analytics.js",
    "templates/base.html",
    "templates/experts/_reach_out.html",
    "templates/experts/detail.html",
    "templates/experts/list.html",
    "templates/mockups/experts/base.html",
    "templates/mockups/experts/list.html",
    "test-data/experts/cedar-rfp-01.json",
    "tests/e2e/test_expert_cards.py",
}


def test_experts_cards_with_reviewed_visual_evidence_cover_required_states() -> None:
    """Require implementation capture, current sources and review for each state.

    :return: None when the matrix, detail navigation, captures and review agree.
    :raises AssertionError: For missing, stale, unresolved or prototype evidence.
    """
    evidence = json.loads(_MANIFEST.read_text(encoding="utf-8"))
    root = Path(
        os.environ.get(
            "EXPERTS_EVIDENCE_ROOT",
            Path.home() / "Desktop/RIPL-Experts-Production/runs/session-01",
        )
    ).resolve()
    _assert_run(evidence, root)
    rows = evidence["captures"]
    matrix = {
        (row["screen_id"], row["variant"], row["viewport"]["name"]) for row in rows
    }
    required = {
        (_LIST_SCREEN, variant, viewport)
        for variant, viewport in itertools.product(_VARIANTS, _VIEWPORTS)
    }
    required.add((_DETAIL_SCREEN, "profile_handoff", "minimum-phone"))
    assert len(rows) == len(matrix) and matrix == required
    approved = json.loads(_APPROVED_INDEX.read_text(encoding="utf-8"))
    for row in rows:
        _assert_review(row, approved, root)
        _assert_capture(row, root, evidence["environment"]["browser"])
    assert len({row["screenshot"] for row in rows}) == len(rows)
    assert len({row["trace"] for row in rows}) == len(rows)


def _assert_run(evidence: dict[str, Any], root: Path) -> None:
    """Tie the review to the real local Chromium run and relevant current sources."""
    assert evidence["status"] == "reviewed"
    assert evidence["owner"] == "S04" and evidence["contract"] == "EXPERTS-LIST-04"
    assert evidence["evidence_observed"] is True and evidence["defects"] == []
    assert re.fullmatch(r"[a-f0-9]{40}", evidence["source_revision"])
    environment = evidence["environment"]
    assert environment["settings"] == "mimir.settings.e2e"
    assert environment["server_scope"] == "function"
    assert environment["dataset"] == "CEDAR-RFP-01"
    assert environment["browser"].startswith("Chromium ")
    _assert_verification(evidence, root)
    hashes = evidence["source_sha256"]
    assert set(hashes) == _REQUIRED_SOURCE_FILES
    for name, expected in hashes.items():
        assert _sha256(_REPO / name) == expected, f"Stale capture inputs in {name}"


def _assert_verification(evidence: dict[str, Any], root: Path) -> None:
    """Require a full, passing matrix on the recorded source revision."""
    verification = evidence["verification"]
    assert verification["target"] == "make test-experts-s04-browser"
    assert (
        verification["selected"] == verification["passed"] == len(evidence["captures"])
    )
    assert verification["failed"] == verification["skipped"] == 0
    transcript = _artifact(root, verification["transcript"]).read_text()
    assert f"collected {verification['selected']} items" in transcript
    assert f"{verification['passed']} passed in " in transcript
    captured_head = _artifact(root, verification["source_head"]).read_text().strip()
    assert captured_head == evidence["source_revision"]
    captured_hashes = json.loads(
        _artifact(root, verification["source_hashes"]).read_text()
    )
    assert captured_hashes == evidence["source_sha256"]
    _assert_recapture_provenance(evidence, root)


def _assert_recapture_provenance(evidence: dict[str, Any], root: Path) -> None:
    """Allow identified CDN recaptures only with identical source inputs."""
    verification = evidence["verification"]
    full_run = Path(verification["source_head"]).parent
    case_directories: dict[str, Path] = {}
    for recapture in verification["asset_recaptures"]:
        directory = Path(recapture["directory"])
        hashes = _artifact(root, str(directory / "source-sha256.json"))
        assert json.loads(hashes.read_text()) == evidence["source_sha256"]
        transcript = _artifact(root, recapture["transcript"]).read_text()
        cases = recapture["cases"]
        assert f"{len(cases)} passed, " in transcript
        for case in cases:
            assert case not in case_directories
            original_path = _artifact(root, str(full_run / f"{case}.json"))
            original = json.loads(original_path.read_text())
            assert original["result"] == "passed" and not _has_rendered_fonts(original)
            case_directories[case] = directory
    for row in evidence["captures"]:
        report = Path(row["capture_report"])
        assert report.parent == case_directories.pop(report.stem, full_run)
        assert (
            Path(row["screenshot"]).parent == Path(row["trace"]).parent == report.parent
        )
    assert not case_directories


def _assert_review(
    row: dict[str, Any], approved: list[dict[str, Any]], root: Path
) -> None:
    """Match the observed review to the approved recipe for the same viewport."""
    detail = row["screen_id"] == _DETAIL_SCREEN
    variant = row["variant"]
    reference_variant = "public-profile" if detail else _VARIANTS[variant][3]
    viewport = row["viewport"]
    assert (viewport["width"], viewport["height"]) == _VIEWPORTS[viewport["name"]]
    assert row["recipe"] == (
        "8+4 read and context rail" if detail else "Full-width ranked cards"
    )
    review = row["visual_review"]
    assert review["status"] == "reviewed" and row["reviewer"].strip()
    assert review["notes"].strip() and row["defects"] == []
    _artifact(root, f"screenshots/{review['approved_reference']}")
    assert any(
        ref["variant"] == reference_variant
        and ref["viewport"] == viewport
        and Path(ref["screenshot"]).name == review["approved_reference"]
        for ref in approved
    )


def _assert_capture(row: dict[str, Any], root: Path, browser: str) -> None:
    """Verify real run outputs against the screenshot, trace and manifest record."""
    report_path = _artifact(root, row["capture_report"])
    report = json.loads(report_path.read_text(encoding="utf-8"))
    width, height = _VIEWPORTS[row["viewport"]["name"]]
    assert row["result"] == report["result"] == "passed"
    assert report["browser"] == browser
    assert report["viewport"] == {"width": width, "height": height}
    assert report["document_width"] == width
    _assert_rendered_assets(row, report)
    if row["screen_id"] == _LIST_SCREEN:
        category, form, count, _ = _VARIANTS[row["variant"]]
        assert row["route"] == report["route"] == f"/experts/?category={category}"
        assert report["form"] == form and report["article_count"] == count
    else:
        assert row["route"] == report["route"] == "/experts/mrodriguez/"
        assert report["form"] == "authenticated"
    screenshot = _artifact(root, row["screenshot"])
    assert screenshot.name == report["screenshot"]
    assert _sha256(screenshot) == report["screenshot_sha256"]
    assert _png_covers_viewport(screenshot, width, height)
    trace = _artifact(root, row["trace"])
    assert trace.name == report["trace"] and _sha256(trace) == report["trace_sha256"]
    with ZipFile(trace) as archive:
        assert {"trace.trace", "trace.network"} <= set(archive.namelist())


def _assert_rendered_assets(row: dict[str, Any], report: dict[str, Any]) -> None:
    """Check each documented header and its real webfont assets."""
    detail = row["screen_id"] == _DETAIL_SCREEN
    assert row["loaded_fonts"] == report["loaded_fonts"]
    assert _has_rendered_fonts(report)
    heading = "Maria Rodriguez" if detail else "Experts"
    assert row["header"] == report["header"] == [heading, "28px", "600"]
    assert row["header_icon"] is report["header_icon"] is (not detail)


def _has_rendered_fonts(report: dict[str, Any]) -> bool:
    """Distinguish a complete capture from a transient font CDN miss."""
    fonts = report["loaded_fonts"]
    return "Montserrat" in fonts and any(
        font.startswith(_ICON_FONT_PREFIX) for font in fonts
    )


def _artifact(root: Path, name: str) -> Path:
    """Resolve a nonempty artifact inside the evidence package."""
    path = (root / name).resolve()
    assert path.is_relative_to(root) and path.is_file() and path.stat().st_size, name
    return path


def _sha256(path: Path) -> str:
    """Hash an artifact or source without retaining its bytes in memory."""
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def _png_covers_viewport(screenshot: Path, width: int, height: int) -> bool:
    """Require a genuine PNG header with full CSS-viewport coverage at DPR 1."""
    with screenshot.open("rb") as png:
        header = png.read(24)
    if len(header) != 24 or header[:16] != b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR":
        return False
    image_width, image_height = struct.unpack(">II", header[16:])
    return image_width == width and image_height >= height
