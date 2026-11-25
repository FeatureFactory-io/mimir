"""Full-suite closed lifecycle and public-admission regression contracts."""

from __future__ import annotations

import hashlib
import json
import sys
import zipfile
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "scripts/experts-staging"))
import suite_contract as suite
import suite_export as export
from saga_trace import redact_trace


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
