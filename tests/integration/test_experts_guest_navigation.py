"""Real HTTP certification for the anonymous Experts sidebar contract."""

from __future__ import annotations

import hashlib
import json
from html import unescape
from http import HTTPStatus

import pytest
from django.apps import apps
from django.conf import settings
from django.contrib.auth.models import User
from django.core import mail
from django.http import HttpResponse
from django.test import Client, TestCase
from django.test.html import Element
from django.urls import reverse
from rest_framework.authtoken.models import Token

from methodology.models import Playbook, ProcessImprovementProposal
from tests.support.experts_data import CedarDataset, load_cedar_baseline
from tests.support.experts_guest_assertions import (
    assert_guest_auth_banner,
    assert_no_private_account_controls,
    assert_public_design_ranking,
)
from tests.support.experts_html import _walk_elements, element_text, find_by_test_id

_PRIVATE_PLAYBOOK = "Cedar Bid Pricing"
_PRIVATE_PROPOSAL = "Internal staffing notes for Cedar"
_PRIVATE_TOKEN = "DEMO_ONLY_NOT_A_REAL_TOKEN"
_PRIVATE_HOOKS = {
    "user-display",
    "logout-link",
    "notification-bell",
    "global-search-form",
    "feedback-open-tab",
}
_DEVELOPMENT_RANKING = (("mchen", 12450), ("jlee", 6100))
_COLLABORATE_LINKS = ("nav-teams", "nav-experts", "nav-pips")


@pytest.mark.django_db
def test_guest_navigation_with_sidebar_href_reaches_public_experts(
    client: Client,
) -> None:
    """Follow the real guest shell link without authenticating.

    :param client: Real Django Client. Example: a fresh anonymous client.
    :return: None. Example: public 200 responses and an unchanged database.
    :raises AssertionError: Navigation, category, privacy or persisted state differs.
    """
    dataset = load_cedar_baseline()
    private_values = _private_cedar_values(dataset)
    assert not User.objects.filter(username__iexact="bob").exists()
    before = _guest_state()
    with TestCase.captureOnCommitCallbacks(execute=False) as callbacks:
        landing = client.get("/")
        _assert_public_response(landing, private_values)
        href = _assert_guest_sidebar_link(landing)
        response = client.get(href, follow=False)
        _assert_experts_destination(response, private_values)
        _certify_public_design_and_detail(client, response, private_values)
    assert callbacks == []
    assert settings.SESSION_COOKIE_NAME not in client.cookies
    assert _guest_state() == before, "Guest navigation changed persisted state."


def _guest_state() -> str:
    """Fingerprint every model and M2M row plus local mail delivery count.

    :return: Private digest. Example: a SHA256 hex string.
    :raises TypeError: A stored field cannot use the real serialization adapter.
    """
    models = sorted(
        apps.get_models(include_auto_created=True), key=lambda m: m._meta.label
    )
    rows = [
        (model._meta.label, list(model.objects.order_by("pk").values_list()))
        for model in models
    ]
    rows.append(("mail_count", len(getattr(mail, "outbox", ()))))
    return hashlib.sha256(
        json.dumps(rows, default=str, sort_keys=True).encode()
    ).hexdigest()


def _private_cedar_values(dataset: CedarDataset) -> tuple[str, ...]:
    """Require the genuine private fixture before checking its non-disclosure.

    :param dataset: Imported Cedar objects. Example: users_by_username["mchen"].
    :return: Private values to exclude. Example: fixture email and token strings.
    :raises AssertionError: Required private playbook, proposal or token is absent.
    """
    assert Playbook.objects.filter(
        name=_PRIVATE_PLAYBOOK, visibility="private"
    ).exists()
    assert ProcessImprovementProposal.objects.filter(
        title=_PRIVATE_PROPOSAL, status=ProcessImprovementProposal.STATUS_DRAFT
    ).exists()
    tokens = tuple(Token.objects.order_by("pk").values_list("key", flat=True))
    assert _PRIVATE_TOKEN in tokens
    emails = tuple(
        user.email for user in dataset.users_by_username.values() if user.email
    )
    assert emails
    return (_PRIVATE_PLAYBOOK, _PRIVATE_PROPOSAL, *tokens, *emails)


def _assert_public_response(
    response: HttpResponse, private_values: tuple[str, ...], status: int = HTTPStatus.OK
) -> None:
    """Check real anonymous response status, top actions and private-value absence.

    :param response: Actual Django response. Example: client.get("/experts/").
    :param private_values: Real fixture secrets. Example: the private token sentinel.
    :param status: Required status. Example: 404 for the non-expert Nora.
    :return: None. Example: anonymous public response retained.
    :raises AssertionError: A redirect, account control or private value appears.
    """
    assert response.status_code == status and not response.has_header("Location")
    assert not response.wsgi_request.user.is_authenticated
    html = response.content.decode()
    assert_no_private_account_controls(html)
    surface = unescape(html).casefold() + repr(response.context).casefold()
    assert "mailto:" not in surface
    assert not any(value.casefold() in surface for value in private_values)
    for hook, route in (("login-link", "login"), ("register-link", "register")):
        link = find_by_test_id(html, hook)
        assert link.name == "a" and dict(link.attributes)["href"] == reverse(route)
    sidebar = find_by_test_id(html, "app-sidebar")
    assert sidebar.name == "aside"
    assert not _PRIVATE_HOOKS.intersection(
        value
        for node in _walk_elements(find_by_test_id(html, "realm-navbar"))
        for name, value in node.attributes
        if name == "data-testid"
    )
    assert 'id="navbar-user-menu"' not in html


def _assert_guest_sidebar_link(response: HttpResponse) -> str:
    """Resolve the unique real Experts href from the Collaborate section.

    :param response: Real public shell response. Example: client.get("/").
    :return: Actual rendered local href. Example: "/experts/".
    :raises AssertionError: Group membership, uniqueness or destination differs.
    """
    sidebar = find_by_test_id(response.content, "app-sidebar")
    groups = [
        node
        for node in _walk_elements(sidebar)
        if node.name == "ul"
        and ("aria-labelledby", "sidebar-sec-collaborate") in node.attributes
    ]
    assert len(groups) == 1
    links = [node for node in _walk_elements(groups[0]) if node.name == "a"]
    assert (
        tuple(dict(node.attributes)["data-testid"] for node in links)
        == _COLLABORATE_LINKS
    )
    whole_page_link = find_by_test_id(response.content, "nav-experts")
    link = links[_COLLABORATE_LINKS.index("nav-experts")]
    assert dict(link.attributes) == dict(whole_page_link.attributes)
    assert element_text(link) == element_text(whole_page_link) == "Experts"
    href = dict(link.attributes)["href"]
    assert link.name == "a" and href == reverse("experts_list") == "/experts/"
    return href


def _assert_only_current(root: Element, expected_hook: str) -> None:
    """Require active class and accessible current-page state on the same link.

    :param root: Actual parsed region. Example: the application sidebar.
    :param expected_hook: Its sole active action. Example: "nav-experts".
    :return: None. Example: one correctly marked link.
    :raises AssertionError: Active and aria-current state differ or are duplicated.
    """
    nodes = tuple(_walk_elements(root))
    current = [
        dict(node.attributes).get("data-testid")
        for node in nodes
        if ("aria-current", "page") in node.attributes
    ]
    active = [
        dict(node.attributes).get("data-testid")
        for node in nodes
        if "active" in dict(node.attributes).get("class", "").split()
    ]
    assert current == active == [expected_hook]


def _assert_experts_destination(
    response: HttpResponse, private_values: tuple[str, ...]
) -> None:
    """Assert the exact public landing, default category and existing guest banner.

    :param response: Actual followed sidebar destination. Example: client.get(href).
    :param private_values: Required exclusions. Example: Cedar private emails.
    :return: None. Example: default Development and current Experts.
    :raises AssertionError: Public navigation, ranking or authentication actions differ.
    """
    _assert_public_response(response, private_values)
    assert response.wsgi_request.get_full_path() == "/experts/"
    assert "experts/list.html" in [template.name for template in response.templates]
    assert response.context["selected_category"] == "development"
    assert (
        tuple(
            (row["username"], row["total_points"]) for row in response.context["people"]
        )
        == _DEVELOPMENT_RANKING
    )
    html = response.content.decode()
    assert_guest_auth_banner(html)
    _assert_only_current(find_by_test_id(html, "app-sidebar"), "nav-experts")
    _assert_only_current(
        find_by_test_id(html, "experts-category-tabs"), "experts-category-development"
    )


def _certify_public_design_and_detail(
    client: Client, response: HttpResponse, private_values: tuple[str, ...]
) -> None:
    """Follow real Design/profile links and preserve the existing non-expert 404.

    :param client: Same anonymous client. Example: Bob's fresh visitor client.
    :param response: Actual default landing response. Example: Development.
    :param private_values: Required exclusions. Example: unpublished proposal title.
    :return: None. Example: public Maria evidence and private Nora rejection.
    :raises AssertionError: A declared public or denied read changes its boundary.
    """
    tab = find_by_test_id(response.content, "experts-category-design")
    design = client.get(dict(tab.attributes)["href"], follow=False)
    _assert_public_response(design, private_values)
    assert_public_design_ranking(design.content.decode())
    link = find_by_test_id(design.content, "experts-view-profile-mrodriguez")
    profile = client.get(dict(link.attributes)["href"], follow=False)
    _assert_public_response(profile, private_values)
    assert (
        element_text(find_by_test_id(profile.content, "expert-name"))
        == "Maria Rodriguez"
    )
    denied = client.get(reverse("expert_detail", args=["nberg"]), follow=False)
    _assert_public_response(denied, private_values, status=HTTPStatus.NOT_FOUND)
