"""Real ORM/native login tests for the two independent staged visual variants."""

from __future__ import annotations

import copy
import hashlib
import sys
from pathlib import Path
from typing import Any

import pytest
from django.contrib.auth.models import User
from django.test import Client, override_settings
from rest_framework.authtoken.models import Token

from tests.support.experts_data import CEDAR_PASSWORD, CedarDataset

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "scripts/experts-staging"))
import saga_visual_fixture as fixture
from saga_visual_contract import (
    assert_preparation_rows,
    assert_visual_effects,
    source_constants,
)


def _constants() -> dict[str, Any]:
    """Read exact candidate source as data.

    :return: Checked pure literals.
    """
    return source_constants(_ROOT / "tests/e2e/test_expert_cards.py")


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("case", ["long_identity_and_prose", "missing_summary"])
def test_prepare_rows_with_actual_baseline_changes_only_declared_fields(
    cedar_baseline: CedarDataset, case: str
) -> None:
    """Real39model precision snapshots protect the exact three-field preparation.

    :param cedar_baseline: Real separately owned pytest lifecycle.
    :param case: Explicit long or missing lane.
    :return: None after exact whole-state and independent field checks.
    """
    before = fixture.domain_rows()
    after = fixture._prepare_rows(case, _constants())
    assert len(before) == len(after) == 39
    assert_preparation_rows(before, after, case, _constants())
    maria = User.objects.get(username="mrodriguez")
    assert maria.first_name == (
        _constants()["_LONG_FIRST"] if case == "long_identity_and_prose" else "Maria"
    )
    if case == "missing_summary":
        assert before == after


@pytest.mark.django_db(transaction=True)
def test_prepare_rows_with_unrelated_user_delta_is_rejected(
    cedar_baseline: CedarDataset,
) -> None:
    """Another account's otherwise legitimate field change cannot be absorbed.

    :param cedar_baseline: Real Cedar database.
    :return: None after the complete-state oracle rejects the delta.
    """
    before = fixture.domain_rows()
    after = fixture._prepare_rows("long_identity_and_prose", _constants())
    row = next(
        row
        for row in after["auth.user"].values()
        if row["fields"]["username"] == "esvensson"
    )
    row["fields"]["email"] = "changed@example.com"
    with pytest.raises(AssertionError):
        assert_preparation_rows(before, after, "long_identity_and_prose", _constants())


def _native_login(client: Client) -> dict[str, Any]:
    """Record the actual normal Elena POST response envelope and cookie identity.

    :param client: Real Django client with native session middleware.
    :return: Safe complete precise native login metadata.
    """
    client.get("/auth/user/login/")
    start = fixture.now()
    response = client.post(
        "/auth/user/login/", {"username": "esvensson", "password": CEDAR_PASSWORD}
    )
    end = fixture.now()
    assert response.status_code == 302
    return {
        "actor": "esvensson",
        "method": "POST",
        "path": "/auth/user/login/",
        "status": 302,
        "started_at": start,
        "completed_at": end,
        "session_key_sha256": hashlib.sha256(
            client.cookies["sessionid"].value.encode()
        ).hexdigest(),
    }


@pytest.mark.django_db(transaction=True)
@override_settings(SESSION_SAVE_EVERY_REQUEST=True)
@pytest.mark.parametrize("case", ["long_identity_and_prose", "missing_summary"])
def test_assert_visual_effects_with_native_elena_login_preserves_all_other_rows(
    cedar_baseline: CedarDataset, case: str
) -> None:
    """Actual native login and later session refresh fit the reviewed exact oracle.

    :param cedar_baseline: Real separate fixture baseline.
    :param case: Independent prepared variant.
    :return: None after39models and original native token/session effects agree.
    """
    rows = fixture._prepare_rows(case, _constants())
    baseline = {"rows": rows, "prepared_at": fixture.now()}
    client = Client()
    observed = _native_login(client)
    assert client.get("/experts/?category=development").status_code == 200
    assert_visual_effects(
        baseline, fixture.domain_rows(), observed, fixture.now(), 1209600
    )
    assert Token.objects.get(user__username="esvensson")


@pytest.mark.django_db(transaction=True)
@override_settings(SESSION_SAVE_EVERY_REQUEST=True)
@pytest.mark.parametrize(
    "tamper",
    [
        "unrelated_password",
        "unrelated_token",
        "profile_prose",
        "session_digest",
        "native_start",
    ],
)
def test_assert_visual_effects_with_unrelated_change_or_invalid_login_rejects(
    cedar_baseline: CedarDataset, tamper: str
) -> None:
    """Whole-state comparison rejects unrelated writes and widened login bounds.

    :param cedar_baseline: Fresh real Cedar test lifecycle.
    :param tamper: One independent actual ORM or native metadata counterexample.
    :return: None after the precise fail-closed rejection.
    """
    rows = fixture._prepare_rows("missing_summary", _constants())
    baseline = {"rows": copy.deepcopy(rows), "prepared_at": fixture.now()}
    observed = _native_login(Client())
    if tamper == "unrelated_password":
        User.objects.filter(username="mchen").update(password="changed")
    elif tamper == "unrelated_token":
        Token.objects.create(user=User.objects.get(username="mchen"))
    elif tamper == "profile_prose":
        fixture.ExpertProfile.objects.filter(user__username="mrodriguez").update(
            contribution_summary="changed"
        )
    elif tamper == "session_digest":
        observed["session_key_sha256"] = "0" * 64
    else:
        observed["started_at"] = baseline["prepared_at"].replace("2026", "2025")
    with pytest.raises(AssertionError):
        assert_visual_effects(
            baseline, fixture.domain_rows(), observed, fixture.now(), 1209600
        )
