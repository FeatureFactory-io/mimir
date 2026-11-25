"""Independent local archive readback before owned private runtime disposal."""

from __future__ import annotations

import json
import re
import tarfile
from pathlib import Path
from typing import Any

from suite_contract import selected_case
from suite_export import allowed_name


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
            _required_records(case, records, manifest)


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
    _lane_records(case, records)


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
            "nonce",
            "web_image",
            "suite_phase",
            "saga_case",
            "control_revision",
        )
    ):
        raise ValueError("Downloaded candidate/control/case identity differs.")


def _lane_records(case: str, records: dict[str, Any]) -> None:
    """Check the actual lane-specific public browser and complete-effects receipts.

    :param case: Closed true lane ID.
    :param records: Actual parsed archive reports.
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
    if (
        case == "summary-acceptance"
        and records.get("saga-summary-mail-preview.json", {}).get("evidence_kind")
        != "actual_file_mail_preview"
    ):
        raise ValueError("Actual verified file-mail preview required.")
