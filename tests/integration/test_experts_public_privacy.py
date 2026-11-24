from __future__ import annotations

from http import HTTPStatus

import pytest
from django.core.mail import EmailMessage
from django.http import HttpResponse
from django.test import Client

from methodology.models import AgentInteraction, ExpertProfile, KarmaAward
from tests.support.experts_privacy import (
    EXCLUDED_EVIDENCE_CASES,
    assert_private_rows_exist,
    assert_public_projection,
    assert_public_response,
    load_privacy_case,
)

pytestmark = pytest.mark.django_db

_DETAIL_PATH = "/experts/mrodriguez/"
_READ_ONLY_MODELS = (KarmaAward, ExpertProfile, AgentInteraction)


def test_public_detail_with_anonymous_viewer_excludes_private_data(
    client: Client, mailoutbox: list[EmailMessage]
) -> None:
    """Certify guest HTML against persisted sensitive data.

    :param client: Real Django client, e.g. anonymous session.
    :param mailoutbox: Captured Django email, e.g. an empty outbox.
    :return: None; all guest privacy assertions pass.
    :raises AssertionError: If private data leaks or public evidence disappears.
    """
    dataset = load_privacy_case()
    assert_private_rows_exist(dataset)
    response = _read_public_detail(client, mailoutbox)
    assert_public_response(response, dataset, authenticated=False)


def test_public_detail_with_authenticated_elena_preserves_public_boundary(
    client: Client, mailoutbox: list[EmailMessage]
) -> None:
    """Preserve authorized contact while excluding private contribution data.

    :param client: Real Django client, e.g. force_login(esvensson).
    :param mailoutbox: Captured Django email, e.g. an empty outbox.
    :return: None; public boundary and legitimate mailto both pass.
    :raises AssertionError: If privacy or authenticated contact regresses.
    """
    dataset = load_privacy_case()
    assert_private_rows_exist(dataset)
    client.force_login(dataset.users_by_username["esvensson"])
    response = _read_public_detail(client, mailoutbox)
    assert_public_response(response, dataset, authenticated=True)


@pytest.mark.parametrize(("visibility", "status"), EXCLUDED_EVIDENCE_CASES)
@pytest.mark.parametrize("authenticated", (False, True), ids=("bob", "elena"))
def test_public_detail_with_unpublished_evidence_excludes_each_status(
    client: Client,
    mailoutbox: list[EmailMessage],
    visibility: str,
    status: str,
    authenticated: bool,
) -> None:
    """Certify explicit public-released filtering for both viewer types.

    :param client: Real Django client, e.g. Bob's session.
    :param mailoutbox: Captured Django email, e.g. an empty outbox.
    :param visibility: Persisted variant visibility, e.g. "public".
    :param status: Persisted variant status, e.g. "active".
    :param authenticated: Whether Elena signs in, e.g. True.
    :return: None; variant excluded and public released evidence retained.
    :raises AssertionError: If fixtures are absent or excluded evidence leaks.
    """
    dataset = load_privacy_case()
    assert_private_rows_exist(dataset)
    if authenticated:
        client.force_login(dataset.users_by_username["esvensson"])
    response = _read_public_detail(client, mailoutbox)
    assert_public_response(
        response, dataset, authenticated, excluded_evidence=(visibility, status)
    )


def test_public_detail_with_private_fixture_has_allowlisted_projection(
    client: Client, mailoutbox: list[EmailMessage]
) -> None:
    """Check only S17 DTO schema and real evidence eligibility.

    :param client: Real Django client, e.g. anonymous session.
    :param mailoutbox: Captured Django email, e.g. an empty outbox.
    :return: None; no private fields or ORM objects enter the DTO.
    :raises AssertionError: If schema or public-released eligibility fails.
    """
    dataset = load_privacy_case()
    assert_private_rows_exist(dataset)
    response = _read_public_detail(client, mailoutbox)
    assert response.status_code == HTTPStatus.OK
    assert_public_projection(response.context["person"], dataset)


def _read_public_detail(client: Client, mailoutbox: list[EmailMessage]) -> HttpResponse:
    """Read the profile and verify that the persisted state and mail remain stable.

    :param client: Django client after viewer setup, e.g. an Elena session.
    :param mailoutbox: Captured Django email, e.g. an empty outbox.
    :return: Actual response, e.g. HTTP 200 for Maria.
    :raises AssertionError: If the GET touches a tracked model or sends mail.
    """
    mail_before = tuple(mailoutbox)
    state_before = tuple(
        list(model.objects.order_by("pk").values()) for model in _READ_ONLY_MODELS
    )
    response = client.get(_DETAIL_PATH)
    for model, rows in zip(_READ_ONLY_MODELS, state_before, strict=True):
        if list(model.objects.order_by("pk").values()) != rows:
            raise AssertionError(f"Public detail changed {model.__name__} records.")
    if tuple(mailoutbox) != mail_before:
        raise AssertionError("Public detail changed the email outbox.")
    return response
