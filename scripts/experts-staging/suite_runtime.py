"""Initialized-Django dispatch, never a normal deployment entrypoint."""

from __future__ import annotations

import json
import os
from pathlib import Path

from bootstrap import verify_after
from saga_fixture import prepare_case, verify_case
from saga_summary_fixture import prepare_summary_case, verify_summary_case
from saga_visual_fixture import prepare_visual_case, verify_visual_case
from suite_contract import selected_case
from suite_mail import mail_preview
from suite_readonly import prepare_readonly_case, verify_readonly_case

_RUNTIME = Path("/runtime")


def case_name() -> str:
    """Validate the actual mounted declaration and explicit app environment.

    :return: Closed true case ID.
    :raises AssertionError: Declaration and process environment differ.
    """
    manifest = json.loads((_RUNTIME / "run.json").read_text())
    case = selected_case(manifest).case
    assert os.environ.get("EXPERTS_SAGA_CASE", "core") == case
    return case


def prepare() -> None:
    """Prepare exactly one fresh case after bootstrap before Gunicorn serves.

    :return: None after the case-specific preparation.
    :raises ValueError: Case identity or owning fixture guard fails.
    """
    case = case_name()
    if case in {"nomination", "copy-maria", "copy-guest", "copy-self"}:
        prepare_case(case)
    elif case in {"guest-public", "authenticated-matrix"}:
        prepare_readonly_case(case)
    elif case in {"long_identity_and_prose", "missing_summary"}:
        prepare_visual_case(case)
    elif case == "summary-acceptance":
        prepare_summary_case()


def verify() -> None:
    """Run only the precise lane oracle; awarded lanes never use core's oracle.

    :return: None after actual database effects and companion mail verify.
    :raises AssertionError: Any actual effect differs.
    """
    case = case_name()
    if case == "core":
        verify_after()
    elif case in {"nomination", "copy-maria", "copy-guest", "copy-self"}:
        verify_case(case)
    elif case in {"guest-public", "authenticated-matrix"}:
        verify_readonly_case(case)
    elif case in {"long_identity_and_prose", "missing_summary"}:
        verify_visual_case(case)
    elif case == "summary-acceptance":
        verify_summary_case()
        mail_preview()
