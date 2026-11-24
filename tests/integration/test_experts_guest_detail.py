"""Real anonymous public-detail contract without simulated interaction proof."""

from __future__ import annotations

from typing import Any

import pytest
from django.conf import settings
from django.contrib.auth.models import User
from django.core.mail import EmailMessage
from django.db import connection
from django.test import Client, TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from rest_framework.authtoken.models import Token

from methodology.models import (
    AgentInteraction,
    ExpertProfile,
    KarmaAward,
    Playbook,
    ProcessImprovementProposal,
)
from tests.support.experts_guest_detail import assert_guest_detail_evidence_readable
from tests.support.experts_privacy import assert_private_rows_exist, load_privacy_case

_READ_ONLY_MODELS = (
    User,
    Token,
    Playbook,
    ProcessImprovementProposal,
    KarmaAward,
    ExpertProfile,
    AgentInteraction,
)
_WRITE_PREFIXES = ("INSERT", "UPDATE", "DELETE", "REPLACE", "CREATE", "ALTER", "DROP")


@pytest.mark.django_db
def test_guest_detail_with_anonymous_request_preserves_restricted_contact_and_public_evidence(
    client: Client, mailoutbox: list[EmailMessage]
) -> None:
    """Certify real guest contact privacy and readable evidence without GET writes.

    :param client: Fresh anonymous Django client, e.g. Client().
    :param mailoutbox: Real captured Django mail, e.g. an empty list.
    :return: None after public evidence and read-only assertions pass.
    :raises AssertionError: If contact leaks, evidence disappears or GET mutates state.
    """
    dataset = load_privacy_case()
    assert_private_rows_exist(dataset)
    assert not client.cookies
    before, prior_mail = _state_snapshot(), tuple(mailoutbox)
    with (
        TestCase.captureOnCommitCallbacks() as callbacks,
        CaptureQueriesContext(connection) as queries,
    ):
        response = client.get(
            reverse("expert_detail", args=["mrodriguez"]), follow=False
        )
        assert_guest_detail_evidence_readable(client, response, dataset)
    if _state_snapshot() != before or tuple(mailoutbox) != prior_mail:
        raise AssertionError(
            "Anonymous evidence reads changed persisted state or mail."
        )
    assert not callbacks, "Anonymous GET scheduled a post-commit side effect."
    assert not any(
        row["sql"].lstrip().upper().startswith(_WRITE_PREFIXES) for row in queries
    ), "Anonymous evidence GET executed SQL writes."
    assert not client.cookies
    assert settings.SESSION_COOKIE_NAME not in client.cookies


def _state_snapshot() -> tuple[list[dict[str, Any]], ...]:
    """Capture full ordered rows without disclosing their contents on failure.

    :return: Seven model snapshots, e.g. complete account, ledger and profile rows.
    :raises RuntimeError: If the isolated test database is unavailable.
    """
    return tuple(
        list(model.objects.order_by("pk").values()) for model in _READ_ONLY_MODELS
    )
