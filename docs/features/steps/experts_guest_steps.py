"""S07 acceptance bindings for public Experts rankings and account privacy."""

from __future__ import annotations

from html import unescape
from http import HTTPStatus

from behave import given, then
from behave.runner import Context
from django.test import Client
from django.urls import reverse
from rest_framework.authtoken.models import Token

from tests.support.experts_guest_assertions import (
    assert_guest_auth_banner,
    assert_no_private_account_controls,
    assert_public_design_ranking,
)
from tests.support.experts_guest_contact import GUEST_CONTACT_EXPLANATION
from tests.support.experts_html import _walk_elements, element_text, find_by_test_id

_DEVELOPMENT_RANKING = (("mchen", 12450), ("jlee", 6100))


@given("Bob is an anonymous visitor")
def bob_is_anonymous(context: Context) -> None:
    """Reuse the working anonymous AT primitive without creating Bob.

    :param context: Real AT Context. Example: context.client is available.
    :return: None. Example: authenticated cookies are removed.
    :raises RuntimeError: The Django-client harness was not initialized.
    """
    if not hasattr(context, "client"):
        raise RuntimeError("Run Experts acceptance with the Django client harness.")
    context.execute_steps("Given an anonymous AT visitor")


@then("the same five Design contributors are visible")
def same_design_contributors(context: Context) -> None:
    """Compare the guest and Elena rankings against the fixed Cedar order.

    :param context: AT Context. Example: context.response.status_code == 200.
    :return: None. Example: both see five Design cards and Development is the default.
    :raises AssertionError: Response status, identity, category or ranking differs.
    """
    guest_design = context.response
    assert guest_design.status_code == HTTPStatus.OK
    assert not guest_design.wsgi_request.user.is_authenticated
    assert guest_design.context["selected_category"] == "design"
    assert_public_design_ranking(guest_design.content.decode())

    elena = Client()
    elena.force_login(context.cedar_dataset.users_by_username["esvensson"])
    elena_design = elena.get(guest_design.wsgi_request.get_full_path())
    assert elena_design.status_code == HTTPStatus.OK
    assert elena_design.wsgi_request.user.is_authenticated
    assert_public_design_ranking(elena_design.content.decode())

    default = context.client.get(reverse("experts_list"))
    assert default.status_code == HTTPStatus.OK
    assert not default.wsgi_request.user.is_authenticated
    current_tab = find_by_test_id(default.content, "experts-category-development")
    assert ("aria-current", "page") in current_tab.attributes
    leaderboard = find_by_test_id(default.content, "experts-leaderboard")
    cards = [node for node in _walk_elements(leaderboard) if node.name == "article"]
    assert len(cards) == len(_DEVELOPMENT_RANKING)
    for card, (username, total) in zip(cards, _DEVELOPMENT_RANKING, strict=True):
        assert ("data-testid", f"experts-card-{username}") in card.attributes
        score = find_by_test_id(str(card), "expert-card-karma")
        assert element_text(score) == f"{total:,}"


@then("a guest banner offers Sign In and Register")
def guest_banner_offers_authentication(context: Context) -> None:
    """Apply the shared banner assertion to real rendered HTML.

    :param context: AT Context. Example: context.response contains the list.
    :return: None. Example: two correctly named auth anchors are present.
    :raises AssertionError: Banner or destination fails the contract.
    """
    assert_guest_auth_banner(context.response.content.decode())


@then("no own-profile Karma card or API token is present")
def private_account_controls_are_absent(context: Context) -> None:
    """Verify the server-rendered contact gate and private account boundary.

    :param context: AT Context. Example: anonymous Design response.
    :return: None. Example: contact stays disabled while its explanation is present.
    :raises AssertionError: Private data appears or the contact gate differs.
    """
    response = context.response
    html = response.content.decode()
    assert_no_private_account_controls(html)
    users = context.cedar_dataset.users_by_username.values()
    private_values = [user.email for user in users if user.email]
    private_values.extend(Token.objects.values_list("key", flat=True))
    surface = unescape(html).casefold()
    assert "mailto:" not in surface, "Guest HTML exposed a mail destination."
    leaked = any(value.casefold() in surface for value in private_values)
    assert not leaked, "Guest HTML exposed private Cedar contact or account data."
    leaderboard = find_by_test_id(html, "experts-leaderboard")
    cards = [node for node in _walk_elements(leaderboard) if node.name == "article"]
    for card in cards:
        username = dict(card.attributes)["data-testid"].removeprefix("experts-card-")
        tooltip = find_by_test_id(str(card), "experts-reach-out-guest-tooltip")
        description_id = f"reach-explanation-{username}"
        assert ("aria-describedby", description_id) in tooltip.attributes
        assert ("title", GUEST_CONTACT_EXPLANATION) in tooltip.attributes
        assert ("tabindex", "0") in tooltip.attributes
        assert ("data-bs-toggle", "tooltip") in tooltip.attributes
        descriptions = [
            element_text(node)
            for node in _walk_elements(tooltip)
            if ("id", description_id) in node.attributes
        ]
        assert descriptions == [GUEST_CONTACT_EXPLANATION]
        button = find_by_test_id(str(tooltip), f"experts-reach-out-disabled-{username}")
        assert button.name == "button" and element_text(button) == "Reach out"
        button_attributes = dict(button.attributes)
        assert "disabled" in button_attributes and "href" not in button_attributes
