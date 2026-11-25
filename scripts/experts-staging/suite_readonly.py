"""True guest and authenticated-matrix preparation with whole39model oracles."""

from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from django.conf import settings
from django.urls import reverse
from methodology.models import Workflow

from bootstrap import scope, write_private
from saga_contract import (
    assert_login_user,
    assert_new_auth_token,
    assert_session_rows,
    checked_login_interval,
    utc_timestamp,
)
from saga_fixture import (
    assert_pristine,
    domain_rows,
    projections,
    verify_actual_session,
)

logger = logging.getLogger(__name__)
_ROOT = Path("/experts-scope")
_OUTPUT = Path("/output")
_MAIL = Path("/experts-mail")
_FIXTURE = Path("/app/test-data/experts/cedar-rfp-01.json")
CASES = ("guest-public", "authenticated-matrix")
_AUTH = frozenset({"auth.user", "authtoken.token", "sessions.session"})


def now() -> str:
    """Read precise actual UTC.

    :return: Full microsecond aware timestamp.
    """
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def validate_case(case: str) -> str:
    """Require a true readonly case.

    :param case: Explicit guest or authenticated matrix.
    :return: Unchanged case.
    :raises ValueError: An unsupported lane is supplied.
    """
    if type(case) is not str or case not in CASES:
        raise ValueError("True guest-public or authenticated-matrix case required.")
    return case


def prepare_readonly_case(case: str) -> None:
    """Snapshot the fresh baseline without relabeling another case.

    :param case: Closed true case ID.
    :return: None after exclusive private baseline and public oracle.
    :raises AssertionError: The positive owned baseline differs.
    """
    validate_case(case)
    assert_pristine()
    rows = domain_rows()
    assert len(rows) == 39 and not rows["sessions.session"]
    baseline = {
        "case": case,
        "rows": rows,
        "projections": projections(),
        "prepared_at": now(),
    }
    write_private(_ROOT / "suite-readonly-baseline.json", baseline)
    document = json.loads(_FIXTURE.read_text())
    maria = next(p for p in document["people"] if p["username"] == "mrodriguez")
    workflow = Workflow.objects.get(
        playbook_id=6101, name="Lead an Accessibility Review"
    )
    oracle = {
        "case": case,
        "source_revision": os.environ["MIMIR_GIT_REVISION"],
        "fixture_sha256": hashlib.sha256(_FIXTURE.read_bytes()).hexdigest(),
        "summary": maria["summary"],
        "workflow_path": reverse("workflow_detail", args=(6101, workflow.pk)),
    }
    write_private(_OUTPUT / "suite-readonly-oracle.json", oracle)
    logger.info("Readonly case prepared | case=%s | models=39", case)


def assert_readonly_rows(
    case: str,
    baseline: dict[str, Any],
    after: dict[str, Any],
    observed: dict[str, Any],
    verified: str,
) -> Any:
    """Prove all39models and only exact source-supported native login effects.

    :param case: Closed true case.
    :param baseline: Complete private pre-browser state.
    :param after: Complete current state.
    :param observed: Actual precise native login envelope, or None.
    :param verified: Actual verification instant.
    :return: Exact Elena interval, or None for the guest.
    :raises AssertionError: Any row or time bound differs.
    """
    validate_case(case)
    before = baseline["rows"]
    assert len(before) == len(after) == 39 and before.keys() == after.keys()
    window = (utc_timestamp(baseline["prepared_at"]), utc_timestamp(verified))
    assert 0 <= (window[1] - window[0]).total_seconds() <= 720
    if case == "guest-public":
        assert observed is None and before == after
        return None
    login = checked_login_interval(
        "esvensson", observed, window, settings.SESSION_COOKIE_AGE
    )
    assert settings.SESSION_COOKIE_AGE == 1209600
    for label in before.keys() - _AUTH:
        assert before[label] == after[label], "Readonly domain rows changed."
    _verify_auth(before, after, login)
    return login


def _verify_auth(before: dict[str, Any], after: dict[str, Any], login: Any) -> None:
    """Reconcile exact actor/token/cookie effects without unrelated allowances.

    :param before: All original model rows.
    :param after: All current model rows.
    :param login: Exact source-supported native interval.
    :return: None after complete auth comparison.
    :raises AssertionError: Any account effect differs.
    """
    assert before["auth.user"].keys() == after["auth.user"].keys()
    user_id = None
    for pk, row in before["auth.user"].items():
        if row["fields"]["username"] == "esvensson":
            assert_login_user(row, after["auth.user"][pk], login)
            user_id = int(pk)
        else:
            assert row == after["auth.user"][pk]
    assert user_id is not None
    old, new = before["authtoken.token"], after["authtoken.token"]
    assert all(new.get(pk) == row for pk, row in old.items())
    added = new.keys() - old.keys()
    assert len(added) == int(
        not any(row["fields"]["user"] == user_id for row in old.values())
    )
    for pk in added:
        assert_new_auth_token(pk, new[pk], user_id, login)
    assert_session_rows(before["sessions.session"], after["sessions.session"], login)


def verify_readonly_case(case: str) -> None:
    """Recheck actual owned39model state after seven real viewport acquisitions.

    :param case: Same true case prepared before Gunicorn.
    :return: None after a precise public verification receipt.
    :raises AssertionError: Browser, account, model, totals or mail differs.
    """
    validate_case(case)
    scope()
    baseline = json.loads((_ROOT / "suite-readonly-baseline.json").read_text())
    observed = json.loads((_OUTPUT / "suite-readonly-browser.json").read_text())
    login = _readonly_observation(case, baseline, observed)
    verify_actual_session(login)
    assert projections() == baseline["projections"] and not list(_MAIL.iterdir())
    write_private(
        _OUTPUT / "suite-readonly-effects.json",
        {
            "case": case,
            "status": "CASE_VERIFIED",
            "model_count": 39,
            "scope_rechecked": True,
            "new_awards": 0,
            "decision_mail_files": 0,
            "full_saga_accepted": False,
        },
    )
    logger.info("Readonly case verified | case=%s | models=39", case)


def _readonly_observation(
    case: str, baseline: dict[str, Any], observed: dict[str, Any]
) -> Any:
    """Bind actual source-sized browser completion to complete private model state.

    :param case: Closed true readonly case.
    :param baseline: Complete private independently prepared baseline.
    :param observed: Actual seven-size native browser metadata.
    :return: Exact observed login interval or None for the guest.
    :raises AssertionError: Case, measured sizes or any39model effect differs.
    """
    assert baseline["case"] == observed["case"] == case
    assert observed["status"] == "BROWSER_OBSERVED" and observed["viewport_count"] == 7
    sizes = (
        (1280, 800),
        (1920, 1080),
        (1512, 982),
        (768, 1024),
        (1024, 768),
        (390, 844),
        (360, 800),
    )
    assert observed["viewports"] == [{"width": w, "height": h} for w, h in sizes]
    return assert_readonly_rows(
        case, baseline, domain_rows(), observed["login_observation"], now()
    )
