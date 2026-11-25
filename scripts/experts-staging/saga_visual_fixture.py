"""Guarded preparation and complete row proof for S04 long/missing cases."""

from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from django.conf import settings
from django.contrib.auth.models import User
from django.db import transaction
from methodology.models import ExpertProfile

from bootstrap import scope, write_private
from saga_contract import checked_login_interval, utc_timestamp
from saga_fixture import (
    assert_pristine,
    domain_rows,
    projections,
    verify_actual_session,
)
from saga_visual_contract import (
    FIXTURE_SHA256,
    assert_preparation_rows,
    assert_visual_effects,
    expected_contributors,
    source_constants,
    validate_case,
)

logger = logging.getLogger(__name__)
_ROOT = Path("/experts-scope")
_OUTPUT = Path("/output")
_MAIL = Path("/experts-mail")
_FIXTURE = Path("/app/test-data/experts/cedar-rfp-01.json")
_SOURCE = Path("/app/tests/e2e/test_expert_cards.py")


def now() -> str:
    """Read actual UTC with complete precision.

    :return: Aware microsecond ISO timestamp.
    """
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def checked_fixture() -> dict[str, Any]:
    """Check exact source fixture and original accounts before preparation.

    :return: Actual independent checked Cedar document.
    :raises AssertionError: The fixture identity or original account differs.
    """
    assert hashlib.sha256(_FIXTURE.read_bytes()).hexdigest() == FIXTURE_SHA256
    document = json.loads(_FIXTURE.read_text())
    for person in document["people"]:
        user = User.objects.get(username=person["username"])
        assert user.get_full_name() == person["name"] and user.email == person["email"]
        assert user.is_staff == (user.username == "mchen")
        assert ExpertProfile.objects.get(user=user).contribution_summary == (
            person["summary"] or ""
        )
    elena = User.objects.get(username="esvensson")
    assert elena.get_full_name() == "Elena Svensson" and not elena.is_staff
    return document


def _prepare_rows(case: str, constants: dict[str, Any]) -> dict[str, Any]:
    """Apply exact fields after the caller has checked positive scope ownership.

    :param case: Explicit validated variant.
    :param constants: Checked source literals.
    :return: Complete prepared rows; all other rows and projections stay exact.
    :raises AssertionError: Initial accounts or a preparation effect differs.
    """
    validate_case(case)
    with transaction.atomic():
        before, totals = domain_rows(), projections()
        assert len(before) == 39
        assert not before["sessions.session"]
        if case == "long_identity_and_prose":
            user_id = _apply_long_identity(constants)
            totals[str(user_id)]["display_name"] = (
                constants["_LONG_FIRST"] + " " + constants["_LONG_LAST"]
            )
        after = domain_rows()
        assert_preparation_rows(before, after, case, constants)
        assert projections() == totals
    return after


def _apply_long_identity(constants: dict[str, Any]) -> int:
    """Update only Maria's source-declared first/last names and stored prose.

    :param constants: Exact checked S04 literals.
    :return: Maria's real unchanged primary key.
    :raises AssertionError: Either exact update fails to affect one row.
    """
    user = User.objects.get(username="mrodriguez")
    changed = User.objects.filter(pk=user.pk).update(
        first_name=constants["_LONG_FIRST"], last_name=constants["_LONG_LAST"]
    )
    assert changed == 1
    changed = ExpertProfile.objects.filter(user=user).update(
        contribution_summary=constants["_LONG_SUMMARY"]
    )
    assert changed == 1
    return user.pk


def prepare_visual_case(case: str) -> None:
    """Prepare one freshly owned variant, preserving original bootstrap evidence.

    :param case: Explicit long or missing variant.
    :return: None after exclusive original/prepared snapshots and safe oracle.
    :raises AssertionError: Ownership, original fixture or exact field delta differs.
    :raises FileExistsError: Preparation has already occurred.
    """
    validate_case(case)
    scope()
    if (_ROOT / "saga-visual-baseline.json").exists():
        raise FileExistsError("Visual preparation cannot be repeated.")
    assert_pristine()
    original = (_ROOT / "domain-state.json").read_bytes()
    constants, document = source_constants(_SOURCE), checked_fixture()
    category, contributors = expected_contributors(document, case, constants)
    write_private(
        _ROOT / "saga-visual-original.json",
        {"case": case, "rows": domain_rows(), "projections": projections()},
    )
    rows = _prepare_rows(case, constants)
    baseline = {
        "case": case,
        "rows": rows,
        "projections": projections(),
        "prepared_at": now(),
        "original_bootstrap_sha256": hashlib.sha256(original).hexdigest(),
    }
    assert (_ROOT / "domain-state.json").read_bytes() == original
    write_private(_ROOT / "saga-visual-baseline.json", baseline)
    _write_oracle(case, category, contributors, constants)
    logger.info(
        "Visual companion prepared | case=%s | exact_field_changes=%s",
        case,
        3 if case == "long_identity_and_prose" else 0,
    )


def _write_oracle(
    case: str,
    category: str,
    contributors: list[dict[str, str]],
    constants: dict[str, Any],
) -> None:
    """Publish only exact public/source facts, never private model snapshots.

    :param case: Validated variant.
    :param category: Independent expected category.
    :param contributors: Independent public ranked display facts.
    :param constants: Checked S04 literal/source identities.
    :return: None after exclusive safe oracle creation.
    """
    oracle = {
        "case": case,
        "category": category,
        "contributors": contributors,
        "constants": constants,
        "fixture_sha256": FIXTURE_SHA256,
        "application_source_revision": os.environ["MIMIR_GIT_REVISION"],
        "s04_candidate_revision": "04c9432",
        "fixture_control_sha256": hashlib.sha256(
            Path(__file__).read_bytes()
        ).hexdigest(),
    }
    write_private(_OUTPUT / "saga-visual-oracle.json", oracle)


def verify_visual_case(case: str) -> None:
    """Recheck all actual effects against the private prepared variant baseline.

    :param case: Same exact freshly prepared variant.
    :return: None after all39models, precise login effects and mail agree.
    :raises AssertionError: Any unrelated row or browser observation differs.
    """
    validate_case(case)
    scope()
    baseline = json.loads((_ROOT / "saga-visual-baseline.json").read_text())
    observed = json.loads((_OUTPUT / "saga-visual-browser.json").read_text())
    assert baseline["case"] == observed["case"] == case
    _verify_observation(baseline, observed)
    assert projections() == baseline["projections"] and not list(_MAIL.iterdir())
    assert (
        hashlib.sha256((_ROOT / "domain-state.json").read_bytes()).hexdigest()
        == baseline["original_bootstrap_sha256"]
    )
    result = {
        "case": case,
        "status": "CASE_VERIFIED",
        "model_count": len(baseline["rows"]),
        "scope_rechecked": True,
        "new_awards": 0,
        "decision_mail_files": 0,
        "full_saga_accepted": False,
    }
    write_private(_OUTPUT / "saga-visual-effects.json", result)
    logger.info(
        "Visual companion verified | case=%s | model_count=%s",
        case,
        len(baseline["rows"]),
    )


def _verify_observation(baseline: dict[str, Any], observed: dict[str, Any]) -> None:
    """Bind seven actual screens and the exact native session to the baseline.

    :param baseline: Complete private prepared snapshot.
    :param observed: Actual safe browser metadata.
    :return: None after native actor/token/cookie/time and complete rows agree.
    :raises AssertionError: Exact seven-size proof or any side effect differs.
    """
    constants = source_constants(_SOURCE)
    assert observed["status"] == "BROWSER_OBSERVED"
    assert [
        (row["viewport"]["width"], row["viewport"]["height"])
        for row in observed["screens"]
    ] == list(constants["VIEWPORTS"])
    verified_at = now()
    assert_visual_effects(
        baseline,
        domain_rows(),
        observed["login_observation"],
        verified_at,
        settings.SESSION_COOKIE_AGE,
    )
    login = checked_login_interval(
        "esvensson",
        observed["login_observation"],
        (utc_timestamp(baseline["prepared_at"]), utc_timestamp(verified_at)),
        settings.SESSION_COOKIE_AGE,
    )
    verify_actual_session(login)
