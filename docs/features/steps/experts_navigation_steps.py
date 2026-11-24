"""Exercise Experts navigation through the rendered app shell."""

from __future__ import annotations

import hashlib
import json
import logging

from behave import given, then, when
from behave.runner import Context
from django.contrib.auth.models import User
from django.core import mail
from django.db import connection
from django.test.html import Element, parse_html
from django.urls import reverse

from methodology.models import AgentInteraction, ExpertProfile, KarmaAward
from tests.support.experts_data import CEDAR_PASSWORD
from tests.support.experts_html import _walk_elements, element_text, find_by_test_id

logger = logging.getLogger(__name__)
_ELENA_USERNAME = "esvensson"
_SIDEBAR_TEST_ID = "app-sidebar"
_EXPERTS_LINK_TEST_ID = "nav-experts"
_CATEGORY_TABS_TEST_ID = "experts-category-tabs"
_S48_SECTION_LABELS = (
    ("sidebar-sec-workspace", "Workspace"),
    ("sidebar-sec-methodology", "Methodology"),
    ("sidebar-sec-collaborate", "Collaborate"),
)
_S48_LINK_GROUPS = (
    (("Home", "/dashboard/", "nav-dashboard"),),
    (
        ("Playbooks", "/playbooks/", "nav-playbooks"),
        ("Workflows", "/workflows/", "nav-workflows"),
        ("Phases", "/phases/", "nav-phases"),
        ("Activities", "/activities/", "nav-activities"),
        ("Artifacts", "/artifacts/", "nav-artifacts"),
        ("Agents", "/agents/", "nav-agents"),
        ("Skills", "/skills/", "nav-skills"),
        ("Rules", "/rules/", "nav-rules"),
    ),
    (
        ("Teams", "/teams/", "nav-teams"),
        ("Experts", "/experts/", "nav-experts"),
        ("PIPs", "/pips/", "nav-pips"),
    ),
)
_S48_PROTECTED_MODELS = (User, KarmaAward, ExpertProfile, AgentInteraction)


@given("Elena is authenticated")
@given("Elena is authenticated in FOB")
def elena_is_authenticated(context: Context) -> None:
    """Authenticate the real baseline Elena account.

    :param context: AT context with CedarDataset. Example: context.cedar_dataset.
    :return: None. Example: None.
    :raises AssertionError: If baseline Elena is missing or sign-in fails.
    """
    elena = context.cedar_dataset.users_by_username.get(_ELENA_USERNAME)
    assert elena is not None, "The Cedar baseline must contain Elena."
    logger.info("Experts navigation AT | sign-in entry | user_id=%s", elena.pk)
    signed_in = context.client.login(username=elena.username, password=CEDAR_PASSWORD)
    assert signed_in, "Elena's Cedar account could not sign in."
    logger.info("Experts navigation AT | sign-in exit | user_id=%s", elena.pk)


@when("she follows the Experts navigation link")
@when("she follows Experts")
def follows_experts_navigation_link(context: Context) -> None:
    """Follow the actual rendered shell destination with the Django client.

    :param context: Authenticated AT context. Example: Elena's client.
    :return: None. Example: None.
    :raises AssertionError: If the signed-in shell, link or destination is wrong.
    """
    landing = getattr(context, "response", None)
    if landing is None:
        landing = context.client.get(reverse("dashboard"))
    assert landing.status_code == 200, "The app sidebar did not load."
    elena = landing.wsgi_request.user
    assert elena.is_authenticated and elena.username == _ELENA_USERNAME
    href = _experts_navigation_href(landing.content.decode(landing.charset))

    logger.info("Experts navigation AT | follow entry | path=%s", href)
    context.response = context.client.get(href)
    assert context.response.status_code == 200, "The Experts page did not load."
    assert context.response.wsgi_request.user == elena, "Elena's session was lost."
    logger.info(
        "Experts navigation AT | follow exit | status=%s", context.response.status_code
    )


def _experts_navigation_href(html: str) -> str:
    """Extract and validate the single Experts sidebar destination.

    :param html: Rendered existing page. Example: HTML containing nav-experts.
    :return: Local destination. Example: "/experts/".
    :raises AssertionError: If missing, duplicated or pointing to another route.
    """
    sidebar = find_by_test_id(html, _SIDEBAR_TEST_ID)
    link = find_by_test_id(str(sidebar), _EXPERTS_LINK_TEST_ID)
    assert link.name == "a" and element_text(link) == "Experts"
    href = dict(link.attributes).get("href", "")
    assert href == reverse("experts_list"), f"Unexpected Experts link: {href!r}"
    return href


@then('the URL is "{path}"')
def url_is(context: Context, path: str) -> None:
    """Compare the actual final response request path and query.

    :param context: AT context with real response. Example: Experts response.
    :param path: Expected local URL. Example: "/experts/?category=design".
    :return: None. Example: None.
    :raises AssertionError: If the actual URL differs.
    """
    actual_path = context.response.wsgi_request.get_full_path()
    assert actual_path == path, f"Expected URL {path!r}, got {actual_path!r}."


@then('the page title is "{title}"')
def page_title_is(context: Context, title: str) -> None:
    """Check the document title and visible page heading.

    :param context: AT context with real response. Example: Experts response.
    :param title: Required title. Example: "Experts".
    :return: None. Example: None.
    :raises AssertionError: If document title or page heading differs.
    """
    response = context.response
    nodes = tuple(_walk_elements(parse_html(response.content.decode(response.charset))))
    for tag in ("title", "h1"):
        actual = [element_text(node) for node in nodes if node.name == tag]
        assert actual == [title], f"Expected one {tag} with {title!r}, got {actual!r}."


@then('the subtitle is "{subtitle}"')
def subtitle_is(context: Context, subtitle: str) -> None:
    """Check the rendered page subtitle exactly.

    :param context: AT context with real response. Example: Experts response.
    :param subtitle: Required text. Example: "Top contributors by playbook category".
    :return: None. Example: None.
    :raises AssertionError: If the subtitle differs.
    """
    response = context.response
    page = parse_html(response.content.decode(response.charset))
    actual = [
        element_text(child)
        for header in _walk_elements(page)
        if header.name == "header"
        and "hg-page-header" in dict(header.attributes).get("class", "").split()
        for child in header.children
        if isinstance(child, Element) and child.name == "p"
    ]
    assert actual == [subtitle], f"Expected subtitle {subtitle!r}, got {actual!r}."


@then('the "{category}" category is current')
def category_is_current(context: Context, category: str) -> None:
    """Check the selected category's semantic current-page state.

    :param context: AT context with real response. Example: Experts response.
    :param category: Visible category label. Example: "Development".
    :return: None. Example: None.
    :raises AssertionError: If the category lacks aria-current="page".
    """
    tabs = find_by_test_id(context.response.content, _CATEGORY_TABS_TEST_ID)
    current = [
        element_text(link)
        for link in _walk_elements(tabs)
        if link.name == "a" and ("aria-current", "page") in link.attributes
    ]
    assert current == [category], f"Expected {category!r} as current, got {current!r}."


@when("she opens the Collaborate section of the app sidebar")
def opens_collaborate_section(context: Context) -> None:
    """Inspect the real labelled section in the server response.

    :param context: Real AT context. Example: authenticated Elena client.
    :return: None. Example: None.
    :raises AssertionError: If sidebar or labelled Collaborate list is absent.
    """
    elena = context.cedar_dataset.users_by_username[_ELENA_USERNAME]
    elena.refresh_from_db()
    assert not elena.is_staff and not elena.is_superuser
    context.s48_state_before = _s48_state_fingerprint()
    context.s48_callbacks_before = tuple(connection.run_on_commit)
    context.response = context.client.get(reverse("dashboard"))
    response = context.response
    assert response.status_code == 200 and not response.has_header("Location")
    assert response.wsgi_request.user == elena
    assert response.wsgi_request.path == reverse("dashboard")
    assert response.context["chrome"] == "authenticated"
    _s48_sidebar_structure(response.content)
    _s48_assert_current(
        find_by_test_id(response.content, _SIDEBAR_TEST_ID), "nav-dashboard"
    )
    assert _s48_state_fingerprint() == context.s48_state_before
    assert tuple(connection.run_on_commit) == context.s48_callbacks_before
    logger.info("Experts sidebar AT | section exit | actor_id=%s", elena.pk)


@then('Experts is a link to "{path}" with data-testid "{test_id}"')
def experts_sidebar_link(context: Context, path: str, test_id: str) -> None:
    """Check the unique anchor within the real Collaborate list.

    :param context: AT context with response. Example: dashboard response.
    :param path: Exact destination. Example: "/experts/".
    :param test_id: Stable selector. Example: "nav-experts".
    :return: None. Example: None.
    :raises AssertionError: If destination, accessible name or grouping differs.
    """
    assert (path, test_id) == (reverse("experts_list"), _EXPERTS_LINK_TEST_ID)
    _, collaborate = _s48_sidebar_structure(context.response.content)
    link = find_by_test_id(str(collaborate), test_id)
    attributes = dict(link.attributes)
    assert link.name == "a" and element_text(link) == "Experts"
    assert attributes["href"] == path
    assert attributes["title"] == "Top contributors by playbook category"
    context.s48_experts_href = attributes["href"]


@then('"{test_id}" is present and Experts is the active navigation item')
def experts_sidebar_is_current(context: Context, test_id: str) -> None:
    """Prove the destination and scoped sidebar current state together.

    :param context: AT context after actual href GET. Example: Experts response.
    :param test_id: Required destination marker. Example: "experts-leaderboard".
    :return: None. Example: None.
    :raises AssertionError: If marker or exclusive semantic current state differs.
    """
    assert test_id == "experts-leaderboard"
    response = context.response
    assert response.status_code == 200 and not response.has_header("Location")
    assert response.wsgi_request.get_full_path() == context.s48_experts_href
    assert response.wsgi_request.user.username == _ELENA_USERNAME
    assert response.wsgi_request.user.is_authenticated
    assert response.context["chrome"] == "authenticated"
    assert "experts/list.html" in [item.name for item in response.templates]
    find_by_test_id(response.content, test_id)
    sidebar, _ = _s48_sidebar_structure(response.content)
    _s48_assert_current(sidebar, _EXPERTS_LINK_TEST_ID)
    _s48_assert_current(
        find_by_test_id(response.content, "realm-nav-list"), "realm-nav-mimir"
    )
    _s48_assert_current(
        find_by_test_id(response.content, _CATEGORY_TABS_TEST_ID),
        "experts-category-development",
    )
    assert _s48_state_fingerprint() == context.s48_state_before
    assert tuple(connection.run_on_commit) == context.s48_callbacks_before
    logger.info(
        "Experts sidebar AT | destination exit | status=%s", response.status_code
    )


def _s48_sidebar_structure(html: str | bytes) -> tuple[Element, Element]:
    """Validate original shell groups and return the real Collaborate list.

    :param html: Actual response bytes. Example: dashboard response.content.
    :return: Parsed sidebar and group. Example: aside and Collaborate ul.
    :raises AssertionError: Labels, order, links or accessible structure differ.
    """
    sidebar = find_by_test_id(html, _SIDEBAR_TEST_ID)
    assert sidebar.name == "aside"
    assert dict(sidebar.attributes)["aria-label"] == "Mimir in-app navigation"
    nodes = tuple(_walk_elements(sidebar))
    labels = [
        node
        for node in nodes
        if "mm-sidebar-section-label" in dict(node.attributes).get("class", "").split()
    ]
    assert (
        tuple((dict(node.attributes)["id"], element_text(node)) for node in labels)
        == _S48_SECTION_LABELS
    )
    groups = [node for node in nodes if node.name == "ul"]
    assert len(groups) == len(_S48_SECTION_LABELS)
    for group, (label_id, _), expected in zip(
        groups, _S48_SECTION_LABELS, _S48_LINK_GROUPS, strict=True
    ):
        assert dict(group.attributes)["aria-labelledby"] == label_id
        _s48_assert_group(group, expected)
    return sidebar, groups[-1]


def _s48_assert_group(
    group: Element, expected: tuple[tuple[str, str, str], ...]
) -> None:
    """Require original ordered destinations and decorative icons.

    :param group: Actual labelled sidebar ul. Example: Collaborate.
    :param expected: Contract links in order. Example: Teams, Experts, PIPs.
    :return: None. Example: all actual anchors match the contract.
    :raises AssertionError: A link, title, order or icon differs.
    """
    links = [node for node in _walk_elements(group) if node.name == "a"]
    actual = tuple(
        (
            element_text(node),
            dict(node.attributes).get("href"),
            dict(node.attributes).get("data-testid"),
        )
        for node in links
    )
    assert actual == expected
    for link in links:
        assert dict(link.attributes).get("title", "").strip()
        icons = [node for node in _walk_elements(link) if node.name == "i"]
        assert len(icons) == 1 and ("aria-hidden", "true") in icons[0].attributes
        assert element_text(icons[0]) == ""


def _s48_assert_current(container: Element, test_id: str) -> None:
    """Require both current-page signals on exactly one scoped anchor.

    :param container: Actual parsed region. Example: sidebar or realm nav.
    :param test_id: Sole current anchor. Example: nav-experts.
    :return: None. Example: every other scoped anchor is not current.
    :raises AssertionError: Semantic current or active class differs.
    """
    links = [
        dict(node.attributes) for node in _walk_elements(container) if node.name == "a"
    ]
    assert [
        link.get("data-testid") for link in links if link.get("aria-current") == "page"
    ] == [test_id]
    assert [
        link.get("data-testid")
        for link in links
        if "active" in link.get("class", "").split()
    ] == [test_id]


def _s48_state_fingerprint() -> str:
    """Hash every protected stored field and complete existing mail contents.

    :return: Private deterministic digest. Example: SHA256 of complete rows.
    :raises TypeError: A stored value cannot use the real JSON adapter.
    """
    rows = [
        (model._meta.label, list(model.objects.order_by("pk").values_list()))
        for model in _S48_PROTECTED_MODELS
    ]
    messages = [vars(message) for message in getattr(mail, "outbox", ())]
    rows.append(("mail", messages))
    return hashlib.sha256(
        json.dumps(rows, default=str, sort_keys=True).encode()
    ).hexdigest()
