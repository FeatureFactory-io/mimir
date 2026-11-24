"""S15 initial guest contact and request isolation through the real Django client."""

from __future__ import annotations

from collections.abc import Iterator
from html import unescape
from http import HTTPStatus
from urllib.parse import unquote

import pytest
from django.core.mail import EmailMessage
from django.http import HttpResponse
from django.test import Client, TestCase
from django.urls import reverse
from rest_framework.authtoken.models import Token

from methodology.models import AgentInteraction, ExpertProfile, KarmaAward
from methodology.services.expert_contact_context import ExpertContactContext
from methodology.services.experts_service import ExpertsService
from tests.support.experts_data import CEDAR_PASSWORD, CedarDataset, load_cedar_baseline
from tests.support.experts_guest_assertions import (
    assert_guest_auth_banner,
    assert_no_private_account_controls,
    assert_public_design_ranking,
)
from tests.support.experts_guest_contact import (
    GUEST_CONTACT_EXPLANATION,
    assert_guest_contact_markup,
    assert_guest_profile_link,
)
from tests.support.experts_html import element_text, find_by_test_id

_DESIGN_PATH = "/experts/?category=design"
_DESIGN_CARD_COUNT = 5
_MARIA = "mrodriguez"
_ELENA = "esvensson"
_PUBLIC_CARD_FIELDS = (
    "username",
    "name",
    "initials",
    "total_points",
    "category_subtotal",
    "formatted_karma",
    "primary_category",
    "hint",
)
_PublicCards = tuple[tuple[str | int, ...], ...]


@pytest.fixture
def cedar_guest_contact_dataset(db: None) -> CedarDataset:
    """Load the independently specified Cedar baseline for one server test.

    :param db: Runner-owned database access. Example: None.
    :return: Imported dataset. Example: CedarDataset with Maria and Elena.
    :raises ValueError: If the database scope or fixture data is invalid.
    """
    return load_cedar_baseline()


@pytest.fixture
def read_only_expert_state(
    cedar_guest_contact_dataset: CedarDataset, mailoutbox: list[EmailMessage]
) -> Iterator[None]:
    """Bracket requests with real storage, pending-callback and mail checks.

    :param cedar_guest_contact_dataset: Imported baseline. Example: Cedar Design rankings.
    :param mailoutbox: Real test mail capture. Example: [].
    :return: An iterator spanning the request sequence. Example: one None.
    :raises AssertionError: If requests change records or schedule work or mail.
    """
    before = _expert_state()
    assert not mailoutbox
    with TestCase.captureOnCommitCallbacks() as callbacks:
        yield
    assert not callbacks, "A list request scheduled a commit callback"
    assert not mailoutbox, "A list request sent mail"
    if _expert_state() != before:
        pytest.fail("The request chain changed ledger, profile or model state")


def test_guest_list_contact_with_anonymous_request_restricts_contact(
    client: Client,
    cedar_guest_contact_dataset: CedarDataset,
    read_only_expert_state: None,
) -> None:
    """Prove initial guest HTML and an enabled profile link on all five cards.

    :param client: Anonymous real Django client. Example: no authenticated session.
    :param cedar_guest_contact_dataset: Real baseline. Example: Maria has 8200 Karma.
    :param read_only_expert_state: Ledger, profile, model and mail guard. Example: None.
    :return: None after all five ordered cards pass the server contract.
    :raises AssertionError: If guest contact, privacy or profile navigation differs.
    """
    response = client.get(_DESIGN_PATH)

    _assert_guest_design(response, cedar_guest_contact_dataset)


def test_guest_list_contact_with_authenticated_then_guest_requests_does_not_leak_email(
    client: Client,
    cedar_guest_contact_dataset: CedarDataset,
    read_only_expert_state: None,
) -> None:
    """Compare retained and new public data across real authentication changes.

    :param client: Client reused across login and logout. Example: Elena then guest.
    :param cedar_guest_contact_dataset: Real baseline. Example: has Elena's account.
    :param read_only_expert_state: Ledger, profile, model and mail guard. Example: None.
    :return: None after authenticated mailto and independent guest checks pass.
    :raises AssertionError: If contact leaks or public projections change.
    """
    dataset = cedar_guest_contact_dataset
    initial_guest = client.get(_DESIGN_PATH)
    expected_public_cards = _assert_guest_design(initial_guest, dataset)
    leaders = ExpertsService().list_leaders("design", correlation_id="cedar-s15-before")
    assert client.login(username=_ELENA, password=CEDAR_PASSWORD)
    signed_in = client.get(_DESIGN_PATH)
    _assert_elena_contact(signed_in, dataset)
    logout = client.get(reverse("logout"))
    assert logout.status_code == HTTPStatus.FOUND and logout.url == reverse("login")

    after_logout = client.get(_DESIGN_PATH)
    fresh_guest = Client().get(_DESIGN_PATH)
    for response in (initial_guest, after_logout, fresh_guest):
        assert _assert_guest_design(response, dataset) == expected_public_cards
    _assert_elena_contact(signed_in, dataset)
    assert _public_card_fields(signed_in) == expected_public_cards
    assert (
        ExpertsService().list_leaders("design", correlation_id="cedar-s15-after")
        == leaders
    )


def _expert_state() -> tuple[tuple[dict[str, object], ...], ...]:
    """Read complete persisted Experts records in stable order.

    :return: Ledger, profiles and model interactions. Example: nonempty ledger rows.
    :raises DatabaseError: If the runner cannot read the isolated database.
    """
    return tuple(
        tuple(model.objects.order_by("pk").values())
        for model in (KarmaAward, ExpertProfile, AgentInteraction)
    )


def _assert_guest_design(response: HttpResponse, dataset: CedarDataset) -> _PublicCards:
    """Check all guest card actions and keep a contact-free public snapshot.

    :param response: Real GET. Example: anonymous Design list HTTP 200.
    :param dataset: Independent fixture with public ranks and private records.
    :return: Public card values in order. Example: Sofia before Maria.
    :raises AssertionError: If the route, privacy, ranking or contact differs.
    """
    assert response.status_code == HTTPStatus.OK
    assert response.wsgi_request.get_full_path() == _DESIGN_PATH
    assert response.wsgi_request.user.is_anonymous
    html = response.content.decode()
    emails = tuple(
        user.email for user in dataset.users_by_username.values() if user.email
    )
    _assert_guest_privacy(response, emails)
    assert_guest_auth_banner(html)
    assert_no_private_account_controls(html)
    assert_public_design_ranking(html)
    assert ("aria-current", "page") in find_by_test_id(
        html, "experts-category-design"
    ).attributes
    usernames = tuple(dataset.oracle["expected_design_order"])
    assert len(usernames) == _DESIGN_CARD_COUNT
    assert response.context["count"] == _DESIGN_CARD_COUNT
    assert response.context["selected_category"] == "design"
    public_cards = _public_card_fields(response)
    assert tuple(card[0] for card in public_cards) == usernames
    for row, username in zip(response.context["people"], usernames, strict=True):
        expected = ExpertContactContext(
            username, "authentication_required", None, GUEST_CONTACT_EXPLANATION
        )
        if row["contact"] != expected:
            pytest.fail("A guest card received an unexpected contact context")
        assert_guest_contact_markup(response, f"experts-card-{username}", emails)
        assert_guest_profile_link(response, username)
    return public_cards


def _assert_guest_privacy(response: HttpResponse, emails: tuple[str, ...]) -> None:
    """Check both public output and Django context without echoing private values.

    :param response: Real anonymous response. Example: initial Design listing.
    :param emails: Nonempty fixture addresses. Example: all Cedar account emails.
    :return: None when no mail destinations or account secrets are present.
    :raises AssertionError: If the privacy check lacks sentinels or detects a leak.
    """
    tokens = tuple(Token.objects.values_list("key", flat=True))
    assert emails and tokens, "Expected real Cedar email and token sentinels"
    for content in (response.content.decode(), repr(response.context)):
        surface = unquote(unescape(content)).casefold()
        if "mailto:" in surface or any(
            value.casefold() in surface for value in (*emails, *tokens)
        ):
            pytest.fail("Guest listing exposed a private address or credential")


def _public_card_fields(response: HttpResponse) -> _PublicCards:
    """Take an immutable snapshot of the allowlisted card fields in display order.

    :param response: Real list response. Example: signed-in Design listing.
    :return: Contact-free snapshots. Example: one tuple of values per card.
    :raises AssertionError: If an unapproved field or non-scalar enters public data.
    """
    rows = response.context["people"]
    if any(row.keys() != {*_PUBLIC_CARD_FIELDS, "contact"} for row in rows):
        pytest.fail("The card context breached the public field allowlist")
    values = tuple(tuple(row[key] for key in _PUBLIC_CARD_FIELDS) for row in rows)
    if any(type(value) not in (str, int) for row in values for value in row):
        pytest.fail("The public card fields include a non-scalar value")
    return values


def _assert_elena_contact(response: HttpResponse, dataset: CedarDataset) -> None:
    """Prove actual authenticated contact context plus the matching rendered link.

    :param response: Real Elena list response. Example: authenticated Design GET.
    :param dataset: Real Cedar accounts. Example: fixture Maria and Elena.
    :return: None when Maria's exact email handoff appears on the signed-in card.
    :raises AssertionError: If session, public ranking or handoff is incorrect.
    """
    assert response.status_code == HTTPStatus.OK
    assert response.wsgi_request.get_full_path() == _DESIGN_PATH
    actor = response.wsgi_request.user
    assert actor.is_authenticated and actor.pk == dataset.user_ids[_ELENA]
    assert_public_design_ranking(response.content.decode())
    card = find_by_test_id(response.content, f"experts-card-{_MARIA}")
    link = find_by_test_id(str(card), f"experts-reach-out-{_MARIA}")
    assert link.name == "a" and element_text(link) == "Reach out"
    [maria] = [row for row in response.context["people"] if row["username"] == _MARIA]
    expected = f"mailto:{dataset.users_by_username[_MARIA].email}"
    contact = maria["contact"]
    if (
        contact.state != "available"
        or contact.href != expected
        or dict(link.attributes).get("href") != expected
    ):
        pytest.fail("Elena did not receive the expected authenticated handoff")
