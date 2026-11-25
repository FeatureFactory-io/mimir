"""Content-checked public derivatives; raw reports and traces remain private."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import stat
import zipfile
from pathlib import Path
from typing import Any

import resource_profile
from saga_trace import (
    encode_private_values,
    trace_provenance,
    validate_members,
    verify_redacted,
    write_redacted,
)
from suite_contract import FULL_CASES
from suite_pixels import png_nonuniform
from suite_receipts import protocol_fields

_STATUSES = {
    "FAILED",
    "CASE_VERIFIED",
    "BROWSER_OBSERVED",
    "healthy",
    "CORE_READINESS_PASSED",
    "SMOKE_ONLY_UAT_PENDING",
}
_EXCEPTIONS = {
    "Exception",
    "AssertionError",
    "ValueError",
    "RuntimeError",
    "TimeoutError",
    "Error",
    "OSError",
    "CalledProcessError",
    "JSONDecodeError",
    "FileExistsError",
}
_INTS = {
    "users",
    "awards",
    "profiles",
    "bytes",
    "verified_files",
    "new_awards",
    "new_activities",
    "new_versions",
    "decision_mail_files",
    "provider_calls",
    "model_count",
    "viewport_count",
    "members",
    "redacted_members",
    "actual_clipboard_bytes",
    "proposed_target_seconds",
    "blocked_requests",
    "copy_receipt_requests",
    "document_width",
    "rejected_captures",
    "available_memory_bytes",
    "required_memory_bytes",
    "required_disk_bytes",
    "available_docker_disk_bytes",
    "full_uat_contracts_passed",
}
_BOOLS = {
    "image_cache_verified",
    "scope_rechecked",
    "full_saga_accepted",
    "galdr_eager",
    "all_installed_rows_protected",
    "secure_context",
    "contact_activated",
    "email_sent",
    "automated_path_within_proposed_target",
    "public_trace_is_derivative",
    "binary_images_unchanged",
    "raw_trace_exported",
    "original_native_video",
    "private_output_exported",
    "domain_unchanged",
    "pixels_nonuniform",
    "blank_originals_private",
    "trace_screenshots",
    "trace_snapshots",
    "trace_sources",
}
_HASHES = {
    "sha256",
    "fixture_sha256",
    "domain_sha256",
    "original_sha256",
    "public_sha256",
    "actual_clipboard_sha256",
    "s04_source_sha256",
    "browser_control_sha256",
    "fixture_control_sha256",
}
_CLOSED_REPORTS = {
    "resource-receipt.json",
    "health.json",
    "public-copy.json",
    "seed-receipt.json",
    "post-browser-state.json",
    "source-identity.json",
    "image-source-verification.json",
    "source-manifest.json",
    "browser-readiness.json",
    "browser-failure.json",
    "runtime-isolation.json",
    "capacity.json",
    "runtime-failure.json",
    "saga-oracle.json",
    "saga-browser.json",
    "saga-effects.json",
    "saga-failure.json",
    "saga-trace-provenance.json",
    "saga-visual-oracle.json",
    "saga-visual-browser.json",
    "saga-visual-effects.json",
    "saga-visual-failure.json",
    "saga-visual-video.json",
    "saga-summary-oracle.json",
    "saga-summary-browser.json",
    "saga-summary-effects.json",
    "saga-summary-failure.json",
    "saga-summary-mail-preview.json",
    "suite-readonly-oracle.json",
    "suite-readonly-browser.json",
    "suite-readonly-effects.json",
    "control-identity.json",
    "owned-cleanup.json",
    "capture-rejections.json",
    "browser-trace-provenance.json",
}
_STEPS = {
    "nomination": (
        "E02-design",
        "E03-sofia",
        "E04-maria",
        "E06-public-release",
        "E06-workflow",
        "E07-unsent-contact",
    ),
    "copy-maria": (
        "own-summary-8200",
        "own-summary-8205",
        "native-clipboard",
        "maria-after",
        "mike-after",
    ),
    "copy-guest": ("native-clipboard", "maria-after", "mike-after"),
    "copy-self": ("native-clipboard", "mike-after"),
    "summary-acceptance": (
        "C01-own-8200",
        "C02-keyboard-preview",
        "C02-keyboard-expanded",
        "C03-reviewed",
        "C03-refreshed-8200",
        "C04-confirm",
        "C04-accepted",
        "C05-public-8700",
        "C05-own-8700",
    ),
}
_SIZES = (
    (1280, 800),
    (1920, 1080),
    (1512, 982),
    (768, 1024),
    (1024, 768),
    (390, 844),
    (360, 800),
)
_GUEST_STEPS = {
    "G01-design",
    "G01-detail",
    "G02-list-hover",
    "G02-list-keyboard",
    "G02-detail-hover",
    "G02-detail-keyboard",
    "G03-playbook",
    "G03-workflow",
    "G04-other",
    "G04-nberg",
    "G04-no-such-cedar-user",
}


def allowed_name(path: Path) -> bool:
    """Admit only closed producer files and exact case/step/size combinations.

    :param path: Relative output member.
    :return: Whether its exact spelling is reviewed.
    """
    name = path.as_posix()
    if name in _CLOSED_REPORTS or name in {
        "saga-trace.zip",
        "browser-trace.zip",
        "screenshots/guest-native-clipboard.png",
    }:
        return True
    if re.fullmatch(r"video/(?:page@)?[a-f0-9]{32}\.webm", name):
        return True
    return name in capture_names()


def capture_names() -> set[str]:
    """Enumerate exact native acquisition paths; no arbitrary step wildcard.

    :return: Finite reviewed JSON/PNG names.
    """
    return _step_capture_names() | _size_capture_names()


def _step_capture_names() -> set[str]:
    """Enumerate source-owned UAT step acquisitions.

    :return: Exact finite step image/metadata names.
    """
    result = set()
    for case, steps in _STEPS.items():
        for step in steps:
            for attempt in (1, 2):
                stem = f"saga-{case}-{step}-attempt-{attempt}"
                result.update({stem + ".json", "screenshots/" + stem + ".png"})
                result.update(
                    {stem + "-viewport.json", "screenshots/" + stem + "-viewport.png"}
                )
    return result


def _size_capture_names() -> set[str]:
    """Enumerate source-owned seven-size screenshots and trace chunks.

    :return: Exact finite matrix image/trace/metadata names.
    """
    result = set()
    for width, height in _SIZES:
        result.update(
            {
                f"traces/guest-public-{width}-{height}.zip",
                f"traces/guest-public-{width}-{height}.provenance.json",
            }
        )
        for screen in ("list", "profile"):
            for attempt in (1, 2):
                stem = f"guest-{screen}-{width}-{height}-attempt-{attempt}"
                result.update({stem + ".json", "screenshots/" + stem + ".png"})
        for case in ("long_identity_and_prose", "missing_summary"):
            stem = f"visual-{case}-{width}-{height}.png"
            result.update({stem + ".json", "screenshots/" + stem})
        result.update(
            f"screenshots/elena-{width}-{height}/{screen}.png"
            for screen in ("list", "detail")
        )
        result.update(
            f"screenshots/guest-{width}-{height}/{step}.png" for step in _GUEST_STEPS
        )
    return result | _native_capture_names()


def _native_capture_names() -> set[str]:
    """Declare only paired native guest captures for the six reviewed UI states.

    :return: Exact seven-size native PNG and geometry-sidecar paths.
    """
    steps = (
        "G01-design",
        "G01-detail",
        "G02-list-hover",
        "G02-list-keyboard",
        "G02-detail-hover",
        "G02-detail-keyboard",
    )
    return {
        f"screenshots/guest-{w}-{h}/{step}-viewport.png{suffix}"
        for w, h in _SIZES
        for step in steps
        for suffix in ("", ".json")
    }


def _owned_regular_file(path: Path, root: Path) -> None:
    """Reject aliases, links and foreign files before reading actual evidence bytes.

    :param path: Exact constructed owned evidence path.
    :param root: Positively owned invocation root.
    :return: None only for an owned regular unlinked actual file beneath root.
    :raises ValueError: Type, ownership, alias or hardlink topology differs.
    """
    info = path.lstat()
    if (
        not path.is_relative_to(root)
        or path.resolve() != path
        or not stat.S_ISREG(info.st_mode)
        or info.st_nlink != 1
        or info.st_uid != os.getuid()
    ):
        raise ValueError("Actual unlinked positively owned evidence file required.")


def _check_evidence_topology(root: Path) -> None:
    """Reject every incoming alias before relocating, reading or transforming it.

    :param root: Owned runtime root.
    :return: None after public and private evidence topology is safe.
    :raises ValueError: Any link, foreign owner or special file is present.
    """
    if root.resolve() != root or root.stat().st_uid != os.getuid():
        raise ValueError("Actual owned evidence root required.")
    for base in (root / "output", root / "private-evidence"):
        if not base.exists() and not base.is_symlink():
            continue
        if (
            base.is_symlink()
            or base.resolve() != base
            or not base.is_dir()
            or base.stat().st_uid != os.getuid()
        ):
            raise ValueError("Actual unlinked owned evidence directory required.")
        for path in base.rglob("*"):
            info = path.lstat()
            if path.resolve() != path or info.st_uid != os.getuid():
                raise ValueError("Evidence cannot borrow aliases or foreign owners.")
            if stat.S_ISREG(info.st_mode):
                _owned_regular_file(path, root)
            elif not stat.S_ISDIR(info.st_mode):
                raise ValueError(
                    "Evidence accepts only owned regular files/directories."
                )


def move_private(root: Path) -> None:
    """Move raw browser evidence outside the exporter before admission.

    :param root: Owned runtime root.
    :return: None after private originals are isolated.
    :raises ValueError: Linked or conflicting destinations.
    """
    destination = root / "private-evidence"
    if destination.is_symlink() or root.resolve() != root:
        raise ValueError("Owned unlinked evidence root required.")
    destination.mkdir(mode=0o700, exist_ok=True)
    source = root / "output/private"
    if source.exists() or source.is_symlink():
        if (
            source.is_symlink()
            or not source.is_dir()
            or (destination / "browser").exists()
        ):
            raise ValueError("Private evidence must move once without aliases.")
        source.rename(destination / "browser")


def _typed_fields(record: dict[str, Any]) -> dict[str, Any]:
    """Project only finite primitive fields; arbitrary original text never escapes.

    :param record: Parsed untrusted producer object.
    :return: Typed public facts.
    :raises ValueError: A selected field has unreviewed type or value.
    """
    result = {}
    for key, value in record.items():
        if key in _INTS:
            if type(value) is not int or not 0 <= value <= 2**63 - 1:
                raise ValueError("Receipt integer is outside its closed type.")
            result[key] = value
        elif key in _BOOLS:
            if type(value) is not bool or (
                key in {"full_saga_accepted", "raw_trace_exported"} and value
            ):
                raise ValueError("Receipt boolean exceeds preparation authority.")
            result[key] = value
        elif key in _HASHES:
            if not isinstance(value, str) or not re.fullmatch(r"[a-f0-9]{64}", value):
                raise ValueError("Receipt digest is malformed.")
            result[key] = value
    return result


def public_receipt(
    name: str, record: dict[str, Any], original: bytes
) -> dict[str, Any]:
    """Emit reviewed typed facts with the untouched original's exact hash.

    :param name: Closed admitted JSON filename.
    :param record: Parsed actual receipt.
    :param original: Exact original bytes retained privately.
    :return: Safe canonical derivative; arbitrary strings and nested bodies omitted.
    :raises ValueError: Invalid content or unreviewed receipt identity.
    """
    if not allowed_name(Path(name)) or not isinstance(record, dict):
        raise ValueError("Closed typed public receipt required.")
    result = _typed_fields(record)
    _selected_identity(record, result)
    _selected_observations(record, result)
    _matrix_fields(record, result)
    _capture_fields(record, result)
    _step_fields(record, result)
    _geometry_fields(record, result)
    _rejection_fields(record, result)
    protocol_fields(record, result)
    if name.endswith("effects.json"):
        _check_effects(record)
    if "failure" in name:
        _failure_fields(record, result)
    if name == "saga-summary-mail-preview.json":
        _mail_fields(record, result)
    if "original_sha256" in result:
        result["source_original_sha256"] = result["original_sha256"]
    result.update(
        derivative=True,
        original_sha256=hashlib.sha256(original).hexdigest(),
        receipt=name,
        raw_metadata_exported=False,
    )
    return result


def _selected_identity(record: dict[str, Any], result: dict[str, Any]) -> None:
    """Validate closed case/status and immutable candidate/control SHA fields.

    :param record: Original receipt.
    :param result: Typed derivative under construction.
    :return: None after selected identity fields validate.
    :raises ValueError: Unreviewed strings or fake statuses.
    """
    for key in ("status", "case", "exception_class"):
        if key not in record:
            continue
        allowed = _identity_values(key)
        if type(record[key]) is not str or record[key] not in allowed:
            raise ValueError("Unreviewed receipt identity value.")
        result[key] = record[key]
    for key in (
        "source_revision",
        "application_source_revision",
        "revision",
        "control_revision",
        "s04_source_blob",
    ):
        if key in record:
            if not isinstance(record[key], str) or not re.fullmatch(
                r"[a-f0-9]{40}", record[key]
            ):
                raise ValueError("Exact immutable revision required.")
            result[key] = record[key]


def _identity_values(key: str) -> set[str]:
    """Return only the closed values for one selected receipt field.

    :param key: Fixed status, case or exception_class field.
    :return: Reviewed finite identity values.
    """
    if key == "status":
        return _STATUSES
    if key == "exception_class":
        return _EXCEPTIONS
    captures = {
        f"guest-{screen}-{w}-{h}" for w, h in _SIZES for screen in ("list", "profile")
    }
    return {row.case for row in FULL_CASES} | captures


def _selected_observations(record: dict[str, Any], result: dict[str, Any]) -> None:
    """Keep measured geometry/time and exact fictional nomination, never raw URLs.

    :param record: Original parsed receipt.
    :param result: Derivative being constructed.
    :return: None after selected observation types validate.
    :raises ValueError: Invalid timing, viewport or nomination text.
    """
    if "secure_context" in record and record["secure_context"] is not True:
        raise ValueError("Actual secure browser context required.")
    if "viewport" in record:
        viewport = record["viewport"]
        if (
            not isinstance(viewport, dict)
            or set(viewport) != {"width", "height"}
            or (viewport["width"], viewport["height"]) not in _SIZES
        ):
            raise ValueError("Exact IA viewport required.")
        result["viewport"] = viewport
    for key in ("elapsed_monotonic_seconds", "elapsed_seconds"):
        if key in record:
            value = record[key]
            if type(value) not in (int, float) or not 0 <= value <= 720:
                raise ValueError("Actual bounded monotonic time required.")
            result[key] = value
    _nomination_fields(record, result)


def _nomination_fields(record: dict[str, Any], result: dict[str, Any]) -> None:
    """Retain only the exact observed fictional nomination and unsent destination.

    :param record: Original actual task observation.
    :param result: Typed public derivative.
    :return: None after exact public fixture text validation.
    :raises ValueError: Unknown nomination prose or contact destination differs.
    """
    if "inspected_contact_destination" in record:
        if (
            record["inspected_contact_destination"]
            != "mailto:maria.rodriguez@example.com"
        ):
            raise ValueError("Exact inspected fictional contact destination required.")
        result["inspected_contact_destination"] = record[
            "inspected_contact_destination"
        ]
    if "nomination_text" in record:
        text = "I nominate Maria Rodriguez for a discussion about Noor's Cedar bank onboarding brief. Her Accessibility Audit Playbook v1.0 includes Trace Keyboard Focus, Review Form Feedback, Document Recovery Paths. These public examples address keyboard navigation, understandable form errors and recovery. Next step is to request a discussion. Availability is unconfirmed."
        if record["nomination_text"] != text:
            raise ValueError("Exact fictional observed nomination required.")
        result["nomination_text"] = text


def _matrix_fields(record: dict[str, Any], result: dict[str, Any]) -> None:
    """Retain exact measured seven-size matrix observations without nested bodies.

    :param record: Actual browser metadata.
    :param result: Public derivative.
    :return: None after actual measured sizes/count agree with the declared IA.
    :raises ValueError: Missing, repeated, untyped or relabelled dimensions.
    """
    expected = [{"width": w, "height": h} for w, h in _SIZES]
    if "screens" in record:
        screens = record["screens"]
        if not isinstance(screens, list) or len(screens) != 7:
            raise ValueError("Exact seven measured screens required.")
        measured = [row["viewport"] for row in screens]
        if measured != expected:
            raise ValueError("Exact measured IA size sequence required.")
        result.update(viewport_count=7, viewports=measured)
    if "viewports" in record:
        if record["viewports"] != expected or record.get("viewport_count") != 7:
            raise ValueError("Exact measured IA size sequence/count required.")
        result["viewports"] = record["viewports"]


def _capture_fields(record: dict[str, Any], result: dict[str, Any]) -> None:
    """Validate exact actual font families and explicit capture geometry labels.

    :param record: Actual capture metadata.
    :param result: Safe public projection.
    :return: None after font and capture labels agree with reviewed acquisition.
    :raises ValueError: Unreviewed strings or fabricated geometry label.
    """
    if "fonts" in record:
        fonts = record["fonts"]
        if not isinstance(fonts, list) or any(
            value not in {"Montserrat", "Font Awesome 6 Pro", "Font Awesome 6 Brands"}
            for value in fonts
        ):
            raise ValueError("Closed actual font family list required.")
        result["fonts"] = fonts
    if "pixels_nonuniform" in record and record["pixels_nonuniform"] is not True:
        raise ValueError("Actual public frame must contain visible pixel variation.")
    if "capture_kind" in record:
        if record["capture_kind"] not in {"full_document", "native_viewport"}:
            raise ValueError("Closed native capture label required.")
        result["capture_kind"] = record["capture_kind"]
    if "modal_viewport_acquired" in record:
        if type(record["modal_viewport_acquired"]) is not bool:
            raise ValueError("Actual modal acquisition boolean required.")
        result["modal_viewport_acquired"] = record["modal_viewport_acquired"]


def _geometry_fields(record: dict[str, Any], result: dict[str, Any]) -> None:
    """Retain only actual numeric native navbar and tooltip geometry.

    :param record: Parsed original viewport acquisition facts.
    :param result: Typed public derivative.
    :return: None after exact shape/type/bounds checks.
    :raises ValueError: Untrusted metadata attempts to export strings or extra fields.
    """
    if "capture_scroll_y" in record:
        value = record["capture_scroll_y"]
        if type(value) not in (int, float) or not 0 <= value <= 100000:
            raise ValueError("Actual numeric viewport scroll coordinate required.")
        result["capture_scroll_y"] = value
    for key in ("navbar_geometry", "tooltip_geometry"):
        if key not in record:
            continue
        box = record[key]
        if box is None:
            result[key] = None
            continue
        if (
            not isinstance(box, dict)
            or set(box) != {"x", "y", "width", "height"}
            or any(
                type(value) not in (int, float) or not -100000 <= value <= 100000
                for value in box.values()
            )
        ):
            raise ValueError("Closed actual numeric native geometry required.")
        result[key] = box


def _rejection_fields(record: dict[str, Any], result: dict[str, Any]) -> None:
    """Retain only the closed count/hash proof of privately quarantined blanks.

    :param record: Actual rejection metadata.
    :param result: Safe derivative.
    :return: None after exact bounded hash list validation.
    :raises ValueError: Unknown private bytes or inconsistent counts.
    """
    if "rejected_capture_sha256" not in record:
        return
    hashes = record["rejected_capture_sha256"]
    if (
        not isinstance(hashes, list)
        or not 0 < len(hashes) <= 128
        or record.get("rejected_captures") != len(hashes)
        or record.get("blank_originals_private") is not True
        or any(
            not isinstance(value, str) or not re.fullmatch(r"[a-f0-9]{64}", value)
            for value in hashes
        )
    ):
        raise ValueError("Bounded actual blank-original hash proof required.")
    result["rejected_capture_sha256"] = hashes


def _step_fields(record: dict[str, Any], result: dict[str, Any]) -> None:
    """Retain only the literal completed UAT step sequence produced by this lane.

    :param record: Actual browser observation.
    :param result: Public derivative.
    :return: None after the exact literal step declaration validates.
    :raises ValueError: A caller invents or relabels completed steps.
    """
    if "completed_steps" not in record:
        return
    expected = {
        "guest-public": ["G01", "G02", "G03", "G04"],
        "authenticated-matrix": [],
        "summary-acceptance": ["C01", "C02", "C03", "C04", "C05"],
    }
    if (
        record.get("case") not in expected
        or record["completed_steps"] != expected[record["case"]]
    ):
        raise ValueError("Exact literal completed UAT step sequence required.")
    result["completed_steps"] = record["completed_steps"]


def _check_effects(record: dict[str, Any]) -> None:
    """Require exact per-case award proof rather than a caller's pass label.

    :param record: Actual producer verification receipt.
    :return: None after mandatory guard/counts agree.
    :raises ValueError: Success claim or effect count differs.
    """
    case = record.get("case")
    if case not in {row.case for row in FULL_CASES if row.case != "core"}:
        raise ValueError("True implemented effect case required.")
    expected = 2 if case == "copy-maria" else (1 if case == "summary-acceptance" else 0)
    if (
        record.get("status") != "CASE_VERIFIED"
        or record.get("scope_rechecked") is not True
        or type(record.get("new_awards")) is not int
        or record["new_awards"] != expected
        or record.get("full_saga_accepted") is not False
    ):
        raise ValueError("Exact verified per-case effects required.")
    _case_effect_facts(record, case)


def _case_effect_facts(record: dict[str, Any], case: str) -> None:
    """Require exact real summary additions and unchanged readonly model/mail counts.

    :param record: Received or freshly produced actual effects.
    :param case: Validated true case.
    :return: None after mandatory exact numeric and boolean lane facts agree.
    :raises ValueError: A claimed effect count, scheduler or coverage differs.
    """
    facts: dict[str, Any] = {}
    if case == "summary-acceptance":
        facts = {
            "new_activities": 1,
            "new_versions": 1,
            "decision_mail_files": 1,
            "provider_calls": 2,
            "galdr_eager": False,
            "all_installed_rows_protected": True,
        }
    elif case in {
        "guest-public",
        "authenticated-matrix",
        "long_identity_and_prose",
        "missing_summary",
    }:
        facts = {"model_count": 39, "decision_mail_files": 0}
    elif "decision_mail_files" in record:
        facts["decision_mail_files"] = 0
    if "model_count" in record:
        facts["model_count"] = 39
    if any(
        type(record.get(key)) is not type(value) or record.get(key) != value
        for key, value in facts.items()
    ):
        raise ValueError("Exact mandatory lane effect facts required.")


def _failure_fields(record: dict[str, Any], result: dict[str, Any]) -> None:
    """Convert raw denied paths to counts while preserving actual failure status.

    :param record: Private original failure metadata.
    :param result: Safe derivative.
    :return: None after a fixed exception classification and count are emitted.
    :raises ValueError: A purported failure lacks typed actual classification.
    """
    if (
        record.get("status") != "FAILED"
        or record.get("exception_class") not in _EXCEPTIONS
    ):
        raise ValueError("Typed actual failure required.")
    requests = record.get("undeclared_requests", [])
    if not isinstance(requests, list) or len(requests) > 10000:
        raise ValueError("Bounded denied-request list required.")
    result["undeclared_request_count"] = len(requests)


def _mail_fields(record: dict[str, Any], result: dict[str, Any]) -> None:
    """Validate the actual mail derivative's closed safe fixture text.

    :param record: Parsed generated preview.
    :param result: Public projection.
    :return: None after fixed allowed text is copied.
    :raises ValueError: Preview differs from verified fictional acceptance facts.
    """
    expected = {
        "evidence_kind": "actual_file_mail_preview",
        "recipient": "maria.rodriguez@example.com",
        "subject": 'Your PIP "Screen Reader Error Recovery" — Accepted ✓',
        "operation": "ADD Activity",
        "activity": "Screen Reader Error Recovery",
        "version": "3.0",
        "body_excerpt": 'ADD Activity "Screen Reader Error Recovery"\nDecision: ACCEPT\nis now v3.0',
        "raw_headers_exported": False,
    }
    if (
        any(record.get(key) != value for key, value in expected.items())
        or record.get("derivative") is not True
    ):
        raise ValueError("Verified closed real file-mail preview required.")
    result.update(expected)
    result["original_message_sha256"] = record["original_sha256"]


def prepare_public(root: Path, manifest: dict[str, Any]) -> None:
    """Isolate originals, project typed reports, and validate all trace members.

    :param root: Positively owned runtime directory.
    :param manifest: Authenticated runtime identity.
    :return: None only after the complete public subtree is safe.
    :raises ValueError: Any member, receipt or trace fails content admission.
    """
    _check_evidence_topology(root)
    move_private(root)
    output, private = root / "output", root / "private-evidence"
    reports = private / "reports"
    reports.mkdir(mode=0o700)
    secrets = _private_values(root)
    _core_trace(root, secrets)
    _check_trace(root, secrets)
    for path in list(output.rglob("*.json")):
        name = path.relative_to(output).as_posix()
        if (
            not allowed_name(Path(name))
            or path.is_symlink()
            or path.stat().st_nlink != 1
        ):
            raise ValueError("Unreviewed receipt file.")
        raw = path.read_bytes()
        target = reports / name
        target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        path.rename(target)
        try:
            record = json.loads(raw)
        except (ValueError, UnicodeDecodeError):
            record = None
        derivative = _admit_receipt(name, record, raw, manifest)
        write_public_receipt(path, derivative)
    _scan_public(output, secrets)


def _admit_receipt(
    name: str, record: Any, raw: bytes, manifest: dict[str, Any]
) -> dict[str, Any]:
    """Preserve rejected content privately and emit a typed explicit failed derivative.

    :param name: Already admitted closed filename.
    :param record: Parsed original actual receipt.
    :param raw: Untouched private bytes.
    :param manifest: Authenticated invocation.
    :return: Valid typed projection or safe FAILED admission receipt.
    """
    try:
        return _special_receipt(name, record, raw, manifest)
    except (ValueError, TypeError, KeyError, AssertionError):
        return {
            "derivative": True,
            "status": "FAILED",
            "exception_class": "ValueError",
            "original_sha256": hashlib.sha256(raw).hexdigest(),
            "receipt_content_rejected": True,
            "raw_metadata_exported": False,
        }


def _special_receipt(
    name: str, record: Any, raw: bytes, manifest: dict[str, Any]
) -> dict[str, Any]:
    """Admit canonical measured resources or retain the existing receipt contracts.

    :param name: Exact reviewed receipt filename.
    :param record: Parsed original object.
    :param raw: Exact original bytes before parsing.
    :param manifest: Authenticated lifecycle identity.
    :return: Closed source-bound safe derivative.
    :raises ValueError: Exact byte/identity/resource admission differs.
    """
    if name == "runtime-failure.json":
        phase, frames = resource_profile.checked_failure(record)
        result = public_receipt(name, record, raw)
        result.update(phase=phase, source_frames=frames)
        return result
    if name == "resource-receipt.json":
        checked = resource_profile.checked_receipt(
            raw, manifest, passing=record.get("status") == "VERIFIED"
        )
        return {
            **checked,
            "derivative": True,
            "original_sha256": hashlib.sha256(raw).hexdigest(),
        }
    return _ordinary_receipt(name, record, raw, manifest)


def _ordinary_receipt(
    name: str, record: Any, raw: bytes, manifest: dict[str, Any]
) -> dict[str, Any]:
    """Bind source/control facts to authenticated declarations, not raw contents.

    :param name: Exact admitted original filename.
    :param record: Parsed original object.
    :param raw: Exact original bytes.
    :param manifest: Authenticated invocation contract.
    :return: Checked identity or ordinary typed derivative.
    :raises ValueError: Identity/content differs.
    """
    if name == "runtime-isolation.json":
        return _isolation_receipt(record, raw, manifest)
    result = public_receipt(name, record, raw)
    if name == "source-identity.json":
        bind_source_identity(record, result, manifest)
    if name in {"source-manifest.json", "control-identity.json"}:
        declaration = (
            "source.json" if name == "source-manifest.json" else "controls.json"
        )
        expected = json.loads((Path(__file__).parent / declaration).read_text())
        if record != expected:
            raise ValueError(
                "Source/control declaration differs from authenticated bundle."
            )
        result["declaration"] = expected
    return result


def _isolation_receipt(
    record: Any, raw: bytes, manifest: dict[str, Any]
) -> dict[str, Any]:
    """Validate numeric bounds and immutable source images of every actual role.

    :param record: Actual original Docker inspection projections.
    :param raw: Exact original bytes.
    :param manifest: Authenticated candidate and browser digests.
    :return: Typed exact role facts; no ambient configuration or credentials.
    :raises ValueError: Any role, image, network, memory or CPU differs.
    """
    if (
        not isinstance(record, list)
        or len(record) != 3
        or not all(isinstance(row, dict) for row in record)
        or {r.get("role") for r in record} != {"web", "db", "browser"}
    ):
        raise ValueError("Actual three-role isolation receipt required.")
    facts = [_isolation_role(row, manifest) for row in record]
    return {
        "derivative": True,
        "roles": facts,
        "original_sha256": hashlib.sha256(raw).hexdigest(),
    }


def _isolation_role(row: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    """Check one actual immutable role and its unchanged resource ceilings.

    :param row: Actual Docker projection.
    :param manifest: Authenticated images.
    :return: Typed public runtime identity facts.
    :raises ValueError: Actual identity or numeric ceilings differ.
    """
    limits = {
        "web": (384, 750000000),
        "db": (192, 250000000),
        "browser": (768 if resource_profile.selected(manifest) else 512, 1000000000),
    }
    role = row["role"]
    image_key = "postgres_image" if role == "db" else role + "_image"
    if (
        row["image"] != manifest[image_key]
        or type(row["memory_bytes"]) is not int
        or row["memory_bytes"] != limits[role][0] * 1024**2
        or row["nano_cpus"] != limits[role][1]
    ):
        raise ValueError("Actual role identity or enforced resource ceiling differs.")
    return {key: row[key] for key in ("role", "image", "memory_bytes", "nano_cpus")}


def _private_values(root: Path) -> tuple[bytes, ...]:
    """Read actual captured secrets privately for all-member export scanning.

    :param root: Verified owned invocation root.
    :return: Encoded actual private values, never exported.
    """
    values = {"Cedar-fictional-tests-only-2026"}
    captured = root / "private-evidence/browser/captured-secrets.json"
    if captured.exists():
        _owned_regular_file(captured, root)
        values.update(json.loads(captured.read_text())["values"])
    environment = root / "app.env"
    if environment.exists():
        _owned_regular_file(environment, root)
        values.update(
            line.partition("=")[2]
            for line in environment.read_text().splitlines()
            if line.startswith(("DJANGO_SECRET_KEY=", "DATABASE_URL="))
        )
    encoded = {base64.b64encode(value.encode()).decode() for value in values}
    encoded.update(
        base64.urlsafe_b64encode(value.encode()).decode() for value in values
    )
    return encode_private_values(values | encoded)


def _core_trace(root: Path, secrets: tuple[bytes, ...]) -> None:
    """Convert legacy anonymous core trace into an explicitly safe derivative.

    :param root: Owned runtime root after private relocation.
    :param secrets: Actual private values and encodings.
    :return: None after core original is private and all-member scan succeeds.
    :raises ValueError: Unsafe original member or surviving private value.
    """
    public = root / "output/browser-trace.zip"
    if not public.exists() and not public.is_symlink():
        return
    _owned_regular_file(public, root)
    folder = root / "private-evidence/browser"
    folder.mkdir(mode=0o700, exist_ok=True)
    original = folder / "browser-trace-original.zip"
    provenance = root / "output/browser-trace-provenance.json"
    if (
        original.exists()
        or original.is_symlink()
        or provenance.exists()
        or provenance.is_symlink()
    ):
        raise ValueError("Original trace/provenance cannot be replaced.")
    public.rename(original)
    os.chmod(original, 0o600)
    changed, members = write_redacted(original, public, secrets)
    verify_redacted(public, secrets)
    record = {
        **trace_provenance(original, public),
        "redacted_members": changed,
        "members": members,
    }
    with provenance.open("x") as stream:
        json.dump(record, stream)


def _check_trace(root: Path, secrets: tuple[bytes, ...]) -> None:
    """Bind derivative hashes and preserve every original binary image resource.

    :param root: Owned invocation root after private relocation.
    :param secrets: Actual raw and encoded private values.
    :return: None after every public ZIP member is checked.
    :raises ValueError: Missing provenance, private value or changed image.
    """
    pairs = [
        ("saga-trace.zip", "saga-trace-original.zip", "saga-trace-provenance.json")
    ]
    pairs.extend(
        (
            f"traces/guest-public-{w}-{h}.zip",
            f"guest-public-{w}-{h}-trace-original.zip",
            f"traces/guest-public-{w}-{h}.provenance.json",
        )
        for w, h in _SIZES
    )
    for public, original, provenance in pairs:
        if (root / "output" / public).exists():
            _trace_pair(
                root,
                root / "output" / public,
                root / "private-evidence/browser" / original,
                root / "output" / provenance,
                secrets,
            )


def _trace_pair(
    root: Path,
    public: Path,
    original: Path,
    provenance: Path,
    secrets: tuple[bytes, ...],
) -> None:
    """Validate one actual safe derivative against its untouched private original.

    :param root: Exact positively owned invocation root.
    :param public: Actual safe derivative ZIP.
    :param original: Untouched private browser chunk.
    :param provenance: Actual matching JSON provenance.
    :param secrets: Captured private values/encodings.
    :return: None after hash, topology, all-member and binary image comparison.
    :raises ValueError: Any claimed fact differs from original actual bytes.
    """
    record = json.loads(provenance.read_text())
    if (
        record.get("public_sha256") != hashlib.sha256(public.read_bytes()).hexdigest()
        or record.get("original_sha256")
        != hashlib.sha256(original.read_bytes()).hexdigest()
        or record.get("raw_trace_exported") is not False
        or record.get("binary_images_unchanged") is not True
    ):
        raise ValueError("Actual derivative/original trace provenance differs.")
    verify_redacted(public, secrets)
    with zipfile.ZipFile(original) as raw, zipfile.ZipFile(public) as safe:
        validate_members(safe.infolist())
        if set(raw.namelist()) != set(safe.namelist()):
            raise ValueError("Trace member set changed.")
        for name in raw.namelist():
            data = raw.read(name)
            if data.startswith((b"\x89PNG", b"\xff\xd8\xff")) and data != safe.read(
                name
            ):
                raise ValueError("Original binary screenshot resource changed.")


def _scan_public(output: Path, secrets: tuple[bytes, ...]) -> None:
    """Scan all public file names/bytes and every decompressed ZIP member.

    :param output: Only the public exporter root.
    :param secrets: Actual raw and encoded private values.
    :return: None after all-member admission.
    :raises ValueError: Any private value, link or undeclared file survives.
    """
    for path in output.rglob("*"):
        if path.is_symlink():
            raise ValueError("No public links allowed.")
        if not path.is_file():
            continue
        if not allowed_name(path.relative_to(output)) or path.stat().st_nlink != 1:
            raise ValueError("No undeclared public member allowed.")
        if any(
            value in path.name.encode() or value in path.read_bytes()
            for value in secrets
        ):
            raise ValueError("Private value in public member.")
        if path.suffix == ".png" and not png_nonuniform(path):
            raise ValueError(
                "Uniform actual PNG cannot certify visible application content."
            )
        if path.suffix == ".zip":
            verify_redacted(path, secrets)


def write_public_receipt(path: Path, record: dict[str, Any]) -> None:
    """Write the resource derivative with exact canonical byte admission downstream.

    :param path: Already admitted positively owned output file.
    :param record: Closed safe derivative.
    :return: None after exact public bytes are written.
    """
    if path.name == "resource-receipt.json":
        path.write_bytes(resource_profile.canonical(record))
    else:
        path.write_text(json.dumps(record, indent=2) + "\n")


def bind_source_identity(
    record: dict[str, Any], result: dict[str, Any], manifest: dict[str, Any]
) -> None:
    """Bind the safe source derivative to the authenticated original invocation.

    :param record: Parsed original source receipt.
    :param result: Safe derivative under construction.
    :param manifest: Authenticated source/case/control declaration.
    :return: None after all declared identities agree.
    :raises ValueError: Original receipt cross-binds another invocation.
    """
    for key in (
        "source_revision",
        "build_run_id",
        "web_image",
        "browser_image",
        "nonce",
        "fixture_sha256",
        "suite_phase",
        "saga_case",
        "control_revision",
    ):
        if key in manifest:
            if record.get(key) != manifest[key]:
                raise ValueError("Actual source identity differs from invocation.")
            result[key] = manifest[key]
