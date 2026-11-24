"""Certify the existing public guest navigation using real Django responses."""

from __future__ import annotations

import hashlib
import json
import logging
from html import unescape
from http import HTTPStatus
from urllib.parse import urlsplit

from behave import then, when
from behave.runner import Context
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
from tests.support.experts_data import CedarDataset
from tests.support.experts_guest_assertions import (
    assert_guest_auth_banner,
    assert_no_private_account_controls,
    assert_public_design_ranking,
)
from tests.support.experts_html import _walk_elements, element_text, find_by_test_id

logger = logging.getLogger(__name__)
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


@when("he follows Experts from the app sidebar")
def guest_follows_experts_from_sidebar(context: Context) -> None:
    """Follow the rendered public shell href using the real Django client.

    :param context: Prepared AT Context. Example: context.client is anonymous.
    :return: None. Example: context.response contains GET /experts/ response.
    :raises AssertionError: Public shell, unique link or anonymous baseline is wrong.
    """
    assert not User.objects.filter(username__iexact="bob").exists()
    assert settings.SESSION_COOKIE_NAME not in context.client.cookies
    context.s49_private_values = _private_cedar_values(context.cedar_dataset)
    context.s49_before_state = _guest_state()
    context.s49_before_cookies = context.client.cookies.output()
    context.s49_callback_capture = TestCase.captureOnCommitCallbacks(execute=False)
    context.s49_callbacks = context.s49_callback_capture.__enter__()
    context.s49_callbacks_closed = False
    context.add_cleanup(_close_callback_capture, context)
    context.s49_home = context.client.get("/", follow=False)
    _assert_public_response(context.s49_home, context.s49_private_values)
    href = _assert_guest_sidebar_link(context.s49_home)
    logger.info("Guest navigation AT | follow entry | path=%s", href)
    context.response = context.client.get(href, follow=False)
    logger.info(
        "Guest navigation AT | follow exit | status=%s", context.response.status_code
    )


@then('he reaches "{path}" without a login redirect')
def guest_reaches_public_path(context: Context, path: str) -> None:
    """Assert the real response reaches the declared public destination.

    :param context: AT Context. Example: response from rendered sidebar href.
    :param path: Expected local path str. Example: "/experts/".
    :return: None. Example: HTTP 200 at /experts/ with no Location header.
    :raises ValueError: Expected path is not an absolute local path.
    :raises AssertionError: Response redirects, authenticates or lands elsewhere.
    """
    if not isinstance(path, str) or not path.startswith("/") or path.startswith("//"):
        raise ValueError("Expected an absolute local navigation path.")
    target = urlsplit(path)
    if target.scheme or target.netloc or target.query or target.fragment:
        raise ValueError("Expected an absolute local path without URL components.")
    assert path == reverse("experts_list") == "/experts/"
    assert context.response.wsgi_request.get_full_path() == path
    _assert_experts_destination(context.response, context.s49_private_values)


@then("the guest banner explains sign-in and registration")
def guest_banner_explains_authentication(context: Context) -> None:
    """Check the live banner, public boundaries and unchanged guest state.

    :param context: AT Context. Example: context.response contains Experts HTML.
    :return: None. Example: banner actions work without private data or writes.
    :raises AssertionError: Banner, public access, privacy or stored state differs.
    """
    _assert_public_response(context.s49_home, context.s49_private_values)
    _assert_guest_sidebar_link(context.s49_home)
    _assert_experts_destination(context.response, context.s49_private_values)
    _certify_public_design_and_detail(
        context.client, context.response, context.s49_private_values
    )
    _close_callback_capture(context)
    assert context.s49_callbacks == [], "Guest navigation queued commit callbacks."
    assert context.client.cookies.output() == context.s49_before_cookies
    assert settings.SESSION_COOKIE_NAME not in context.client.cookies
    assert not User.objects.filter(username__iexact="bob").exists()
    unchanged = _guest_state() == context.s49_before_state
    assert unchanged, "Guest navigation changed persisted state."
    logger.info(
        "Guest navigation AT | verified | public=true persisted_state=unchanged"
    )


def _close_callback_capture(context: Context) -> None:
    """Close the real callback collector exactly once, including failed scenarios.

    :param context: Prepared AT context. Example: its collector is still open.
    :return: None. Example: callbacks are available for final verification.
    :raises RuntimeError: The callback collector could not be closed.
    """
    if not context.s49_callbacks_closed:
        context.s49_callback_capture.__exit__(None, None, None)
        context.s49_callbacks_closed = True


def _guest_state() -> str:
    """Fingerprint every model and M2M row plus complete existing local mail.

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
    rows.append(("mail", [vars(message) for message in getattr(mail, "outbox", ())]))
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
    assert element_text(find_by_test_id(html, "guest-auth-banner")) == (
        "Sign in to reach out to a contributor. Sign In · Register"
    )
    _assert_development_cards(html)
    _assert_only_current(find_by_test_id(html, "app-sidebar"), "nav-experts")
    _assert_only_current(
        find_by_test_id(html, "experts-category-tabs"), "experts-category-development"
    )


def _assert_development_cards(html: str) -> None:
    """Check the actual default cards rather than trusting response context alone.

    :param html: Rendered destination. Example: response.content.decode().
    :return: None. Example: exactly Michael then Jordan with their real totals.
    :raises AssertionError: Card identity, order, score or accessible rank differs.
    """
    leaderboard = find_by_test_id(html, "experts-leaderboard")
    cards = [node for node in _walk_elements(leaderboard) if node.name == "article"]
    assert len(cards) == len(_DEVELOPMENT_RANKING)
    for rank, (card, (username, total)) in enumerate(
        zip(cards, _DEVELOPMENT_RANKING, strict=True), start=1
    ):
        attributes = dict(card.attributes)
        assert attributes["data-testid"] == f"experts-card-{username}"
        assert attributes["data-total-points"] == str(total)
        score = find_by_test_id(str(card), "expert-card-karma")
        assert element_text(score) == f"{total:,}"
        label = find_by_test_id(str(card), "expert-card-rank")
        assert element_text(label) == str(rank)
        assert dict(label.attributes)["aria-label"] == f"Rank {rank}"


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
