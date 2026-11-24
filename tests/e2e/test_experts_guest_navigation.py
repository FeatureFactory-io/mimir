"""Actual public sidebar navigation with fresh anonymous browser state."""

from __future__ import annotations

import hashlib
import json
from html import unescape
from http import HTTPStatus
from urllib.parse import urlsplit

import pytest
from django.apps import apps
from django.conf import settings
from django.contrib.auth.models import User
from django.core import mail
from django.db import connection
from django.urls import reverse
from playwright.sync_api import Locator, Page, Response, expect
from rest_framework.authtoken.models import Token

from tests.support.experts_data import CedarDataset
from tests.support.experts_guest_assertions import (
    assert_guest_auth_banner,
    assert_no_private_account_controls,
    assert_public_design_ranking,
)

_DESIGN = ("sreed", "mrodriguez", "pnair", "dortiz", "hkim")
_DEVELOPMENT = (("mchen", "12,450"), ("jlee", "6,100"))
_PRIVATE_HOOKS = (
    "user-display",
    "nav-view-profile",
    "logout-link",
    "notification-bell",
)


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("viewport", [(1280, 720), (390, 844)])
def test_guest_navigation_with_real_sidebar_click_preserves_public_access(
    page: Page,
    live_server_url: str,
    viewport: tuple[int, int],
    cedar_baseline: CedarDataset,
) -> None:
    """Click from the public shell to Experts with no account or domain mutation.

    :param page: Fresh real Page. Example: anonymous Chromium context.
    :param live_server_url: Real origin. Example: http://localhost:51000.
    :param viewport: CSS dimensions. Example: (390, 844).
    :param cedar_baseline: Real runner-owned Cedar data. Example: twelve users.
    :return: None. Example: public navigation and unchanged persisted state.
    :raises AssertionError: Redirect, ranking, privacy or read-only boundary fails.
    """
    assert cedar_baseline.users_by_username and not page.context.cookies()
    private_values = _private_values()
    page.set_viewport_size(dict(zip(("width", "height"), viewport, strict=True)))
    before, callbacks = _protected_state(), tuple(connection.run_on_commit)
    _navigate_from_home(page, live_server_url, viewport, private_values)
    _read_public_design(page, live_server_url, private_values)
    assert all(
        cookie["name"] != settings.SESSION_COOKIE_NAME
        for cookie in page.context.cookies()
    )
    assert not User.objects.filter(username__iexact="bob").exists()
    assert tuple(connection.run_on_commit) == callbacks
    unchanged = _protected_state() == before
    assert unchanged, "Guest navigation changed persisted state or mail."


def _navigate_from_home(
    page: Page, origin: str, viewport: tuple[int, int], private_values: tuple[str, ...]
) -> None:
    """Use the public shell and its actual responsive navigation.

    :param page: Real anonymous browser. Example: fresh Chromium page.
    :param origin: Real server origin. Example: http://localhost:51000.
    :param viewport: CSS dimensions. Example: (390, 844).
    :param private_values: Forbidden fixture values. Example: token strings.
    :return: None. Example: the default Experts page is visible.
    :raises AssertionError: Navigation, shell, default category or banner differs.
    """
    _assert_document(page, page.goto(f"{origin}/"), f"{origin}/", private_values)
    _open_sidebar(page, viewport)
    _assert_sidebar(page, current=False)
    _follow_link(
        page,
        page.get_by_test_id("nav-experts"),
        f"{origin}/experts/",
        private_values,
    )
    _open_sidebar(page, viewport)
    _assert_sidebar(page, current=True)
    _close_sidebar(page, viewport)
    _assert_development(page)
    _assert_banner(page)


def _read_public_design(
    page: Page, origin: str, private_values: tuple[str, ...]
) -> None:
    """Continue through Design and Maria's real public contribution profile.

    :param page: Actual anonymous Experts browser. Example: Development list.
    :param origin: Real server origin. Example: http://localhost:51000.
    :param private_values: Forbidden fixture values. Example: Cedar addresses.
    :return: None. Example: Maria's public profile remains contact-restricted.
    :raises AssertionError: Ranking, real profile link or public detail differs.
    """
    design = page.get_by_test_id("experts-category-design")
    _follow_link(page, design, f"{origin}/experts/?category=design", private_values)
    _assert_design(page)
    _follow_link(
        page,
        page.get_by_test_id("experts-view-profile-mrodriguez"),
        f"{origin}/experts/mrodriguez/",
        private_values,
    )
    expect(page.get_by_test_id("expert-name")).to_have_text("Maria Rodriguez")
    _assert_disabled_contact(page, "mrodriguez")


def _protected_state() -> str:
    """Digest every model/M2M row and every stored local message field.

    :return: Private deterministic digest. Example: a SHA256 hex string.
    :raises TypeError: A stored field cannot use the serialization adapter.
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


def _private_values() -> tuple[str, ...]:
    """Require actual private fixture values before checking public disclosure.

    :return: Synthetic secrets. Example: real token keys and Cedar emails.
    :raises AssertionError: Baseline lacks its private token or email sentinels.
    """
    tokens = tuple(Token.objects.values_list("key", flat=True))
    emails = tuple(User.objects.exclude(email="").values_list("email", flat=True))
    assert "DEMO_ONLY_NOT_A_REAL_TOKEN" in tokens and emails
    return (*tokens, *emails, "Cedar Bid Pricing", "Internal staffing notes for Cedar")


def _assert_document(
    page: Page, response: Response | None, url: str, private_values: tuple[str, ...]
) -> None:
    """Check actual response and hydrated DOM for redirects and private content.

    :param page: Actual anonymous browser. Example: the public home page.
    :param response: Observed document response. Example: status200.
    :param url: Exact destination. Example: http://localhost:51000/experts/.
    :param private_values: Forbidden real fixture values. Example: token strings.
    :return: None. Example: unchanged public access.
    :raises AssertionError: A redirect, error or private disclosure occurs.
    """
    assert response is not None and response.status == HTTPStatus.OK
    assert response.request.redirected_from is None
    expect(page).to_have_url(url)
    for html in (response.text(), page.content()):
        assert_no_private_account_controls(html)
        surface = unescape(html).casefold()
        assert "mailto:" not in surface
        assert not any(value.casefold() in surface for value in private_values)
    for hook in _PRIVATE_HOOKS:
        expect(page.get_by_test_id(hook)).to_have_count(0)
    expect(page.locator('[id="navbar-user-menu"]')).to_have_count(0)
    assert page.evaluate(
        "document.documentElement.scrollWidth <= document.documentElement.clientWidth"
    )


def _follow_link(
    page: Page, link: Locator, destination: str, private_values: tuple[str, ...]
) -> None:
    """Follow an actual rendered href using native pointer input.

    :param page: Real public browser. Example: Experts directory.
    :param link: Existing real anchor. Example: nav-experts.
    :param destination: Exact absolute URL. Example: http://localhost:51000/experts/.
    :param private_values: Forbidden fixture values. Example: private token.
    :return: None. Example: HTTP200 without login redirection.
    :raises AssertionError: The real anchor or navigation differs.
    """
    expect(link).to_have_attribute(
        "href",
        destination.removeprefix(
            f"{urlsplit(page.url).scheme}://{urlsplit(page.url).netloc}"
        ),
    )
    with page.expect_navigation(wait_until="domcontentloaded") as navigation:
        link.click()
    _assert_document(page, navigation.value, destination, private_values)


def _open_sidebar(page: Page, viewport: tuple[int, int]) -> None:
    """Open the existing guest offcanvas drawer when the viewport requires it.

    :param page: Actual public browser. Example: phone home page.
    :param viewport: CSS dimensions. Example: (390, 844).
    :return: None. Example: visible app sidebar.
    :raises AssertionError: Guest navigation cannot be reached.
    """
    sidebar = page.get_by_test_id("app-sidebar")
    expect(sidebar).to_have_count(1)
    if viewport[0] < 992:
        expect(sidebar).not_to_be_visible()
        page.get_by_test_id("sidebar-toggler").click()
    expect(sidebar).to_be_visible()


def _close_sidebar(page: Page, viewport: tuple[int, int]) -> None:
    """Dismiss the actual phone drawer before reading the destination.

    :param page: Real browser with open drawer. Example: phone Experts.
    :param viewport: CSS dimensions. Example: (390, 844).
    :return: None. Example: destination content is unobscured.
    :raises AssertionError: Phone drawer does not close.
    """
    if viewport[0] < 992:
        sidebar = page.get_by_test_id("app-sidebar")
        sidebar.get_by_role("button", name="Close").click()
        expect(sidebar).not_to_be_visible()


def _assert_sidebar(page: Page, current: bool) -> None:
    """Verify real Collaborate order, destination and current semantics.

    :param page: Browser with real visible drawer. Example: public home.
    :param current: Whether Experts is current. Example: True after navigation.
    :return: None. Example: existing guest sidebar retained.
    :raises AssertionError: Group, anchor or current markers differ.
    """
    sidebar = page.get_by_test_id("app-sidebar")
    group = sidebar.get_by_role("list", name="Collaborate", exact=True)
    expect(group.get_by_role("link")).to_have_text(["Teams", "Experts", "PIPs"])
    expert = group.get_by_test_id("nav-experts")
    expect(expert).to_have_attribute("href", "/experts/")
    expect(expert).to_be_visible()
    if current:
        for selector in ('a[aria-current="page"]', "a.active"):
            expect(sidebar.locator(selector)).to_have_count(1)
            expect(sidebar.locator(selector)).to_have_attribute(
                "data-testid", "nav-experts"
            )
    else:
        expect(expert).not_to_have_attribute("aria-current", "page")


def _assert_development(page: Page) -> None:
    """Require the actual default category and its two independent ranked users.

    :param page: Real Experts landing page. Example: /experts/ without query.
    :return: None. Example: Mike12450 then Jordan6100 remain default.
    :raises AssertionError: Default category or live score/rank is wrong.
    """
    expect(page.get_by_test_id("experts-category-development")).to_have_attribute(
        "aria-current", "page"
    )
    cards = page.get_by_test_id("experts-leaderboard").get_by_role("article")
    expect(cards).to_have_count(len(_DEVELOPMENT))
    for index, (username, score) in enumerate(_DEVELOPMENT):
        expect(cards.nth(index)).to_have_attribute(
            "data-testid", f"experts-card-{username}"
        )
        expect(cards.nth(index).get_by_test_id("expert-card-karma")).to_have_text(score)
        _assert_disabled_contact(page, username)


def _assert_banner(page: Page) -> None:
    """Require the visible guest explanation and reachable authentication anchors.

    :param page: Actual anonymous Experts page. Example: Development directory.
    :return: None. Example: Sign In and Register remain available.
    :raises AssertionError: Guest explanation or either real action differs.
    """
    assert_guest_auth_banner(page.content())
    banner = page.get_by_test_id("guest-auth-banner")
    expect(banner).to_be_visible()
    expect(banner).to_contain_text("Sign in to reach out to a contributor.")
    for hook, route in (
        ("experts-guest-login", "login"),
        ("experts-guest-register", "register"),
    ):
        action = banner.get_by_test_id(hook)
        expect(action).to_be_visible()
        expect(action).to_have_attribute("href", reverse(route))
        expect(action).to_be_enabled()


def _assert_design(page: Page) -> None:
    """Check exact five-person public Design ranking and disabled contact actions.

    :param page: Real Design directory. Example: category=design.
    :return: None. Example: Sofia15400 followed by Maria8200.
    :raises AssertionError: Actual ranking, contact or category differs.
    """
    assert_public_design_ranking(page.content())
    expect(page.get_by_test_id("experts-category-design")).to_have_attribute(
        "aria-current", "page"
    )
    for username in _DESIGN:
        card = page.get_by_test_id(f"experts-card-{username}")
        expect(card.get_by_test_id("expert-card-name")).to_be_visible()
        expect(card.get_by_test_id("expert-card-karma")).to_be_visible()
        _assert_disabled_contact(page, username)


def _assert_disabled_contact(page: Page, username: str) -> None:
    """Require the existing disabled guest contact without any email destination.

    :param page: Real public browser. Example: Maria's public detail.
    :param username: Actual Cedar contributor. Example: mrodriguez.
    :return: None. Example: one disabled button and no contact anchor.
    :raises AssertionError: Contact is enabled or an email link is exposed.
    """
    button = page.get_by_test_id(f"experts-reach-out-disabled-{username}")
    expect(button).to_have_count(1)
    expect(button).to_be_disabled()
    expect(page.get_by_test_id(f"experts-reach-out-{username}")).to_have_count(0)
