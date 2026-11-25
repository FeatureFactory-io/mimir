"""Independent local archive readback before owned private runtime disposal."""

from __future__ import annotations

import json
import re
import tarfile
from pathlib import Path
from typing import Any

from suite_contract import selected_case
from suite_export import allowed_name, public_receipt


def verify_case_archive(
    path: Path, manifest: dict[str, Any], *, require_pass: bool = True
) -> None:
    """Check actual downloaded closed archive and required case-specific verdicts.

    :param path: Actual hash-verified downloaded archive.
    :param manifest: Authenticated true case/source identity.
    :param require_pass: Also require successful case effects after safe transfer check.
    :return: None after independent artifact content and effect readback.
    :raises ValueError: Topology, identities or required case proof differs.
    """
    case = selected_case(manifest).case
    with tarfile.open(path, "r:gz") as archive:
        members = archive.getmembers()
        names = [m.name for m in members]
        if (
            len(names) != len(set(names))
            or any(
                not m.isfile()
                or not allowed_name(Path(m.name))
                or m.size > 128 * 1024**2
                for m in members
            )
            or sum(m.size for m in members) > 128 * 1024**2
        ):
            raise ValueError("Closed bounded archive required.")
        records = {
            m.name: json.loads(archive.extractfile(m).read())
            for m in members
            if m.name.endswith(".json")
        }
        _typed_records(records)
        _identity_record(records, manifest)
        if require_pass:
            _required_media(case, names)
            _required_records(case, records, manifest)


def _required_media(case: str, names: list[str]) -> None:
    """Require actual native media and all seven guest trace chunks on success.

    :param case: Closed true case.
    :param names: Exact downloaded file names.
    :return: None when required real media exists.
    :raises ValueError: A passing lane lacks original video/screenshots or traces.
    """
    if not any(
        re.fullmatch(r"video/(?:page@)?[a-f0-9]{32}\.webm", name) for name in names
    ) or not any(
        name.startswith("screenshots/") and name.endswith(".png") for name in names
    ):
        raise ValueError("Original native video and screenshots are required.")
    if case == "guest-public":
        sizes = (
            (1280, 800),
            (1920, 1080),
            (1512, 982),
            (768, 1024),
            (1024, 768),
            (390, 844),
            (360, 800),
        )
        required = {
            f"traces/guest-public-{w}-{h}{suffix}"
            for w, h in sizes
            for suffix in (".zip", ".provenance.json")
        }
        if not required <= set(names):
            raise ValueError("All seven actual guest viewport trace chunks required.")
    elif case != "core" and "saga-trace.zip" not in names:
        raise ValueError("Actual safe derivative trace required for every case.")


def _typed_records(records: dict[str, Any]) -> None:
    """Require every downloaded JSON member to be a content-admitted derivative.

    :param records: Exact parsed JSON archive members.
    :return: None after all original receipt hashes validate.
    :raises ValueError: Raw or untyped metadata appears.
    """
    for record in records.values():
        if (
            not isinstance(record, dict)
            or record.get("derivative") is not True
            or not re.fullmatch(r"[a-f0-9]{64}", str(record.get("original_sha256", "")))
        ):
            raise ValueError("Content-validated derivative receipts required.")


def _required_records(
    case: str, records: dict[str, Any], manifest: dict[str, Any]
) -> None:
    """Require exact real verification, keeping independent visual acceptance pending.

    :param case: Closed true case.
    :param records: Actual downloaded typed reports.
    :param manifest: Authenticated invocation identity.
    :return: None only with all lane-specific proof.
    :raises ValueError: Success is incomplete or any recorded failure exists.
    """
    if any(
        "failure" in name or record.get("status") == "FAILED"
        for name, record in records.items()
    ):
        raise ValueError("Original case failure cannot certify a suite lane.")
    if case == "core":
        if (
            records.get("browser-readiness.json", {}).get("status")
            != "SMOKE_ONLY_UAT_PENDING"
            or records.get("post-browser-state.json", {}).get("scope_rechecked")
            is not True
        ):
            raise ValueError("Actual core browser and effect proof required.")
        return
    _lane_records(case, records, manifest)


def _identity_record(records: dict[str, Any], manifest: dict[str, Any]) -> None:
    """Bind downloaded safe receipts to this actual candidate/control invocation.

    :param records: Actual content-validated records.
    :param manifest: Authenticated case/source identity.
    :return: None after exact identity comparison.
    :raises ValueError: Downloaded invocation differs.
    """
    identity = records.get("source-identity.json", {})
    if any(
        identity.get(key) != manifest.get(key)
        for key in (
            "source_revision",
            "build_run_id",
            "web_image",
            "browser_image",
            "fixture_sha256",
            "nonce",
            "suite_phase",
            "saga_case",
            "control_revision",
        )
    ):
        raise ValueError("Downloaded candidate/control/case identity differs.")
    _declaration_records(records, manifest)


def _declaration_records(records: dict[str, Any], manifest: dict[str, Any]) -> None:
    """Bind actual source/control declarations and emitted readiness source facts.

    :param records: Parsed actual archive reports.
    :param manifest: Authenticated current candidate/control identity and hash maps.
    :return: None after every emitted identity agrees with the current invocation.
    :raises ValueError: Any declaration or emitted readiness proof is cross-bound.
    """
    for filename, map_key, revision_key in (
        ("source-manifest.json", "source_files", "source_revision"),
        ("control-identity.json", "control_files", "control_revision"),
    ):
        if map_key in manifest:
            declaration = records.get(filename, {}).get("declaration", {})
            if (
                declaration.get(revision_key) != manifest[revision_key]
                or declaration.get("files") != manifest[map_key]
            ):
                raise ValueError(
                    "Downloaded exact source/control hash declaration differs."
                )
    _readiness_records(records, manifest)


def _readiness_records(records: dict[str, Any], manifest: dict[str, Any]) -> None:
    """Cross-bind emitted actual image-source and HTTPS readiness observations.

    :param records: Actual parsed archive reports.
    :param manifest: Exact authenticated candidate source/fixture declaration.
    :return: None after every emitted actual readiness source agrees.
    :raises ValueError: A source/fixture/health identity differs.
    """
    image = records.get("image-source-verification.json")
    if image is not None and (
        image.get("source_revision") != manifest["source_revision"]
        or image.get("fixture_sha256") != manifest["fixture_sha256"]
        or (
            "source_files" in manifest
            and image.get("verified_files") != len(manifest["source_files"])
        )
    ):
        raise ValueError(
            "Downloaded actual image-source proof differs from invocation."
        )
    health = records.get("health.json")
    if health is not None and (
        health.get("revision") != manifest["source_revision"]
        or health.get("status") != "healthy"
    ):
        raise ValueError("Downloaded actual health identity differs from invocation.")


def _lane_records(case: str, records: dict[str, Any], manifest: dict[str, Any]) -> None:
    """Check the actual lane-specific public browser and complete-effects receipts.

    :param case: Closed true lane ID.
    :param records: Actual parsed archive reports.
    :param manifest: Exact current fixture/source identity.
    :return: None after exact browser/effects and summary mail agree.
    :raises ValueError: The lane is incomplete or not verified.
    """
    prefixes = {
        "summary-acceptance": "saga-summary",
        "long_identity_and_prose": "saga-visual",
        "missing_summary": "saga-visual",
        "guest-public": "suite-readonly",
        "authenticated-matrix": "suite-readonly",
    }
    prefix = prefixes.get(case, "saga")
    effects = records.get(prefix + "-effects.json", {})
    browser = records.get(prefix + "-browser.json", {})
    if (
        effects.get("case") != case
        or effects.get("status") != "CASE_VERIFIED"
        or browser.get("case") != case
        or browser.get("status") != "BROWSER_OBSERVED"
    ):
        raise ValueError(
            "Actual lane-specific browser and whole-state effect proof required."
        )
    _received_semantics(prefix, effects, browser)
    _browser_facts(case, browser, records, manifest)
    if (
        case == "summary-acceptance"
        and records.get("saga-summary-mail-preview.json", {}).get("evidence_kind")
        != "actual_file_mail_preview"
    ):
        raise ValueError("Actual verified file-mail preview required.")


def _received_semantics(
    prefix: str, effects: dict[str, Any], browser: dict[str, Any]
) -> None:
    """Revalidate actual downloaded content, never rely on upstream pass labels.

    :param prefix: Closed lane receipt family.
    :param effects: Actual received numeric/domain verification.
    :param browser: Actual received native observations.
    :return: None only after exact effects, flags, protocol and metadata validation.
    :raises ValueError: Any received typed semantic fact differs.
    """
    try:
        public_receipt(prefix + "-effects.json", effects, json.dumps(effects).encode())
        public_receipt(prefix + "-browser.json", browser, json.dumps(browser).encode())
    except (AssertionError, KeyError, TypeError) as error:
        raise ValueError("Received lane semantic proof differs.") from error


def _browser_facts(
    case: str,
    browser: dict[str, Any],
    records: dict[str, Any],
    manifest: dict[str, Any],
) -> None:
    """Require complete source-bound actual native evidence for each true case.

    :param case: Closed true lane.
    :param browser: Actual received browser proof.
    :param records: Actual downloaded public reports.
    :param manifest: Authenticated expected fixture identity.
    :return: None after mandatory native actor/steps/sizes/outcomes agree.
    :raises ValueError: Missing, invented or cross-bound browser evidence.
    """
    if browser.get("fixture_sha256") != manifest.get("fixture_sha256"):
        raise ValueError("Actual browser fixture proof differs.")
    if case == "summary-acceptance":
        if (
            browser.get("completed_steps") != ["C01", "C02", "C03", "C04", "C05"]
            or len(browser.get("login_observations", [])) != 3
        ):
            raise ValueError(
                "Actual complete summary steps and native logins required."
            )
    elif case in {
        "guest-public",
        "authenticated-matrix",
        "long_identity_and_prose",
        "missing_summary",
    }:
        _matrix_browser_facts(case, browser)
    else:
        _legacy_browser_facts(case, browser, records)


def _matrix_browser_facts(case: str, browser: dict[str, Any]) -> None:
    """Require actual seven-size and actor evidence, preserving preparation status.

    :param case: Closed true readonly or visual case.
    :param browser: Received typed browser record.
    :return: None after exact actual IA count/sequence and actor metadata exist.
    :raises ValueError: Any complete matrix evidence is missing.
    """
    sizes = (
        (1280, 800),
        (1920, 1080),
        (1512, 982),
        (768, 1024),
        (1024, 768),
        (390, 844),
        (360, 800),
    )
    if (
        browser.get("viewport_count") != 7
        or browser.get("viewports") != [{"width": w, "height": h} for w, h in sizes]
        or "login_observation" not in browser
    ):
        raise ValueError("Actual complete source-bound seven-size matrix required.")
    if case == "guest-public" and browser.get("completed_steps") != [
        "G01",
        "G02",
        "G03",
        "G04",
    ]:
        raise ValueError("Actual complete guest UAT steps required.")


def _legacy_browser_facts(
    case: str, browser: dict[str, Any], records: dict[str, Any]
) -> None:
    """Require actual nomination or native clipboard evidence and exact actor traffic.

    :param case: Closed nomination/copy case.
    :param browser: Received native observation.
    :param records: Actual public prompt digest oracle and other reports.
    :return: None after mandatory actual task outcome and no external send agree.
    :raises ValueError: Missing or mismatched native evidence.
    """
    if not {
        "login_observation",
        "receipt_attempts",
        "nonread_requests",
    } <= browser.keys() or browser.get("viewport") != {"width": 1280, "height": 800}:
        raise ValueError("Actual actor-bound native observations required.")
    if case == "nomination":
        _nomination_facts(browser)
    else:
        prompt = records.get("public-copy.json", {})
        if (
            browser.get("actual_clipboard_sha256") != prompt.get("sha256")
            or browser.get("actual_clipboard_bytes") != prompt.get("bytes")
            or type(prompt.get("bytes")) is not int
            or prompt["bytes"] <= 0
            or "receipt_response" not in browser
        ):
            raise ValueError("Actual native clipboard bytes/receipt outcome required.")


def _nomination_facts(browser: dict[str, Any]) -> None:
    """Require the actual timed fictional nomination and unsent destination.

    :param browser: Actual received native nomination metadata.
    :return: None after complete timing/task/no-send facts agree.
    :raises ValueError: Any required actual nomination evidence is missing.
    """
    required = {
        "nomination_text",
        "elapsed_monotonic_seconds",
        "proposed_target_seconds",
        "automated_path_within_proposed_target",
        "inspected_contact_destination",
    }
    if (
        not required <= browser.keys()
        or browser.get("contact_activated") is not False
        or browser.get("email_sent") is not False
        or browser.get("proposed_target_seconds") != 300
        or browser["automated_path_within_proposed_target"]
        != (browser["elapsed_monotonic_seconds"] <= 300)
    ):
        raise ValueError("Actual unsent timed nomination evidence required.")
