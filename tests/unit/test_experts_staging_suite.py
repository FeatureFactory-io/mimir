"""Full-suite closed lifecycle and public-admission regression contracts."""

from __future__ import annotations

import hashlib
import io
import json
import struct
import sys
import tarfile
import zipfile
import zlib
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "scripts/experts-staging"))
import controller
import suite_archive as archive_control
import suite_capture as capture_control
import suite_contract as suite
import suite_export as export
import suite_pixels as pixels
from saga_trace import redact_trace
from suite_archive import verify_case_archive


def test_suite_cases_with_full_has_eleven_distinct_phases_and_final_true_nomination() -> (
    None
):
    rows = suite.suite_cases("full")
    assert len(rows) == 11 and len({r.phase for r in rows}) == 11
    assert rows[-1] == suite.SuiteCase("final-confirmation", "nomination", "esvensson")
    assert suite.suite_cases("core") == (rows[0],)


@pytest.mark.parametrize("value", [None, "FULL", "guest", "", 1])
def test_suite_cases_with_unknown_selector_rejects(value: object) -> None:
    with pytest.raises(ValueError):
        suite.suite_cases(value)


@pytest.mark.parametrize(
    "phase,case",
    [
        ("guest-public", "nomination"),
        ("final-confirmation", "guest-public"),
        ("evil", "core"),
    ],
)
def test_selected_case_with_relabelled_case_rejects(phase: str, case: str) -> None:
    with pytest.raises(ValueError):
        suite.selected_case({"suite_phase": phase, "saga_case": case})


def test_selected_case_with_legacy_manifest_preserves_default_core() -> None:
    assert suite.selected_case({}).case == "core"


def test_move_private_with_actual_original_moves_outside_exporter(
    tmp_path: Path,
) -> None:
    original = tmp_path / "output/private"
    original.mkdir(parents=True, mode=0o700)
    (original / "saga-trace-original.zip").write_bytes(b"PRIVATE")
    export.move_private(tmp_path)
    assert not original.exists()
    assert (
        tmp_path / "private-evidence/browser/saga-trace-original.zip"
    ).read_bytes() == b"PRIVATE"


def test_public_receipt_with_denied_url_failure_exports_count_and_original_hash() -> (
    None
):
    record = {
        "case": "nomination",
        "status": "FAILED",
        "exception_class": "RuntimeError",
        "undeclared_requests": ["GET https://evil/SECRET_TOKEN"],
    }
    raw = json.dumps(record).encode()
    result = export.public_receipt("saga-failure.json", record, raw)
    assert result["status"] == "FAILED" and result["undeclared_request_count"] == 1
    assert result["original_sha256"] == hashlib.sha256(raw).hexdigest()
    assert "SECRET_TOKEN" not in json.dumps(result)
    assert result["derivative"] is True


@pytest.mark.parametrize(
    "record",
    [
        {"status": "CASE_VERIFIED", "new_awards": "PRIVATE"},
        {"status": "FAILED", "exception_class": "PRIVATE"},
        {"status": "PASSED_BY_CALLER"},
    ],
)
def test_public_receipt_with_untyped_or_unreviewed_content_rejects(
    record: dict[str, object],
) -> None:
    with pytest.raises(ValueError):
        export.public_receipt("saga-effects.json", record, json.dumps(record).encode())


def test_prepare_public_with_actual_raw_trace_and_denied_metadata_preserves_safe_pixels(
    tmp_path: Path,
) -> None:

    output = tmp_path / "output"
    private = output / "private"
    private.mkdir(parents=True, mode=0o700)
    secret = "ACTUAL_PRIVATE_SESSION_SENTINEL"
    original = private / "saga-trace-original.zip"
    pixels = b"\x89PNG\r\n\x1a\nORIGINAL_BINARY_PIXELS"
    with zipfile.ZipFile(original, "w") as trace:
        trace.writestr("trace.trace", json.dumps({"session": secret}))
        trace.writestr("resources/original.png", pixels)
    (private / "captured-secrets.json").write_text(json.dumps({"values": [secret]}))
    provenance = redact_trace(original, output / "saga-trace.zip", {secret})
    (output / "saga-trace-provenance.json").write_text(json.dumps(provenance))
    raw = {
        "case": "nomination",
        "status": "FAILED",
        "exception_class": "RuntimeError",
        "undeclared_requests": ["GET https://evil/" + secret],
    }
    (output / "saga-failure.json").write_text(json.dumps(raw))
    export.prepare_public(tmp_path, {})
    assert not private.exists()
    assert (tmp_path / "private-evidence/browser/saga-trace-original.zip").read_bytes()
    receipt = json.loads((output / "saga-failure.json").read_text())
    assert receipt["status"] == "FAILED" and receipt["undeclared_request_count"] == 1
    assert secret not in (output / "saga-failure.json").read_text()
    with zipfile.ZipFile(output / "saga-trace.zip") as trace:
        assert trace.read("resources/original.png") == pixels
        assert secret.encode() not in trace.read("trace.trace")


def test_prepare_public_with_rejected_content_retains_raw_privately_and_exports_failure(
    tmp_path: Path,
) -> None:
    output = tmp_path / "output"
    output.mkdir()
    raw = b'{"status":"CASE_VERIFIED","new_awards":"PRIVATE_REJECTED_BYTES"}'
    (output / "saga-effects.json").write_bytes(raw)
    export.prepare_public(tmp_path, {})
    safe = json.loads((output / "saga-effects.json").read_text())
    assert safe["status"] == "FAILED" and safe["receipt_content_rejected"] is True
    assert (tmp_path / "private-evidence/reports/saga-effects.json").read_bytes() == raw
    assert b"PRIVATE_REJECTED_BYTES" not in (output / "saga-effects.json").read_bytes()


@pytest.mark.parametrize(
    "name",
    [
        "private/saga-browser.json",
        "worker.jsonl",
        "sessions.json",
        "screenshots/saga-nomination-UNDECLARED-attempt-1.png",
        "screenshots/visual-missing_summary-999-999.png",
        "saga-visual-anything.json",
    ],
)
def test_allowed_name_with_raw_or_undeclared_capture_rejects(name: str) -> None:
    assert export.allowed_name(Path(name)) is False


def test_public_receipt_with_precise_native_login_retains_safe_protocol() -> None:
    login = {
        "actor": "esvensson",
        "method": "POST",
        "path": "/auth/user/login/",
        "status": 302,
        "started_at": "2026-11-25T00:00:00.000001+00:00",
        "completed_at": "2026-11-25T00:00:00.000009+00:00",
        "session_key_sha256": "a" * 64,
    }
    row = {
        "case": "authenticated-matrix",
        "status": "BROWSER_OBSERVED",
        "login_observation": login,
        "nonread_requests": [{"method": "POST", "path": "/auth/user/login/"}],
    }
    safe = export.public_receipt(
        "suite-readonly-browser.json", row, json.dumps(row).encode()
    )
    assert (
        safe["login_observation"] == login
        and safe["nonread_requests"] == row["nonread_requests"]
    )


@pytest.mark.parametrize("tamper", ["actor", "path", "session_key_sha256", "extra"])
def test_public_receipt_with_unreviewed_native_protocol_rejects(tamper: str) -> None:
    login = {
        "actor": "esvensson",
        "method": "POST",
        "path": "/auth/user/login/",
        "status": 302,
        "started_at": "2026-11-25T00:00:00.000001+00:00",
        "completed_at": "2026-11-25T00:00:00.000009+00:00",
        "session_key_sha256": "a" * 64,
    }
    login[tamper] = "PRIVATE_REJECTED_VALUE"
    row = {
        "case": "authenticated-matrix",
        "status": "BROWSER_OBSERVED",
        "login_observation": login,
    }
    with pytest.raises((AssertionError, ValueError)):
        export.public_receipt(
            "suite-readonly-browser.json", row, json.dumps(row).encode()
        )


def test_allowed_name_with_guest_trace_chunks_is_closed_by_actual_ia_sizes() -> None:
    assert export.allowed_name(Path("traces/guest-public-1280-800.zip"))
    assert export.allowed_name(Path("traces/guest-public-1280-800.provenance.json"))
    assert not export.allowed_name(Path("traces/guest-public-999-999.zip"))
    assert not export.allowed_name(
        Path("private/guest-public-1280-800-trace-original.zip")
    )


@pytest.mark.parametrize(
    "name,allowed",
    [
        ("video/page@" + "a" * 32 + ".webm", True),
        ("video/" + "a" * 32 + ".webm", True),
        ("video/page@PRIVATE.webm", False),
        ("video/anything.webm", False),
    ],
)
def test_allowed_name_with_actual_native_video_spelling_is_closed(
    name: str, allowed: bool
) -> None:
    assert export.allowed_name(Path(name)) is allowed


def _archive_manifest() -> dict[str, str]:
    """Construct synthetic safe archive identity controls, never browser evidence.

    :return: Closed nonce/source/image/build/control facts.
    """
    return {
        "source_revision": "a" * 40,
        "build_run_id": "123",
        "web_image": "web@sha256:" + "b" * 64,
        "browser_image": "browser@sha256:" + "c" * 64,
        "fixture_sha256": "d" * 64,
        "nonce": "e" * 32,
        "suite_phase": "core",
        "saga_case": "core",
        "control_revision": "f" * 40,
    }


def _write_core_archive(
    path: Path, manifest: dict[str, str], changed: str | None = None
) -> None:
    """Write real tar bytes for a deliberately synthetic validator-only control.

    :param path: Exclusive owned test file.
    :param manifest: Baseline authentication facts.
    :param changed: One identity field changed only inside the downloaded artifact.
    :return: None after complete actual test archive creation.
    """
    identity = dict(manifest)
    if changed:
        identity[changed] = "0" * len(identity[changed])
    records = {
        "source-identity.json": identity,
        "browser-readiness.json": {"status": "SMOKE_ONLY_UAT_PENDING"},
        "post-browser-state.json": {"scope_rechecked": True},
    }
    with tarfile.open(path, "w:gz") as archive:
        for name, record in records.items():
            record.update(derivative=True, original_sha256="9" * 64)
            data = json.dumps(record).encode()
            info = tarfile.TarInfo(name)
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))
        for name in (
            "video/" + "a" * 32 + ".webm",
            "screenshots/guest-native-clipboard.png",
        ):
            data = (
                _png_control(bytes((245, 247, 250)), bytes((0, 0, 0)))
                if name.endswith(".png")
                else b"synthetic-validator-only-control"
            )
            info = tarfile.TarInfo(name)
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))


@pytest.mark.parametrize("field", ["browser_image", "fixture_sha256", "build_run_id"])
def test_verify_case_archive_with_cross_bound_identity_mismatch_rejects(
    tmp_path: Path, field: str
) -> None:
    manifest = _archive_manifest()
    target = tmp_path / "actual.tar.gz"
    _write_core_archive(target, manifest, field)
    with pytest.raises(ValueError):
        verify_case_archive(target, manifest)


def test_verify_case_archive_with_complete_matching_identity_accepts_control(
    tmp_path: Path,
) -> None:
    manifest = _archive_manifest()
    target = tmp_path / "clean.tar.gz"
    _write_core_archive(target, manifest)
    verify_case_archive(target, manifest)


def test_verified_current_download_with_stale_old_nonce_stamp_and_no_archive_preserves_private(
    tmp_path: Path,
) -> None:
    manifest = _archive_manifest()
    stamp = {"nonce": "0" * 32, "sha256": "a" * 64, "safe_archive_verified": True}
    (tmp_path / "verified-safe-download.json").write_text(json.dumps(stamp))
    assert controller.verified_current_download(tmp_path, manifest) is False


def _current_download_files(output: Path, manifest: dict[str, str]) -> None:
    """Write a current fully bound synthetic safe-download filesystem control.

    :param output: Exclusive owned control directory.
    :param manifest: Exact current synthetic identity.
    :return: None after actual archive, command, object and stamp files exist.
    """
    target = output / "idle-browser-evidence.tar.gz"
    _write_core_archive(target, manifest)
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    command = "12345678-1234-4234-8234-123456789abc"
    stamp = {
        "nonce": manifest["nonce"],
        "sha256": digest,
        "safe_archive_verified": True,
        "command_id": command,
    }
    receipt = {
        "evidence_key": f"experts-uat/{manifest['nonce']}/evidence.tar.gz",
        "sha256": digest,
        "bytes": target.stat().st_size,
    }
    ssm = {
        "nonce": manifest["nonce"],
        "CommandId": command,
        "Status": "Success",
        "ResponseCode": 0,
    }
    for name, record in (
        ("verified-safe-download.json", stamp),
        ("artifact-receipt.json", receipt),
        ("ssm-receipt.json", ssm),
    ):
        (output / name).write_text(json.dumps(record))


def test_verified_current_download_with_current_command_object_and_bytes_accepts(
    tmp_path: Path,
) -> None:
    manifest = _archive_manifest()
    _current_download_files(tmp_path, manifest)
    assert controller.verified_current_download(tmp_path, manifest) is True


@pytest.mark.parametrize(
    "tamper",
    [
        "old_nonce",
        "old_command",
        "wrong_object",
        "receipt_hash",
        "archive_bytes",
        "missing_archive",
        "missing_ssm",
        "linked_stamp",
    ],
)
def test_verified_current_download_with_stale_or_mismatched_transfer_preserves_private(
    tmp_path: Path, tamper: str
) -> None:
    manifest = _archive_manifest()
    _current_download_files(tmp_path, manifest)
    if tamper in {"old_nonce", "old_command"}:
        path = tmp_path / "verified-safe-download.json"
        record = json.loads(path.read_text())
        record["nonce" if tamper == "old_nonce" else "command_id"] = "0" * 32
        path.write_text(json.dumps(record))
    elif tamper in {"wrong_object", "receipt_hash"}:
        path = tmp_path / "artifact-receipt.json"
        record = json.loads(path.read_text())
        record["evidence_key" if tamper == "wrong_object" else "sha256"] = "0" * 64
        path.write_text(json.dumps(record))
    elif tamper == "archive_bytes":
        with (tmp_path / "idle-browser-evidence.tar.gz").open("ab") as stream:
            stream.write(b"changed")
    elif tamper == "missing_archive":
        (tmp_path / "idle-browser-evidence.tar.gz").unlink()
    elif tamper == "missing_ssm":
        (tmp_path / "ssm-receipt.json").unlink()
    else:
        path = tmp_path / "verified-safe-download.json"
        path.rename(tmp_path / "outside.json")
        path.symlink_to(tmp_path / "outside.json")
    assert controller.verified_current_download(tmp_path, manifest) is False


@pytest.mark.parametrize("kind", ["symlink", "hardlink"])
def test_prepare_public_with_linked_core_trace_rejects_before_touching_original(
    tmp_path: Path, kind: str
) -> None:
    root = tmp_path / "owned"
    output = root / "output"
    output.mkdir(parents=True, mode=0o700)
    outside = tmp_path / "outside.zip"
    with zipfile.ZipFile(outside, "w") as archive:
        archive.writestr("trace.trace", "PRIVATE_OUTSIDE_TRACE_SENTINEL")
    original = outside.read_bytes()
    target = output / "browser-trace.zip"
    if kind == "symlink":
        target.symlink_to(outside)
    else:
        target.hardlink_to(outside)
    with pytest.raises(ValueError):
        export.prepare_public(root, {})
    assert outside.read_bytes() == original
    assert target.is_symlink() if kind == "symlink" else target.stat().st_nlink == 2


@pytest.mark.parametrize(
    "field,value",
    [("new_awards", 999), ("scope_rechecked", False), ("full_saga_accepted", True)],
)
def test_verify_case_archive_with_received_effect_fact_mutation_rejects(
    tmp_path: Path, field: str, value: object
) -> None:
    manifest = _archive_manifest()
    manifest.update(suite_phase="nomination", saga_case="nomination")
    target = tmp_path / "effects-control.tar.gz"
    effects = {
        "case": "nomination",
        "status": "CASE_VERIFIED",
        "scope_rechecked": True,
        "new_awards": 0,
        "full_saga_accepted": False,
    }
    effects[field] = value
    records = {
        "source-identity.json": manifest,
        "saga-browser.json": {"case": "nomination", "status": "BROWSER_OBSERVED"},
        "saga-effects.json": effects,
    }
    with tarfile.open(target, "w:gz") as archive:
        for name, record in records.items():
            record = {**record, "derivative": True, "original_sha256": "9" * 64}
            data = json.dumps(record).encode()
            info = tarfile.TarInfo(name)
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))
        for name in (
            "video/" + "a" * 32 + ".webm",
            "screenshots/guest-native-clipboard.png",
            "saga-trace.zip",
        ):
            data = (
                _png_control(bytes((245, 247, 250)), bytes((0, 0, 0)))
                if name.endswith(".png")
                else b"synthetic-validator-control"
            )
            info = tarfile.TarInfo(name)
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))
    with pytest.raises(ValueError):
        verify_case_archive(target, manifest)


@pytest.mark.parametrize("field", ["source_revision", "application_source_revision"])
def test_received_browser_facts_with_contradictory_emitted_source_rejects(
    field: str,
) -> None:
    manifest = _archive_manifest()
    browser = {
        "fixture_sha256": manifest["fixture_sha256"],
        "viewport_count": 7,
        "viewports": [
            {"width": w, "height": h}
            for w, h in (
                (1280, 800),
                (1920, 1080),
                (1512, 982),
                (768, 1024),
                (1024, 768),
                (390, 844),
                (360, 800),
            )
        ],
        "login_observation": None,
        field: "0" * 40,
    }
    with pytest.raises(ValueError):
        archive_control._browser_facts("authenticated-matrix", browser, {}, manifest)


def _png_control(color: bytes, second: bytes | None = None) -> bytes:
    """Create tiny synthetic PNG pixel controls, never product screenshots.

    :param color: Exact first RGB pixel.
    :param second: Optional different second pixel.
    :return: Valid actual PNG fixture bytes with CRCs and lossless IDAT.
    """

    def chunk(kind: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + kind
            + data
            + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
        )

    ihdr = struct.pack(">IIBBBBB", 2, 1, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(
            b"IDAT",
            zlib.compress(b"\x00" + color + (color if second is None else second)),
        )
        + chunk(b"IEND", b"")
    )


@pytest.mark.parametrize("different", [False, True])
def test_png_nonuniform_with_actual_lossless_pixel_control_detects_blank(
    tmp_path: Path, different: bool
) -> None:
    target = tmp_path / "control.png"
    target.write_bytes(
        _png_control(bytes((245, 247, 250)), bytes((0, 0, 0)) if different else None)
    )
    assert pixels.png_nonuniform(target) is different


@pytest.mark.parametrize("raw", [b"", b"not-a-PNG", b"\x89PNG\r\n\x1a\n"])
def test_png_nonuniform_with_invalid_original_rejects(
    tmp_path: Path, raw: bytes
) -> None:
    target = tmp_path / "invalid.png"
    target.write_bytes(raw)
    with pytest.raises(ValueError):
        pixels.png_nonuniform(target)


def test_quarantine_blank_with_actual_original_retains_bytes_and_hash(
    tmp_path: Path,
) -> None:
    output = tmp_path / "output"
    (output / "private").mkdir(mode=0o700, parents=True)
    (output / "screenshots").mkdir()
    source = output / "screenshots/saga-summary-acceptance-C01-own-8200-attempt-1.png"
    raw = _png_control(bytes((245, 247, 250)))
    source.write_bytes(raw)
    capture_control.quarantine_blank(output, source, "summary-acceptance")
    private = output / "private/rejected-captures" / source.name
    assert not source.exists() and private.read_bytes() == raw
    receipt = json.loads((output / "capture-rejections.json").read_text())
    assert receipt["rejected_captures"] == 1 and receipt["rejected_capture_sha256"] == [
        hashlib.sha256(raw).hexdigest()
    ]
    assert (
        export.public_receipt(
            "capture-rejections.json", receipt, json.dumps(receipt).encode()
        )["blank_originals_private"]
        is True
    )


@pytest.mark.parametrize(
    "name",
    [
        "saga-summary-acceptance-C02-keyboard-expanded-attempt-1-viewport.json",
        "screenshots/saga-copy-maria-own-summary-8200-attempt-1-viewport.png",
        "screenshots/saga-nomination-E03-sofia-attempt-1-viewport.png",
    ],
)
def test_allowed_name_with_required_actual_native_uat_pair_is_closed(name: str) -> None:
    assert export.allowed_name(Path(name)) is True


@pytest.mark.parametrize("kind", ["hardlinked_receipt", "aliased_private_folder"])
def test_quarantine_blank_with_borrowed_topology_leaves_outside_and_original_untouched(
    tmp_path: Path, kind: str
) -> None:
    output = tmp_path / "output"
    (output / "private").mkdir(parents=True, mode=0o700)
    (output / "screenshots").mkdir()
    source = output / "screenshots/source.png"
    raw = _png_control(bytes((245, 247, 250)))
    source.write_bytes(raw)
    outside = tmp_path / "outside.json"
    original_record = json.dumps(
        {
            "case": "summary-acceptance",
            "rejected_captures": 0,
            "rejected_capture_sha256": [],
            "blank_originals_private": True,
        }
    ).encode()
    outside.write_bytes(original_record)
    if kind == "hardlinked_receipt":
        (output / "capture-rejections.json").hardlink_to(outside)
    else:
        directory = tmp_path / "outside-folder"
        directory.mkdir()
        (output / "private/rejected-captures").symlink_to(
            directory, target_is_directory=True
        )
    with pytest.raises(ValueError):
        capture_control.quarantine_blank(output, source, "summary-acceptance")
    assert source.read_bytes() == raw and outside.read_bytes() == original_record
    if kind == "aliased_private_folder":
        assert not list(directory.iterdir())


@pytest.mark.parametrize(
    "field,value",
    [
        ("unknown_private", "PRIVATE_BYTES"),
        ("case", "copy-maria"),
        ("rejected_captures", True),
        ("rejected_capture_sha256", ["PRIVATE_BYTES"]),
    ],
)
def test_quarantine_blank_with_unreviewed_existing_receipt_rejects_before_move(
    tmp_path: Path, field: str, value: object
) -> None:
    output = tmp_path / "output"
    (output / "private").mkdir(parents=True, mode=0o700)
    (output / "screenshots").mkdir()
    original = output / "screenshots/source.png"
    raw = _png_control(bytes((245, 247, 250)))
    original.write_bytes(raw)
    record = {
        "case": "summary-acceptance",
        "rejected_captures": 0,
        "rejected_capture_sha256": [],
        "blank_originals_private": True,
    }
    record[field] = value
    receipt = output / "capture-rejections.json"
    before = json.dumps(record).encode()
    receipt.write_bytes(before)
    with pytest.raises(ValueError):
        capture_control.quarantine_blank(output, original, "summary-acceptance")
    assert original.read_bytes() == raw and receipt.read_bytes() == before
