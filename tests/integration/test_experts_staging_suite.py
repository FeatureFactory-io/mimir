"""Real39model account effects for true guest/matrix suite identities."""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path
from typing import Any

import pytest
from django.contrib.auth.models import User
from django.test import Client, override_settings
from rest_framework.authtoken.models import Token

from methodology.models import ExpertProfile
from tests.support.experts_data import CEDAR_PASSWORD, CedarDataset

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "scripts/experts-staging"))
import suite_readonly as fixture


def _login(client: Client) -> dict[str, Any]:
    """Perform genuine native Elena login and record the precise response envelope.

    :param client: Actual Django client.
    :return: Exact safe native-login metadata.
    """
    client.get("/auth/user/login/")
    started = fixture.now()
    response = client.post(
        "/auth/user/login/", {"username": "esvensson", "password": CEDAR_PASSWORD}
    )
    completed = fixture.now()
    assert response.status_code == 302
    return {
        "actor": "esvensson",
        "method": "POST",
        "path": "/auth/user/login/",
        "status": 302,
        "started_at": started,
        "completed_at": completed,
        "session_key_sha256": hashlib.sha256(
            client.cookies["sessionid"].value.encode()
        ).hexdigest(),
    }


@pytest.mark.django_db(transaction=True)
def test_assert_readonly_rows_with_true_guest_preserves_all39models(
    cedar_baseline: CedarDataset,
) -> None:
    before = {"rows": fixture.domain_rows(), "prepared_at": fixture.now()}
    client = Client()
    for path in (
        "/experts/?category=design",
        "/experts/mrodriguez/",
        "/experts/?category=other",
    ):
        assert client.get(path).status_code == 200
    assert (
        fixture.assert_readonly_rows(
            "guest-public", before, fixture.domain_rows(), None, fixture.now()
        )
        is None
    )
    assert len(before["rows"]) == 39


@pytest.mark.django_db(transaction=True)
@override_settings(SESSION_SAVE_EVERY_REQUEST=True)
def test_assert_readonly_rows_with_native_matrix_login_allows_only_precise_actor_effects(
    cedar_baseline: CedarDataset,
) -> None:
    before = {"rows": fixture.domain_rows(), "prepared_at": fixture.now()}
    client = Client()
    observed = _login(client)
    assert client.get("/experts/?category=design").status_code == 200
    assert client.get("/experts/mrodriguez/").status_code == 200
    login = fixture.assert_readonly_rows(
        "authenticated-matrix", before, fixture.domain_rows(), observed, fixture.now()
    )
    assert login.actor == "esvensson" and Token.objects.get(user__username="esvensson")


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize(
    "tamper",
    [
        "unrelated_user",
        "prose",
        "unrelated_token",
        "session_digest",
        "native_start",
        "guest_login",
    ],
)
def test_assert_readonly_rows_with_unrelated_delta_or_unbound_login_rejects(
    cedar_baseline: CedarDataset, tamper: str
) -> None:
    before = {"rows": fixture.domain_rows(), "prepared_at": fixture.now()}
    client = Client()
    observed = _login(client)
    if tamper == "unrelated_user":
        User.objects.filter(username="mchen").update(first_name="UNRELATED")
    elif tamper == "prose":
        ExpertProfile.objects.filter(user__username="mrodriguez").update(
            contribution_summary="UNRELATED"
        )
    elif tamper == "unrelated_token":
        Token.objects.get_or_create(user=User.objects.get(username="mchen"))
    elif tamper == "session_digest":
        observed["session_key_sha256"] = "0" * 64
    elif tamper == "native_start":
        observed["started_at"] = "2020-01-01T00:00:00.000000+00:00"
    case = "guest-public" if tamper == "guest_login" else "authenticated-matrix"
    with pytest.raises(AssertionError):
        fixture.assert_readonly_rows(
            case, before, fixture.domain_rows(), observed, fixture.now()
        )
