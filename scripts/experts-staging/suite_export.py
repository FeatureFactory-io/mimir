"""Content-checked public derivatives; raw reports and traces remain private."""

from __future__ import annotations

import hashlib
import json
import re
import zipfile
from pathlib import Path
from typing import Any

from saga_trace import (
    encode_private_values,
    trace_provenance,
    validate_members,
    verify_redacted,
    write_redacted,
)
from suite_contract import FULL_CASES

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
    "available_memory_bytes",
    "available_docker_disk_bytes",
    "full_uat_contracts_passed",
}
_BOOLS = {
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
    if re.fullmatch(r"video/[a-f0-9]{32}\.webm", name):
        return True
    return name in capture_names()


def capture_names() -> set[str]:
    """Enumerate exact native acquisition paths; no arbitrary step wildcard.

    :return: Finite reviewed JSON/PNG names.
    """
    result = set()
    for case, steps in _STEPS.items():
        for step in steps:
            for attempt in (1, 2):
                stem = f"saga-{case}-{step}-attempt-{attempt}"
                result.update({stem + ".json", "screenshots/" + stem + ".png"})
                if step == "C04-confirm":
                    result.update(
                        {
                            stem + "-viewport.json",
                            "screenshots/" + stem + "-viewport.png",
                        }
                    )
    for width, height in _SIZES:
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
    return result


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
    _capture_fields(record, result)
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
        allowed = (
            _STATUSES
            if key == "status"
            else ({r.case for r in FULL_CASES} if key == "case" else _EXCEPTIONS)
        )
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


def _selected_observations(record: dict[str, Any], result: dict[str, Any]) -> None:
    """Keep measured geometry/time and exact fictional nomination, never raw URLs.

    :param record: Original parsed receipt.
    :param result: Derivative being constructed.
    :return: None after selected observation types validate.
    :raises ValueError: Invalid timing, viewport or nomination text.
    """
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
    if "nomination_text" in record:
        text = "I nominate Maria Rodriguez for a discussion about Noor's Cedar bank onboarding brief. Her Accessibility Audit Playbook v1.0 includes Trace Keyboard Focus, Review Form Feedback. These public examples address keyboard navigation, understandable form errors and recovery. Next step is to request a discussion. Availability is unconfirmed."
        if record["nomination_text"] != text:
            raise ValueError("Exact fictional observed nomination required.")
        result["nomination_text"] = text


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
    if "capture_kind" in record:
        if record["capture_kind"] not in {"full_document", "native_viewport"}:
            raise ValueError("Closed native capture label required.")
        result["capture_kind"] = record["capture_kind"]
    if "modal_viewport_acquired" in record:
        if type(record["modal_viewport_acquired"]) is not bool:
            raise ValueError("Actual modal acquisition boolean required.")
        result["modal_viewport_acquired"] = record["modal_viewport_acquired"]


def _check_effects(record: dict[str, Any]) -> None:
    """Require exact per-case award proof rather than a caller's pass label.

    :param record: Actual producer verification receipt.
    :return: None after mandatory guard/counts agree.
    :raises ValueError: Success claim or effect count differs.
    """
    expected = (
        2
        if record.get("case") == "copy-maria"
        else (1 if record.get("case") == "summary-acceptance" else 0)
    )
    if (
        record.get("status") != "CASE_VERIFIED"
        or record.get("scope_rechecked") is not True
        or type(record.get("new_awards")) is not int
        or record["new_awards"] != expected
        or record.get("full_saga_accepted") is not False
    ):
        raise ValueError("Exact verified per-case effects required.")


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
        "subject": "Accepted",
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
        path.write_text(json.dumps(derivative, indent=2) + "\n")
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
        "browser": (512, 1000000000),
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
        values.update(json.loads(captured.read_text())["values"])
    environment = root / "app.env"
    if environment.exists():
        values.update(
            line.partition("=")[2]
            for line in environment.read_text().splitlines()
            if line.startswith(("DJANGO_SECRET_KEY=", "DATABASE_URL="))
        )
    return encode_private_values(values)


def _core_trace(root: Path, secrets: tuple[bytes, ...]) -> None:
    """Convert legacy anonymous core trace into an explicitly safe derivative.

    :param root: Owned runtime root after private relocation.
    :param secrets: Actual private values and encodings.
    :return: None after core original is private and all-member scan succeeds.
    :raises ValueError: Unsafe original member or surviving private value.
    """
    public = root / "output/browser-trace.zip"
    if not public.exists():
        return
    folder = root / "private-evidence/browser"
    folder.mkdir(mode=0o700, exist_ok=True)
    original = folder / "browser-trace-original.zip"
    public.rename(original)
    changed, members = write_redacted(original, public, secrets)
    verify_redacted(public, secrets)
    record = {
        **trace_provenance(original, public),
        "redacted_members": changed,
        "members": members,
    }
    (root / "output/browser-trace-provenance.json").write_text(json.dumps(record))


def _check_trace(root: Path, secrets: tuple[bytes, ...]) -> None:
    """Bind derivative hashes and preserve every original binary image resource.

    :param root: Owned invocation root after private relocation.
    :param secrets: Actual raw and encoded private values.
    :return: None after every public ZIP member is checked.
    :raises ValueError: Missing provenance, private value or changed image.
    """
    public = root / "output/saga-trace.zip"
    if not public.exists():
        return
    original = root / "private-evidence/browser/saga-trace-original.zip"
    record = json.loads((root / "output/saga-trace-provenance.json").read_text())
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
        if path.suffix == ".zip":
            verify_redacted(path, secrets)
