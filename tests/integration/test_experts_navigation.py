from __future__ import annotations

import pytest
from django.test import Client
from django.test.html import Element, parse_html
from django.urls import reverse
from pytest import LogCaptureFixture

from tests.support.experts_data import CedarDataset, load_cedar_baseline
from tests.support.experts_html import _walk_elements, element_text, find_by_test_id
from tests.support.experts_logs import capture_experts_logs
from tests.support.log_story import assert_log_story


@pytest.mark.django_db
def test_experts_navigation_with_authenticated_elena_shows_default_page(
    client: Client,
) -> None:
    """Follow the rendered sidebar link against the real Cedar database.

    :param client: Real Django client. Example: authenticated Elena client.
    :return: None. Example: None.
    :raises AssertionError: If route, page chrome, default state or rank differs.
    """
    elena = load_cedar_baseline().users_by_username["esvensson"]
    client.force_login(elena)
    landing = client.get(reverse("dashboard"))
    assert landing.status_code == 200
    landing_sidebar = find_by_test_id(landing.content, "app-sidebar")
    experts_link = find_by_test_id(str(landing_sidebar), "nav-experts")
    assert experts_link.name == "a"
    assert element_text(experts_link) == "Experts"
    href = dict(experts_link.attributes)["href"]
    assert href == "/experts/"

    response = client.get(href)
    assert response.status_code == 200
    assert response.wsgi_request.get_full_path() == href
    assert response.wsgi_request.user == elena
    _assert_experts_page(response.content.decode(response.charset))


def _assert_experts_page(html: str) -> None:
    """Verify the production landing page and its current navigation state.

    :param html: Real Experts response. Example: the default signed-in list.
    :return: None after the expected page and contributors are found.
    :raises AssertionError: If any rendered page contract differs.
    """
    nodes = tuple(_walk_elements(parse_html(html)))
    assert [element_text(node) for node in nodes if node.name == "title"] == ["Experts"]
    assert [element_text(node) for node in nodes if node.name == "h1"] == ["Experts"]
    assert "Top contributors by playbook category" in [
        element_text(node) for node in nodes if node.name == "p"
    ]
    assert all(
        ("data-testid", "mockup-banner") not in node.attributes for node in nodes
    )
    assert all(
        not dict(node.attributes).get("href", "").startswith("/mockups/")
        for node in nodes
        if node.name == "a"
    )
    realm_navbar = find_by_test_id(html, "realm-navbar")
    find_by_test_id(str(realm_navbar), "logout-link")
    sidebar = find_by_test_id(html, "app-sidebar")
    _assert_current_link(sidebar, "nav-experts")
    tabs = find_by_test_id(html, "experts-category-tabs")
    _assert_current_link(tabs, "experts-category-development")
    development = find_by_test_id(str(tabs), "experts-category-development")
    assert element_text(development) == "Development"
    _assert_development_ranking(find_by_test_id(html, "experts-leaderboard"))


def _assert_current_link(container: Element, test_id: str) -> None:
    """Require one link with both current-page semantics and active styling.

    :param container: Parsed navigation region. Example: the app sidebar.
    :param test_id: Expected current link ID. Example: "nav-experts".
    :return: None after both current-state signals agree.
    :raises AssertionError: If the wrong set of links has either current state.
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


def _assert_development_ranking(leaderboard: Element) -> None:
    """Check the signed-in Cedar Development leaderboard's visible rank order.

    :param leaderboard: Parsed ranked section. Example: experts-leaderboard.
    :return: None after Mike and Jordan are found in order with their ranks.
    :raises AssertionError: If the cards, display names or ranks differ.
    """
    cards = [
        child
        for child in leaderboard.children
        if isinstance(child, Element) and child.name == "article"
    ]
    assert [dict(card.attributes)["data-testid"] for card in cards] == [
        "experts-card-mchen",
        "experts-card-jlee",
    ]
    for rank, (card, name) in enumerate(
        zip(cards, ("Mike Chen", "Jordan Lee")), start=1
    ):
        assert [
            element_text(node) for node in _walk_elements(card) if node.name == "h2"
        ] == [name]
        assert element_text(find_by_test_id(str(card), "expert-card-rank")) == str(rank)


@pytest.mark.django_db
def test_experts_navigation_log_story_happy(
    client: Client, cedar_dataset: CedarDataset, caplog: LogCaptureFixture
) -> None:
    """Prove the authenticated Experts shell log story.

    :param client: Real Django client. Example: authenticated Elena client.
    :param cedar_dataset: Real Cedar baseline. Example: Elena is esvensson.
    :param caplog: INFO capture fixture. Example: captured shell records.
    :return: None. Example: None.
    :raises AssertionError: If response or a Section E beat is missing.
    """
    client.force_login(cedar_dataset.users_by_username["esvensson"])
    with capture_experts_logs(caplog, ("methodology.context_processors",)):
        response = client.get(reverse("experts_list"))
    assert response.status_code == 200
    assert response.context["nav_section"] == "experts"
    assert response.context["chrome"] == "authenticated"
    assert_log_story(
        caplog,
        where="primary_nav_section",
        beats={
            "entry": ("entry", "path=/experts/"),
            "branch": ("branch", "chrome=authenticated"),
            "exit": ("exit", "nav_section=experts"),
        },
    )
