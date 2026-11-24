"""Certify the public Experts ranking with real mouse and keyboard input."""

from __future__ import annotations

import re
from html import unescape
from http import HTTPStatus

import pytest
from django.conf import settings
from django.contrib.auth.models import User
from django.core.mail import EmailMessage
from django.urls import reverse
from e2e_helpers import login
from playwright.sync_api import Locator, Page, Request, Response, expect
from rest_framework.authtoken.models import Token

from methodology.models import KarmaAward
from tests.support.experts_data import CEDAR_PASSWORD, CedarDataset
from tests.support.experts_guest_assertions import (
    assert_guest_auth_banner,
    assert_no_private_account_controls,
)

_DESIGN = (
    ("sreed", "Sofia Reed", "15,400"),
    ("mrodriguez", "Maria Rodriguez", "8,200"),
    ("pnair", "Priya Nair", "7,600"),
    ("dortiz", "Daniel Ortiz", "6,900"),
    ("hkim", "Hana Kim", "5,800"),
)
_DEVELOPMENT = (
    ("mchen", "Mike Chen", "12,450"),
    ("jlee", "Jordan Lee", "6,100"),
)
_EXPLANATION = "You need to be logged in to reach out to the expert"
_EVIDENCE_TITLE = "Accessibility Audit Playbook"
_EVIDENCE_PK = 6101
_MAX_TAB_PRESSES = 40
_GUEST_DOCUMENT_COUNT = 5

Ranking = tuple[tuple[str, str, str], ...]
DatabaseState = tuple[tuple[tuple[object, ...], ...], ...]


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
def test_experts_list_with_guest_browser_shows_public_cards_and_auth_actions(
    page: Page,
    live_server_url: str,
    cedar_dataset: CedarDataset,
    mailoutbox: list[EmailMessage],
) -> None:
    """Certify the anonymous Cedar directory and Maria's public evidence.

    :param page: Fresh Chromium page. Example: no account cookie.
    :param live_server_url: Function-scoped Django origin.
    :param cedar_dataset: Real fixture with synthetic contributors and private data.
    :param mailoutbox: Test runner's local mail outbox.
    :return: None once a guest can read evidence with no contact or account write.
    :raises AssertionError: If rankings, privacy, interaction or persisted state differ.
    """
    directory_url = f"{live_server_url}{reverse('experts_list')}"
    design_url = f"{directory_url}?category=design"
    elena_ranking = _read_elena_ranking(page, live_server_url, design_url)
    state_before = _database_state()
    private_values = _private_values()

    assert not page.context.cookies()
    requests: list[str] = []
    page.on("request", lambda request: _record_guest_request(request, requests))
    _open_guest_page(page, directory_url, private_values)
    _assert_guest_ranking(page, "development", _DEVELOPMENT)
    _open_guest_page(page, design_url, private_values)
    assert _assert_guest_ranking(page, "design", _DESIGN) == elena_ranking
    _assert_auth_actions(page)

    _assert_hover_explanation(page)
    design_tab = page.get_by_test_id("experts-category-design")
    _follow_guest_link(page, design_tab, design_url, private_values)
    _assert_keyboard_explanation(page)
    _follow_public_evidence(page, live_server_url, cedar_dataset, private_values)

    assert all(
        cookie["name"] != settings.SESSION_COOKIE_NAME
        for cookie in page.context.cookies()
    )
    assert requests == ["GET"] * _GUEST_DOCUMENT_COUNT
    assert not mailoutbox
    state_unchanged = _database_state() == state_before
    assert state_unchanged, "The rankings journey changed an account, token or award"


def _database_state() -> DatabaseState:
    """Snapshot account, token and ledger rows, including their values.

    :return: Three row tuples, ordered by primary key. Example: one per model.
    """
    return (
        tuple(User.objects.order_by("pk").values_list()),
        tuple(Token.objects.order_by("pk").values_list()),
        tuple(KarmaAward.objects.order_by("pk").values_list()),
    )


def _private_values() -> tuple[str, ...]:
    """Collect actual synthetic values the guest must never receive.

    :return: Private strings from the baseline and actual test token keys.
    :raises AssertionError: If the token sentinel was missing from the fixture.
    """
    token_keys = tuple(Token.objects.values_list("key", flat=True))
    assert "DEMO_ONLY_NOT_A_REAL_TOKEN" in token_keys
    emails = tuple(User.objects.exclude(email="").values_list("email", flat=True))
    assert emails
    return (
        *emails,
        *token_keys,
        "Cedar Bid Pricing",
        "Internal staffing notes for Cedar",
    )


def _read_elena_ranking(page: Page, origin: str, design_url: str) -> Ranking:
    """Read Elena's real rendered ranking in its own authenticated context.

    :param page: Guest page whose browser launches the comparison context.
    :param origin: Actual server origin. Example: http://localhost:51000.
    :param design_url: Absolute Design list URL.
    :return: Elena's visible usernames, names and points in ranked order.
    :raises AssertionError: If login or the independent ranking oracle fails.
    """
    browser = page.context.browser
    assert browser is not None
    with browser.new_context(ignore_https_errors=True) as elena_context:
        elena = elena_context.new_page()
        login(elena, origin, "esvensson", CEDAR_PASSWORD)
        response = elena.goto(design_url)
        assert response is not None and response.status == HTTPStatus.OK
        expect(elena.get_by_test_id("nav-view-profile")).to_have_count(1)
        return _read_ranking(elena, _DESIGN)


def _record_guest_request(request: Request, methods: list[str]) -> None:
    """Count navigation and write attempts without keeping request data.

    :param request: Actual Chromium request. Example: navigation GET.
    :param methods: Methods of navigation requests and attempted writes.
    """
    if request.is_navigation_request() or request.method not in {
        "GET",
        "HEAD",
        "OPTIONS",
    }:
        methods.append(request.method)


def _open_guest_page(page: Page, url: str, private_values: tuple[str, ...]) -> None:
    """Open a real anonymous document and check both rendered surfaces.

    :param page: Anonymous Chromium page.
    :param url: Absolute production URL served by the e2e runner.
    :param private_values: Synthetic sensitive values to exclude.
    :raises AssertionError: If access redirects, fails or carries private data.
    """
    response = page.goto(url)
    assert response is not None
    _assert_guest_document(page, response, url, private_values)


def _assert_guest_document(
    page: Page, response: Response, url: str, private_values: tuple[str, ...]
) -> None:
    """Inspect the raw response and hydrated DOM for private data.

    :param page: Anonymous Chromium page.
    :param response: Observed document response.
    :param url: Expected absolute public destination.
    :param private_values: Synthetic private addresses, token keys and titles.
    :raises AssertionError: If a redirect, HTTP failure or disclosure occurs.
    """
    assert response.status == HTTPStatus.OK and response.request.redirected_from is None
    expect(page).to_have_url(url)
    for html in (response.text(), page.content()):
        assert_no_private_account_controls(html)
        surface = unescape(html).casefold()
        assert "mailto:" not in surface, "A guest document exposed a contact URL"
        leaked = any(value.casefold() in surface for value in private_values)
        assert not leaked, "A guest document exposed private Cedar data"


def _assert_guest_ranking(page: Page, category: str, expected: Ranking) -> Ranking:
    """Verify category selection, rendered rank, and each guest card's actions.

    :param page: Anonymous directory page.
    :param category: Expected active category slug. Example: design.
    :param expected: Independent Cedar ranking oracle for that category.
    :return: Visible ordered usernames, names and totals.
    :raises AssertionError: If the category, ranking or either action differs.
    """
    tabs = page.get_by_test_id("experts-category-tabs")
    expect(tabs.locator('[aria-current="page"]')).to_have_count(1)
    expect(tabs.get_by_test_id(f"experts-category-{category}")).to_have_attribute(
        "aria-current", "page"
    )
    ranking = _read_ranking(page, expected)
    for username, name, _ in expected:
        card = page.get_by_test_id(f"experts-card-{username}")
        expect(card.get_by_test_id("expert-card-category")).to_have_text(
            category.title()
        )
        profile = card.get_by_test_id(f"experts-view-profile-{username}")
        expect(profile).to_have_role("link")
        expect(profile).to_have_accessible_name("View profile")
        expect(profile).to_have_attribute(
            "href", reverse("expert_detail", args=[username])
        )
        expect(profile).to_be_visible()
        _assert_disabled_contact(card, username, name)
    return ranking


def _read_ranking(page: Page, expected: Ranking) -> Ranking:
    """Read actual contributor articles and visible scores in DOM order.

    :param page: Real Experts directory page for either session.
    :param expected: Independent username, display name and Karma oracle.
    :return: Actual ordered username, display name and Karma tuples.
    :raises AssertionError: If the number, identity, order or score differs.
    """
    cards = page.get_by_test_id("experts-leaderboard").get_by_role("article")
    expect(cards).to_have_count(len(expected))
    ranking = []
    for rank, (username, name, points) in enumerate(expected, start=1):
        card = cards.nth(rank - 1)
        expect(card).to_have_attribute("data-testid", f"experts-card-{username}")
        rank_label = card.get_by_test_id("expert-card-rank")
        expect(rank_label).to_have_text(str(rank))
        heading = card.get_by_role("heading", name=name, exact=True)
        expect(heading).to_be_visible()
        karma = card.get_by_test_id("expert-card-karma")
        expect(karma).to_have_text(points)
        expect(karma).to_be_visible()
        hook = card.get_attribute("data-testid")
        assert hook is not None
        ranking.append(
            (
                hook.removeprefix("experts-card-"),
                heading.inner_text(),
                karma.inner_text(),
            )
        )
    return tuple(ranking)


def _assert_auth_actions(page: Page) -> None:
    """Verify both authentication anchors and reach them in native Tab order.

    :param page: Fresh anonymous Design document.
    :raises AssertionError: If either link is hidden, misrouted or out of tab order.
    """
    assert_guest_auth_banner(page.content())
    banner = page.get_by_test_id("guest-auth-banner")
    expect(banner).to_be_visible()
    for route, name in (("login", "Sign In"), ("register", "Register")):
        anchor = banner.get_by_test_id(f"experts-guest-{route}")
        expect(anchor).to_have_role("link")
        expect(anchor).to_have_accessible_name(name)
        expect(anchor).to_be_visible()
        _tab_to(page, anchor)


def _tab_to(page: Page, target: Locator) -> None:
    """Reach a target using the browser's real sequential focus navigation.

    :param page: Chromium page receiving keyboard input.
    :param target: Expected tabbable DOM node.
    :raises AssertionError: If repeated Tab presses cannot reach the target.
    """
    for _ in range(_MAX_TAB_PRESSES):
        page.keyboard.press("Tab")
        if target.evaluate("(control) => control === document.activeElement"):
            return
    expect(target).to_be_focused(timeout=500)


def _assert_disabled_contact(scope: Locator, username: str, name: str) -> Locator:
    """Verify an inactive button and an accessible explanation on its wrapper.

    :param scope: Card or detail toolbar containing one guest contact control.
    :param username: Public contributor username. Example: mrodriguez.
    :param name: Contributor display name. Example: Maria Rodriguez.
    :return: Guest wrapper ready for real hover or keyboard focus.
    :raises AssertionError: If the button is actionable or its help is unavailable.
    """
    wrapper = scope.get_by_test_id("experts-reach-out-guest-tooltip")
    expect(wrapper).to_be_visible()
    expect(wrapper).to_have_attribute("tabindex", "0")
    expect(wrapper).to_have_accessible_description(_EXPLANATION)
    expect(wrapper.locator("a, form")).to_have_count(0)
    button = wrapper.get_by_test_id(f"experts-reach-out-disabled-{username}")
    expect(button).to_have_role("button")
    expect(button).to_have_js_property("tagName", "BUTTON")
    expect(button).to_have_js_property("disabled", True)
    expect(button).to_have_accessible_name(f"Reach out to {name}")
    expect(button).to_be_visible()
    expect(button).to_be_disabled()
    return wrapper


def _assert_hover_explanation(page: Page) -> None:
    """Use actual pointer hover and click on Maria's inactive contact control.

    :param page: Anonymous Design page with keyboard focus on a banner link.
    :raises AssertionError: If hover help is incorrect or activation navigates.
    """
    card = page.get_by_test_id("experts-card-mrodriguez")
    wrapper = card.get_by_test_id("experts-reach-out-guest-tooltip")
    expect(wrapper).not_to_be_focused()
    wrapper.hover()
    _assert_visible_explanation(page, wrapper)
    url = page.url
    pages = page.context.pages
    wrapper.click()
    expect(page).to_have_url(url)
    assert page.context.pages == pages


def _assert_keyboard_explanation(page: Page) -> None:
    """Navigate from a newly loaded page to Maria's explanation using Tab.

    :param page: Anonymous Design page free of prior contact focus.
    :raises AssertionError: If focus cannot reveal help or activation navigates.
    """
    card = page.get_by_test_id("experts-card-mrodriguez")
    wrapper = card.get_by_test_id("experts-reach-out-guest-tooltip")
    expect(wrapper).to_have_attribute(
        "aria-describedby", "reach-explanation-mrodriguez"
    )
    _tab_to(page, wrapper)
    _assert_visible_explanation(page, wrapper)
    url = page.url
    pages = page.context.pages
    page.keyboard.press("Enter")
    page.keyboard.press("Space")
    expect(page).to_have_url(url)
    assert page.context.pages == pages
    _assert_visible_explanation(page, wrapper)


def _assert_visible_explanation(page: Page, wrapper: Locator) -> None:
    """Check the tooltip associated with this trigger is visibly rendered.

    :param page: Real page where Bootstrap displays the tooltip.
    :param wrapper: Hovered or keyboard-focused guest contact wrapper.
    :raises AssertionError: If the actual tooltip is absent or its text differs.
    """
    expect(wrapper).to_have_attribute("aria-describedby", re.compile(r"^tooltip"))
    tooltip_id = wrapper.get_attribute("aria-describedby")
    tooltip = page.get_by_role("tooltip").and_(page.locator(f'[id="{tooltip_id}"]'))
    expect(tooltip).to_be_visible()
    expect(tooltip).to_be_in_viewport()
    expect(tooltip).to_have_text(_EXPLANATION)


def _follow_public_evidence(
    page: Page, origin: str, dataset: CedarDataset, private_values: tuple[str, ...]
) -> None:
    """Follow Maria's profile and its Cedar evidence as the same guest.

    :param page: Anonymous Design page showing the real contact explanation.
    :param origin: Live Django origin. Example: http://localhost:51000.
    :param dataset: Real Cedar data for the independent stored-summary oracle.
    :param private_values: Synthetic data forbidden from public documents.
    :raises AssertionError: If either real pointer click, content or privacy fails.
    """
    path = reverse("expert_detail", args=["mrodriguez"])
    profile = page.get_by_test_id("experts-view-profile-mrodriguez")
    _follow_guest_link(page, profile, f"{origin}{path}", private_values)
    expect(page.get_by_test_id("expert-name")).to_have_text("Maria Rodriguez")
    summary = next(
        row["summary"]
        for row in dataset.oracle["people"]
        if row["username"] == "mrodriguez"
    )
    assert summary
    body = page.get_by_test_id("expert-contribution-summary")
    expect(body).to_be_visible()
    expect(body).to_have_text(summary)
    contact = page.get_by_role("toolbar", name="Expert contact")
    _assert_disabled_contact(contact, "mrodriguez", "Maria Rodriguez")
    evidence = page.get_by_test_id("expert-public-playbooks")
    expect(evidence.get_by_role("heading", name=_EVIDENCE_TITLE)).to_be_visible()
    view = evidence.get_by_test_id(f"expert-playbook-{_EVIDENCE_PK}")
    expect(view).to_have_accessible_name(f"View {_EVIDENCE_TITLE}")
    playbook = reverse("playbook_detail", args=[_EVIDENCE_PK])
    _follow_guest_link(page, view, f"{origin}{playbook}", private_values)
    detail = page.get_by_test_id("playbook-detail")
    expect(detail.get_by_role("heading", name=_EVIDENCE_TITLE, level=1)).to_be_visible()
    expect(detail.get_by_test_id("status-badge")).to_have_text("Released")


def _follow_guest_link(
    page: Page, link: Locator, destination: str, private_values: tuple[str, ...]
) -> None:
    """Observe actual document navigation caused by a guest's pointer click.

    :param page: Anonymous Chromium page.
    :param link: Guest-visible navigation anchor.
    :param destination: Expected absolute public document URL.
    :param private_values: Synthetic private values forbidden on the destination.
    :raises AssertionError: If the click does not reach the public document.
    """
    with page.expect_response(
        lambda response: response.url == destination
        and response.request.is_navigation_request()
    ) as navigation:
        link.click()
    _assert_guest_document(page, navigation.value, destination, private_values)
