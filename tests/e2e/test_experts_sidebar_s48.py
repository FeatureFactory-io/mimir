"""Actual desktop and offcanvas sidebar certification."""

from __future__ import annotations

import hashlib
import json
import re

import pytest
from django.contrib.auth.models import User
from django.core import mail
from django.db import connection
from e2e_helpers import login
from playwright.sync_api import Locator, Page, expect

from accounts.models import UserEmailVerification, UserOnboardingState
from methodology.models import AgentInteraction, ExpertProfile, KarmaAward
from tests.support.experts_data import CEDAR_PASSWORD, CedarDataset

_SECTIONS = (
    ("Workspace", (("Home", "/dashboard/", "nav-dashboard"),)),
    (
        "Methodology",
        tuple(
            (name, f"/{slug}/", f"nav-{slug}")
            for name, slug in (
                ("Playbooks", "playbooks"),
                ("Workflows", "workflows"),
                ("Phases", "phases"),
                ("Activities", "activities"),
                ("Artifacts", "artifacts"),
                ("Agents", "agents"),
                ("Skills", "skills"),
                ("Rules", "rules"),
            )
        ),
    ),
    (
        "Collaborate",
        (
            ("Teams", "/teams/", "nav-teams"),
            ("Experts", "/experts/", "nav-experts"),
            ("PIPs", "/pips/", "nav-pips"),
        ),
    ),
)
_PROTECTED_MODELS = (
    User,
    User.groups.through,
    User.user_permissions.through,
    UserEmailVerification,
    UserOnboardingState,
    KarmaAward,
    ExpertProfile,
    AgentInteraction,
)


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("viewport", [(1280, 720), (390, 844)])
def test_sidebar_with_real_navigation_opens_experts(
    page: Page,
    live_server_url: str,
    viewport: tuple[int, int],
    cedar_baseline: CedarDataset,
) -> None:
    """Follow the real Experts anchor through the existing responsive shell.

    :param page: Existing fresh Playwright page. Example: Chromium page.
    :param live_server_url: Existing real server URL. Example: http://localhost:8081.
    :param viewport: Exact viewport dimensions. Example: (390, 844).
    :param cedar_baseline: Real imported Cedar records. Example: nonstaff Elena.
    :return: None. Example: None.
    :raises AssertionError: If actual navigation or accessible current state fails.
    """
    elena = cedar_baseline.users_by_username["esvensson"]
    assert not elena.is_staff and not elena.is_superuser
    page.set_viewport_size(dict(zip(("width", "height"), viewport, strict=True)))
    login(page, live_server_url, elena.username, CEDAR_PASSWORD)
    expect(page.get_by_test_id("user-display")).to_have_text(elena.username)
    before = _protected_state()
    callbacks = tuple(connection.run_on_commit)
    page.goto(f"{live_server_url}/dashboard/")
    expect(page).to_have_url(f"{live_server_url}/dashboard/")
    _open_sidebar(page, viewport)
    _assert_shell(page, "nav-dashboard")
    assert _protected_state() == before
    assert tuple(connection.run_on_commit) == callbacks
    _follow_experts(page, live_server_url)
    _open_sidebar(page, viewport)
    _assert_shell(page, "nav-experts")
    if viewport[0] < 992:
        page.get_by_test_id("app-sidebar").get_by_role("button", name="Close").click()
        expect(page.get_by_test_id("app-sidebar")).not_to_be_visible()
    _assert_destination(page)
    assert _protected_state() == before
    assert tuple(connection.run_on_commit) == callbacks


def _follow_experts(page: Page, live_server_url: str) -> None:
    """Click the actual scoped anchor and require its real successful response.

    :param page: Browser with visible sidebar. Example: dashboard drawer.
    :param live_server_url: Existing server origin. Example: http://localhost:8081.
    :return: None after actual /experts/ navigation with status 200.
    :raises AssertionError: If the link, destination or real response differs.
    """
    link = page.get_by_test_id("app-sidebar").get_by_role(
        "link", name="Experts", exact=True
    )
    expect(link).to_have_attribute("data-testid", "nav-experts")
    href = link.get_attribute("href")
    assert href == "/experts/"
    with page.expect_navigation(wait_until="domcontentloaded") as navigation:
        link.click()
    assert navigation.value is not None and navigation.value.status == 200
    expect(page).to_have_url(f"{live_server_url}{href}")


def _open_sidebar(page: Page, viewport: tuple[int, int]) -> None:
    """Open the existing Bootstrap drawer using its real pointer control.

    :param page: Real authenticated browser page. Example: dashboard.
    :param viewport: Required CSS pixels. Example: (390, 844).
    :return: None with the actual sidebar visible.
    :raises AssertionError: If the toggle or responsive drawer is inaccessible.
    """
    sidebar = page.get_by_test_id("app-sidebar")
    expect(sidebar).to_have_count(1)
    toggle = page.get_by_test_id("sidebar-toggler")
    if viewport[0] < 992:
        expect(sidebar).not_to_be_visible()
        expect(toggle).to_be_visible()
        toggle.click()
        expect(sidebar).to_have_class(re.compile(r"\bshow\b"))
    else:
        expect(toggle).not_to_be_visible()
    expect(sidebar).to_be_visible()


def _assert_shell(page: Page, current: str) -> None:
    """Check all existing groups, destinations and scoped current semantics.

    :param page: Actual loaded browser page. Example: authenticated Experts.
    :param current: Only current sidebar hook. Example: nav-experts.
    :return: None with the unchanged shell and reachable Experts link proven.
    :raises AssertionError: If groups, order, links, current state or bounds differ.
    """
    sidebar = page.get_by_test_id("app-sidebar")
    expect(sidebar).to_have_attribute("aria-label", "Mimir in-app navigation")
    groups = sidebar.get_by_role("list")
    expect(groups).to_have_count(len(_SECTIONS))
    for index, (label, links) in enumerate(_SECTIONS):
        group = groups.nth(index)
        expect(group).to_have_accessible_name(label)
        _assert_links(group, links)
    expect(sidebar.locator(".mm-sidebar-section-label")).to_have_text(
        [label for label, _ in _SECTIONS]
    )
    _assert_current(sidebar, current)
    _assert_current(page.get_by_test_id("realm-nav-list"), "realm-nav-mimir")
    _assert_bounds(page, sidebar.get_by_test_id("nav-experts"))


def _assert_links(group: Locator, expected: tuple[tuple[str, str, str], ...]) -> None:
    """Compare actual ordered anchors and decorative icons with the shell oracle.

    :param group: Real labelled navigation list. Example: Collaborate.
    :param expected: Exact ordered destinations. Example: Teams, Experts, PIPs.
    :return: None when every original anchor is preserved.
    :raises AssertionError: If a name, destination, selector or decoration differs.
    """
    links = group.get_by_role("link")
    expect(links).to_have_count(len(expected))
    for index, (label, href, hook) in enumerate(expected):
        link = links.nth(index)
        expect(link).to_have_accessible_name(label)
        expect(link).to_have_attribute("href", href)
        expect(link).to_have_attribute("data-testid", hook)
        assert link.get_attribute("title")
        expect(link.locator("i")).to_have_count(1)
        expect(link.locator("i")).to_have_attribute("aria-hidden", "true")


def _assert_current(region: Locator, hook: str) -> None:
    """Require both current markers on exactly one link within this region.

    :param region: Existing navigation region. Example: app-sidebar.
    :param hook: Expected current anchor. Example: nav-experts.
    :return: None when active styling and aria-current identify the same link.
    :raises AssertionError: If extra, absent or mismatched current markers occur.
    """
    for selector in ('a[aria-current="page"]', "a.active"):
        current = region.locator(selector)
        expect(current).to_have_count(1)
        expect(current).to_have_attribute("data-testid", hook)


def _assert_destination(page: Page) -> None:
    """Check actual Development content and readable responsive page geometry.

    :param page: Browser after following the existing anchor. Example: /experts/.
    :return: None with the production leaderboard visible and default preserved.
    :raises AssertionError: If content, category, mockup boundary or geometry fails.
    """
    expect(page.get_by_role("heading", name="Experts", exact=True)).to_be_visible()
    expect(page.get_by_test_id("experts-leaderboard")).to_be_visible()
    _assert_current(
        page.get_by_test_id("experts-category-tabs"), "experts-category-development"
    )
    cards = page.get_by_test_id("experts-leaderboard").get_by_role("article")
    expect(cards).to_have_count(2)
    expect(cards.nth(0).get_by_role("heading", name="Mike Chen")).to_be_visible()
    expect(cards.nth(1).get_by_role("heading", name="Jordan Lee")).to_be_visible()
    assert "/mockups/" not in page.url
    _assert_bounds(page, page.get_by_role("heading", name="Experts", exact=True))
    assert page.evaluate(
        "document.documentElement.scrollWidth <= document.documentElement.clientWidth"
    ), "Unexpected page-level horizontal overflow"


def _assert_bounds(page: Page, element: Locator) -> None:
    """Require important content to fit horizontally in the actual viewport.

    :param page: Real browser page. Example: phone drawer.
    :param element: Essential visible content. Example: Experts navigation anchor.
    :return: None with positive readable bounds.
    :raises AssertionError: If content is clipped or has no rendered area.
    """
    expect(element).to_be_visible()
    bounds = element.bounding_box()
    assert bounds is not None and page.viewport_size is not None
    assert bounds["width"] > 0 and bounds["height"] > 0
    assert bounds["x"] >= 0
    assert bounds["x"] + bounds["width"] <= page.viewport_size["width"] + 1
    assert bounds["y"] >= 0
    assert bounds["y"] + bounds["height"] <= page.viewport_size["height"] + 1


def _protected_state() -> str:
    """Digest all account, ledger, profile, interaction and complete mail fields.

    :return: Private deterministic digest. Example: SHA256 of complete records.
    :raises TypeError: If a real persisted field cannot use the JSON adapter.
    """
    rows = [
        (model._meta.label, list(model.objects.order_by("pk").values_list()))
        for model in _PROTECTED_MODELS
    ]
    rows.append(("mail", [vars(message) for message in getattr(mail, "outbox", ())]))
    return hashlib.sha256(
        json.dumps(rows, default=str, sort_keys=True).encode()
    ).hexdigest()
