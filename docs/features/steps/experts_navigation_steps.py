"""Exercise Experts navigation through the rendered app shell."""

from __future__ import annotations

import logging

from behave import given, then, when
from behave.runner import Context
from django.test.html import Element, parse_html
from django.urls import reverse

from tests.support.experts_data import CEDAR_PASSWORD
from tests.support.experts_html import _walk_elements, element_text, find_by_test_id

logger = logging.getLogger(__name__)
_ELENA_USERNAME = "esvensson"
_SIDEBAR_TEST_ID = "app-sidebar"
_EXPERTS_LINK_TEST_ID = "nav-experts"
_CATEGORY_TABS_TEST_ID = "experts-category-tabs"


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
    raise NotImplementedError()


@then('Experts is a link to "{path}" with data-testid "{test_id}"')
def experts_sidebar_link(context: Context, path: str, test_id: str) -> None:
    """Check the unique anchor within the real Collaborate list.

    :param context: AT context with response. Example: dashboard response.
    :param path: Exact destination. Example: "/experts/".
    :param test_id: Stable selector. Example: "nav-experts".
    :return: None. Example: None.
    :raises AssertionError: If destination, accessible name or grouping differs.
    """
    raise NotImplementedError()


@then('"{test_id}" is present and Experts is the active navigation item')
def experts_sidebar_is_current(context: Context, test_id: str) -> None:
    """Prove the destination and scoped sidebar current state together.

    :param context: AT context after actual href GET. Example: Experts response.
    :param test_id: Required destination marker. Example: "experts-leaderboard".
    :return: None. Example: None.
    :raises AssertionError: If marker or exclusive semantic current state differs.
    """
    raise NotImplementedError()
