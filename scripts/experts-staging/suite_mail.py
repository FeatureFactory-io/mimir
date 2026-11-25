"""Verified derivative of the actual accepted file-mail companion artifact."""

from __future__ import annotations

import hashlib
import json
from email import policy
from email.parser import BytesParser
from pathlib import Path
from typing import Any

from bootstrap import write_private
from saga_summary_fixture import prepared_change, read_baseline, validate_mail


def preview_record(raw: bytes, recipient: str, name: str) -> dict[str, Any]:
    """Extract only the exact accepted fixture mail facts.

    :param raw: Actual file-mail bytes, never invented mail UI.
    :param recipient: Verified actual fixture recipient.
    :param name: Verified actual ADD Activity name.
    :return: Typed canonical derivative with original message hash.
    :raises AssertionError: Recipient, subject, operation or version differs.
    """
    message = BytesParser(policy=policy.default).parsebytes(raw)
    subject, body = str(message["Subject"]), message.get_content()
    assert (
        message.get_all("To") == [recipient]
        and recipient == "maria.rodriguez@example.com"
    )
    assert "Accepted" in subject and name == "Screen Reader Error Recovery"
    assert (
        f'ADD Activity "{name}"' in body
        and "Decision: ACCEPT" in body
        and "is now v3.0" in body
    )
    return {
        "derivative": True,
        "evidence_kind": "actual_file_mail_preview",
        "original_sha256": hashlib.sha256(raw).hexdigest(),
        "recipient": recipient,
        "subject": "Accepted",
        "operation": "ADD Activity",
        "activity": name,
        "version": "3.0",
        "body_excerpt": f'ADD Activity "{name}"\nDecision: ACCEPT\nis now v3.0',
        "raw_headers_exported": False,
    }


def mail_preview() -> None:
    """Read the genuine mail file only after the complete effects receipt passes.

    :return: None after the exact verified derivative is retained.
    :raises AssertionError: Effects or actual file-mail identity differs.
    """
    effects = json.loads(Path("/output/saga-summary-effects.json").read_text())
    assert effects["status"] == "CASE_VERIFIED" and effects["decision_mail_files"] == 1
    baseline = read_baseline()
    validate_mail(baseline)
    change = prepared_change(baseline)
    files = list(Path("/experts-mail").iterdir())
    assert len(files) == 1 and not files[0].is_symlink()
    record = preview_record(
        files[0].read_bytes(), change.pip.created_by.email, change.name
    )
    write_private(Path("/output/saga-summary-mail-preview.json"), record)
