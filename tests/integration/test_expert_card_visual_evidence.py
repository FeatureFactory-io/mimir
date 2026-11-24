"""Check the committed Experts review manifest and verify acquired artifacts on demand.

Run ``make test-experts-s04-evidence`` with ``EXPERTS_EVIDENCE_ROOT`` set to the
reviewed session package. Normal pytest runs validate the manifest from the checkout.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import os
import re
import struct
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import Any
from zipfile import ZipFile

import pytest

_REPO = Path(__file__).resolve().parents[2]
_MANIFEST = _REPO / "docs/ux/experts-card-implementation-evidence.json"
_APPROVED_INDEX = _REPO / "docs/ux/experts-responsive-evidence.json"
_LIST_SCREEN = "FOB-EXPERTS-LIST+FIND-1"
_ICON_FONT_PREFIX = "Font Awesome "
_DETAIL_SCREEN = "FOB-EXPERT-VIEW-1"
_GIT_SHA = re.compile(r"[a-f0-9]{40}")
_SHA256 = re.compile(r"[a-f0-9]{64}")
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


def test_experts_card_evidence_manifest_covers_reviewed_state_matrix() -> None:
    """Check all committed review declarations and their current source inputs."""
    _assert_manifest(json.loads(_MANIFEST.read_text(encoding="utf-8")))


def test_experts_card_evidence_manifest_with_stale_source_rejects() -> None:
    """A valid-looking hash still has to match the current file."""
    evidence = json.loads(_MANIFEST.read_text(encoding="utf-8"))
    evidence["source_sha256"]["templates/experts/list.html"] = "0" * 64
    with pytest.raises(AssertionError, match="Stale capture inputs"):
        _assert_manifest(evidence)


def test_experts_card_evidence_manifest_with_duplicate_state_rejects() -> None:
    """An unchanged count cannot mask a missing matrix entry."""
    evidence = json.loads(_MANIFEST.read_text(encoding="utf-8"))
    evidence["captures"][-1] = evidence["captures"][0]
    with pytest.raises(AssertionError, match="capture matrix"):
        _assert_manifest(evidence)


@pytest.mark.parametrize("path", ["../capture.png", "/capture.png"])
def test_experts_card_evidence_manifest_with_unsafe_artifact_path_rejects(
    path: str,
) -> None:
    """Reject artifact paths outside the portable package structure."""
    evidence = json.loads(_MANIFEST.read_text(encoding="utf-8"))
    evidence["captures"][0]["screenshot"] = path
    with pytest.raises(AssertionError, match="Unsafe evidence path"):
        _assert_manifest(evidence)


def test_experts_card_evidence_manifest_with_mismatched_recapture_rejects() -> None:
    """A recaptured case must identify its genuine original report."""
    evidence = json.loads(_MANIFEST.read_text(encoding="utf-8"))
    recapture = evidence["verification"]["asset_recaptures"][0]
    recapture["original_report"] = evidence["captures"][0]["capture_report"]
    with pytest.raises(AssertionError, match="Original recapture report"):
        _assert_manifest(evidence)


def test_experts_card_artifact_gate_with_no_evidence_root_fails() -> None:
    """The separate verification command requires an explicit package root."""
    environment = os.environ.copy()
    environment.pop("EXPERTS_EVIDENCE_ROOT", None)
    completed = subprocess.run(
        [sys.executable, "-m", __name__],
        cwd=_REPO,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode != 0
    assert "Set EXPERTS_EVIDENCE_ROOT" in completed.stderr


def test_experts_card_artifact_gate_with_empty_evidence_package_fails(
    tmp_path: Path,
) -> None:
    """An existing directory alone cannot satisfy artifact verification."""
    with pytest.raises(AssertionError, match="Missing or empty evidence artifact"):
        _assert_artifacts(tmp_path.resolve())


def test_experts_card_artifact_with_symlink_outside_package_rejects(
    tmp_path: Path,
) -> None:
    """A safe-looking relative path may still resolve outside the package."""
    package = tmp_path / "package"
    package.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("other", encoding="utf-8")
    (package / "capture.txt").symlink_to(outside)
    with pytest.raises(AssertionError, match="Evidence path escapes package"):
        _artifact(package.resolve(), "capture.txt")


def _assert_manifest(evidence: dict[str, Any]) -> None:
    """Validate the committed review metadata without reading external artifacts."""
    _assert_run_metadata(evidence)
    rows = evidence["captures"]
    _assert_matrix(rows)
    approved = _read_json(_APPROVED_INDEX)
    for row in rows:
        _assert_review(row, approved)
        _assert_capture_declaration(row)
    _assert_provenance_declarations(evidence)


def _assert_matrix(rows: list[dict[str, Any]]) -> None:
    """Require a unique review row for every viewport/state and detail handoff."""
    matrix = {
        (row["screen_id"], row["variant"], row["viewport"]["name"]) for row in rows
    }
    required = {
        (_LIST_SCREEN, variant, viewport)
        for variant, viewport in itertools.product(_VARIANTS, _VIEWPORTS)
    }
    required.add((_DETAIL_SCREEN, "profile_handoff", "minimum-phone"))
    assert len(rows) == len(matrix) and matrix == required, "Incomplete capture matrix"
    for field in ("screenshot", "trace", "capture_report"):
        assert len({row[field] for row in rows}) == len(rows), f"Duplicate {field}"


def _assert_run_metadata(evidence: dict[str, Any]) -> None:
    """Check the review, browser environment and checkout source declaration."""
    assert evidence["status"] == "reviewed"
    assert evidence["owner"] == "S04" and evidence["contract"] == "EXPERTS-LIST-04"
    assert evidence["evidence_observed"] is True and evidence["defects"] == []
    assert _GIT_SHA.fullmatch(evidence["source_revision"])
    environment = evidence["environment"]
    assert environment["scope"].strip()
    assert environment["settings"] == "mimir.settings.e2e"
    assert environment["server_scope"] == "function"
    assert environment["dataset"] == "CEDAR-RFP-01"
    assert re.fullmatch(r"Chromium \d+(?:\.\d+)+", environment["browser"])
    review = evidence["review_basis"]
    assert review["approved_index"] == _APPROVED_INDEX.relative_to(_REPO).as_posix()
    assert review["guide"].partition("#")[0] == "docs/ux/IA_guidelines.md"
    assert review["reviewer"].strip() and review["notes"].strip()
    _relative_path(review["contact_sheets"])
    hashes = evidence["source_sha256"]
    assert set(hashes) == _REQUIRED_SOURCE_FILES
    for name, expected in hashes.items():
        assert _SHA256.fullmatch(expected), f"Invalid source SHA-256 for {name}"
        assert _sha256(_REPO / name) == expected, f"Stale capture inputs in {name}"


def _assert_provenance_declarations(evidence: dict[str, Any]) -> None:
    """Tie each declared capture to the full run or a named asset recapture."""
    verification = evidence["verification"]
    assert verification["target"] == "make test-experts-s04-browser"
    for field in ("selected", "passed", "failed", "skipped"):
        expected = len(evidence["captures"]) if field in ("selected", "passed") else 0
        assert type(verification[field]) is int and verification[field] == expected
    _transcript_path(verification["transcript"])
    source_head = _relative_path(verification["source_head"])
    full_run = source_head.parent
    assert source_head.parts[0] == "traces" and source_head.name == "source-head.txt"
    assert (
        _relative_path(verification["source_hashes"]) == full_run / "source-sha256.json"
    )
    case_directories = _recapture_directories(
        verification["asset_recaptures"], full_run
    )
    for row in evidence["captures"]:
        report = _relative_path(row["capture_report"])
        assert report.parent == case_directories.pop(report.stem, full_run)
        assert all(
            _relative_path(row[key]).parent == report.parent
            for key in ("screenshot", "trace")
        )
    assert not case_directories, "Recaptures must match required browser cases"


def _recapture_directories(
    recaptures: list[dict[str, Any]], full_run: PurePosixPath
) -> dict[str, PurePosixPath]:
    """Check asset recapture declarations and return their case-to-folder map."""
    case_directories: dict[str, PurePosixPath] = {}
    directories: set[PurePosixPath] = set()
    for recapture in recaptures:
        directory = _relative_path(recapture["directory"])
        assert directory != full_run and directory.parent == full_run.parent
        assert (
            directory not in directories
        ), f"Duplicate recapture directory: {directory}"
        directories.add(directory)
        revision = recapture.get("source_revision")
        assert (
            isinstance(revision, str)
            and _GIT_SHA.fullmatch(revision)
            and int(revision, 16) > 0
        ), f"Invalid recapture source revision: {directory}"
        _transcript_path(recapture["transcript"])
        cases = recapture["cases"]
        assert isinstance(cases, list) and cases and recapture["reason"].strip()
        originals = {full_run / f"{case}.json" for case in cases}
        assert (
            _relative_path(recapture["original_report"]) in originals
        ), "Original recapture report must identify a case in the full run"
        for case in cases:
            assert (
                _relative_path(case).parts == (case,) and case not in case_directories
            )
            case_directories[case] = directory
    return case_directories


def _assert_review(row: dict[str, Any], approved: list[dict[str, Any]]) -> None:
    """Match committed review declarations to the approved recipe and viewport."""
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
    reference = _relative_path(review["approved_reference"])
    assert reference.parts == (reference.name,) and reference.suffix == ".png"
    assert any(
        ref["variant"] == reference_variant
        and ref["viewport"] == viewport
        and Path(ref["screenshot"]).name == review["approved_reference"]
        for ref in approved
    )


def _assert_capture_declaration(row: dict[str, Any]) -> None:
    """Check the production route, expected header and declared artifact names."""
    detail = row["screen_id"] == _DETAIL_SCREEN
    viewport = row["viewport"]
    case = f"{row['variant']}-{viewport['width']}-{viewport['height']}"
    if detail:
        case = "detail-minimum-phone"
    for field, extension in (
        ("screenshot", "png"),
        ("trace", "zip"),
        ("capture_report", "json"),
    ):
        assert _relative_path(row[field]).name == f"{case}.{extension}"
    heading = "Maria Rodriguez" if detail else "Experts"
    assert row["header"] == [heading, "28px", "600"]
    assert row["header_icon"] is (not detail)
    assert row["result"] == "passed" and _has_rendered_fonts(row)
    route = (
        "/experts/mrodriguez/"
        if detail
        else f"/experts/?category={_VARIANTS[row['variant']][0]}"
    )
    assert row["route"] == route


def _assert_artifacts(root: Path) -> tuple[int, int]:
    """Validate every recorded artifact and return the capture and recapture counts.

    :param root: Resolved directory containing the reviewed session package.
    :return: Counts of checked captures and CDN recapture runs.
    :raises AssertionError: If any evidence is missing, stale or inconsistent.
    """
    assert root.is_dir(), f"Evidence package directory does not exist: {root}"
    evidence = _read_json(_MANIFEST)
    _assert_manifest(evidence)
    _assert_verification(evidence, root)
    for row in evidence["captures"]:
        _artifact(root, f"screenshots/{row['visual_review']['approved_reference']}")
        _assert_capture(row, root, evidence["environment"]["browser"])
    return len(evidence["captures"]), len(evidence["verification"]["asset_recaptures"])


def _assert_verification(evidence: dict[str, Any], root: Path) -> None:
    """Verify the full browser transcript and each genuine CDN recapture."""
    verification = evidence["verification"]
    transcript, started_at = _recorded_transcript(root, verification["transcript"])
    assert f"collected {verification['selected']} items" in transcript
    assert f"{verification['passed']} passed in " in transcript
    _assert_acquisition_head(
        root, verification["source_head"], evidence["source_revision"]
    )
    hashes = _artifact(root, verification["source_hashes"])
    assert _read_json(hashes) == evidence["source_sha256"]
    for recapture in verification["asset_recaptures"]:
        _assert_recapture(evidence, recapture, root, started_at)


def _assert_recapture(
    evidence: dict[str, Any], recapture: dict[str, Any], root: Path, started_at: int
) -> None:
    """Check the actual rerun revision, identical inputs and missing-font originals."""
    directory = PurePosixPath(recapture["directory"])
    hashes = _artifact(root, (directory / "source-sha256.json").as_posix())
    assert _read_json(hashes) == evidence["source_sha256"]
    _assert_acquisition_head(
        root, (directory / "source-head.txt").as_posix(), recapture["source_revision"]
    )
    transcript, recaptured_at = _recorded_transcript(root, recapture["transcript"])
    assert recaptured_at >= started_at
    cases = recapture["cases"]
    assert (
        f"/ {len(cases)} selected" in transcript
        and f"{len(cases)} passed, " in transcript
    )
    full_run = PurePosixPath(evidence["verification"]["source_head"]).parent
    for case in cases:
        original_path = _artifact(root, (full_run / f"{case}.json").as_posix())
        original = _read_json(original_path)
        assert original["result"] == "passed" and not _has_rendered_fonts(original)


def _assert_acquisition_head(root: Path, path: str, revision: str) -> None:
    """Match the immutable acquisition revision recorded as one line.

    :param root: Resolved directory containing the reviewed session package.
    :param path: Evidence package path to the recorded Git HEAD.
    :param revision: Full Git revision declared for this acquisition.
    :raises AssertionError: If the record is missing or differs from its declaration.
    """
    expected = f"{revision}\n".encode("ascii")
    assert (
        _artifact(root, path).read_bytes() == expected
    ), f"Acquisition revision mismatch: {path}"


def _transcript_path(name: str) -> PurePosixPath:
    """Require the package's portable CLI transcript path."""
    path = _relative_path(name)
    assert path.parent == PurePosixPath("cli") and path.suffix == ".txt"
    return path


def _recorded_transcript(root: Path, name: str) -> tuple[str, int]:
    """Match a transcript to its timestamped PTY recording."""
    transcript = _artifact(root, name).read_bytes().decode("utf-8")
    cast_path = _transcript_path(name).with_suffix(".cast")
    with _artifact(root, cast_path.as_posix()).open(encoding="utf-8") as cast:
        header = json.loads(cast.readline())
        events = [json.loads(line) for line in cast]
    assert header["version"] == 2 and header["title"] == cast_path.stem
    timestamp = header["timestamp"]
    assert type(timestamp) is int and timestamp > 0
    assert (
        events
        and "".join(event[2] for event in events if event[1] == "o") == transcript
    )
    return transcript, timestamp


def _assert_capture(row: dict[str, Any], root: Path, browser: str) -> None:
    """Verify real run outputs against the screenshot, trace and manifest record."""
    report_path = _artifact(root, row["capture_report"])
    report = _read_json(report_path)
    width, height = _VIEWPORTS[row["viewport"]["name"]]
    assert row["result"] == report["result"] == "passed"
    assert report["browser"] == browser
    assert report["viewport"] == {"width": width, "height": height}
    assert report["document_width"] == width
    assert row["loaded_fonts"] == report["loaded_fonts"]
    assert row["header"] == report["header"]
    assert row["header_icon"] is report["header_icon"]
    assert row["route"] == report["route"]
    if row["screen_id"] == _LIST_SCREEN:
        _, form, count, _ = _VARIANTS[row["variant"]]
        assert report["form"] == form and report["article_count"] == count
    else:
        assert report["form"] == "authenticated"
    screenshot = _artifact(root, row["screenshot"])
    assert screenshot.name == report["screenshot"]
    assert (
        _sha256(screenshot) == report["screenshot_sha256"]
    ), f"Screenshot hash mismatch: {row['screenshot']}"
    assert _png_covers_viewport(screenshot, width, height)
    trace = _artifact(root, row["trace"])
    assert trace.name == report["trace"]
    assert (
        _sha256(trace) == report["trace_sha256"]
    ), f"Trace hash mismatch: {row['trace']}"
    with ZipFile(trace) as archive:
        assert {"trace.trace", "trace.network"} <= set(archive.namelist())


def _has_rendered_fonts(report: dict[str, Any]) -> bool:
    """Distinguish a complete capture from a transient font CDN miss."""
    fonts = report["loaded_fonts"]
    return "Montserrat" in fonts and any(
        font.startswith(_ICON_FONT_PREFIX) for font in fonts
    )


def _relative_path(name: str) -> PurePosixPath:
    """Reject unsafe manifest paths even when no evidence files are installed."""
    assert (
        isinstance(name, str) and "\\" not in name and "\0" not in name
    ), f"Unsafe evidence path: {name!r}"
    path = PurePosixPath(name)
    assert (
        path.parts and not path.is_absolute() and ".." not in path.parts
    ), f"Unsafe evidence path: {name}"
    return path


def _artifact(root: Path, name: str) -> Path:
    """Resolve a nonempty artifact inside the evidence package."""
    path = (root / _relative_path(name)).resolve()
    assert path.is_relative_to(root), f"Evidence path escapes package: {name}"
    assert (
        path.is_file() and path.stat().st_size
    ), f"Missing or empty evidence artifact: {name}"
    return path


def _sha256(path: Path) -> str:
    """Hash an artifact or source without retaining its bytes in memory."""
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def _read_json(path: Path) -> Any:
    """Read the package and checkout's UTF-8 JSON files consistently."""
    return json.loads(path.read_text(encoding="utf-8"))


def _png_covers_viewport(screenshot: Path, width: int, height: int) -> bool:
    """Require a genuine PNG header with full CSS-viewport coverage at DPR 1."""
    with screenshot.open("rb") as png:
        header = png.read(24)
    if len(header) != 24 or header[:16] != b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR":
        return False
    image_width, image_height = struct.unpack(">II", header[16:])
    return image_width == width and image_height >= height


def _main() -> None:
    """Run the opt-in verification command and report actual artifact counts."""
    if not __debug__:
        raise SystemExit(
            "S04 evidence verification requires Python assertions enabled."
        )
    configured_root = os.environ.get("EXPERTS_EVIDENCE_ROOT", "")
    if not configured_root.strip():
        raise SystemExit(
            "Set EXPERTS_EVIDENCE_ROOT to the reviewed S04 session package."
        )
    root = Path(configured_root).expanduser().resolve()
    captures, recaptures = _assert_artifacts(root)
    print(
        f"Verified {captures} S04 screenshot and trace pairs across {recaptures} asset recapture runs and the full run."
    )


if __name__ == "__main__":
    _main()
