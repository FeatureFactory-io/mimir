"""Certify guest list contact with actual pointer and keyboard input."""

from __future__ import annotations

from collections.abc import Iterator
from html import unescape
from http import HTTPStatus
from typing import Literal
from urllib.parse import unquote

import pytest
from django.conf import settings
from django.core.mail import EmailMessage
from django.urls import reverse
from playwright.sync_api import Locator, Page, expect
from rest_framework.authtoken.models import Token

from methodology.models import AgentInteraction, ExpertProfile, KarmaAward
from tests.support.experts_data import CedarDataset, load_cedar_baseline
from tests.support.experts_guest_assertions import (
    assert_guest_auth_banner,
    assert_no_private_account_controls,
)
from tests.support.experts_guest_browser import (
    activate_guest_tooltip,
    assert_guest_tooltip_in_viewport,
    guest_contact_wrapper,
    tab_to_guest_control,
)
from tests.support.experts_guest_contact import GUEST_CONTACT_EXPLANATION

_MARIA = "mrodriguez"
_AFTER_MARIA = "pnair"
_DESIGN_CARD_COUNT = 5
_ACTION_TIMEOUT_MS = 2500
_CATEGORY_LABELS = ("Product", "Development", "Research", "Design", "Other")
_ExpertState = tuple[tuple[dict[str, object], ...], ...]


@pytest.fixture
def cedar_guest_browser_dataset(transactional_db: None) -> CedarDataset:
    """Load Cedar into the real browser-test database before page interaction.

    :param transactional_db: Function-isolated database access. Example: live-server-visible committed rows.
    :return: CedarDataset from the shared baseline loader; example: real Maria and Elena users.
    :raises ValueError: If the baseline data is invalid.
    """
    return load_cedar_baseline()


@pytest.fixture
def browser_read_only_expert_state(
    cedar_guest_browser_dataset: CedarDataset, mailoutbox: list[EmailMessage]
) -> Iterator[None]:
    """Check all persisted rows and test mail before and after the browser journey.

    :param cedar_guest_browser_dataset: Existing isolated Cedar baseline.
    :param mailoutbox: Real local mail outbox. Example: [].
    :return: Iterator spanning the live browser request and user input.
    :raises AssertionError: If the journey modifies Experts state or produces email.
    """
    before = _expert_state()
    assert before[0] and before[1], "Expected populated Cedar ledger and profiles"
    assert not mailoutbox
    yield
    assert not mailoutbox, "The guest interaction sent mail"
    if _expert_state() != before:
        pytest.fail("The guest interaction changed ledger, profile or model state")


@pytest.mark.e2e
@pytest.mark.parametrize(
    "viewport",
    [
        (1280, 800),
        (1920, 1080),
        (1512, 982),
        (768, 1024),
        (1024, 768),
        (390, 844),
        (360, 800),
    ],
)
@pytest.mark.parametrize("activation", ["hover", "keyboard"])
def test_experts_reach_02_with_guest_activation_explains_restriction(
    cedar_guest_browser_dataset: CedarDataset,
    page: Page,
    live_server_url: str,
    viewport: tuple[int, int],
    activation: Literal["hover", "keyboard"],
    browser_read_only_expert_state: None,
) -> None:
    """Certify full EXPERTS-REACH-02 on production UI for one viewport and activation.

    :param cedar_guest_browser_dataset: Real fixture. Example: Maria appears on Design list.
    :param page: Existing fresh anonymous page fixture. Example: empty cookies/storage.
    :param live_server_url: Function-scoped server origin. Example: http://localhost:49152.
    :param viewport: Required IA dimensions. Example: (390, 844).
    :param activation: Actual tooltip interaction. Example: "hover".
    :param browser_read_only_expert_state: Ledger, profiles, model and mail guard.
    :return: None when route, disabled contact, email privacy, actual explanation, focus/geometry and profile availability all pass.
    :raises AssertionError: If any exact acceptance assertion fails; never click a mailto or send email.
    """
    width, height = viewport
    page.set_viewport_size({"width": width, "height": height})
    design_url = f"{live_server_url}/experts/?category=design"
    _open_guest_design(page, design_url, cedar_guest_browser_dataset)
    _assert_guest_auth_actions(page, activation)
    _assert_category_layout(page)
    usernames = tuple(cedar_guest_browser_dataset.oracle["expected_design_order"])
    _assert_design_cards(page, usernames)

    wrapper = guest_contact_wrapper(page, f"experts-card-{_MARIA}")
    if activation == "keyboard":
        tab_to_guest_control(
            page, page.get_by_test_id(f"experts-view-profile-{_MARIA}")
        )
    tooltip = activate_guest_tooltip(page, wrapper, activation)
    assert_guest_tooltip_in_viewport(page, tooltip, viewport)
    _dismiss_tooltip(page, wrapper, tooltip, activation)
    _assert_actions_reachable(page, usernames)
    expect(page).to_have_url(design_url)
    assert all(
        cookie["name"] != settings.SESSION_COOKIE_NAME
        for cookie in page.context.cookies()
    )
    _assert_guest_privacy(page.content(), cedar_guest_browser_dataset)


def _expert_state() -> _ExpertState:
    """Collect complete persisted records, including their values.

    :return: Stable snapshots of the Experts ledger, profiles and model interactions.
    :raises DatabaseError: If the test database cannot supply the records.
    """
    return tuple(
        tuple(model.objects.order_by("pk").values())
        for model in (KarmaAward, ExpertProfile, AgentInteraction)
    )


def _open_guest_design(page: Page, url: str, dataset: CedarDataset) -> None:
    """Open the public Design list in the fresh anonymous production-route context.

    :param page: Fresh real Chromium page. Example: empty session cookies.
    :param url: Expected route and selected category. Example: /experts/?category=design.
    :param dataset: Real Cedar fixture with private data sentinels.
    :return: None once the page succeeds directly and styles settle.
    :raises AssertionError: For a redirect, signed-in session or data disclosure.
    """
    assert not page.context.cookies(), "The guest context must start without cookies"
    response = page.goto(url)
    assert response is not None and response.status == HTTPStatus.OK
    assert response.request.redirected_from is None
    expect(page).to_have_url(url)
    expect(page.get_by_role("heading", name="Experts", exact=True)).to_be_visible()
    page.evaluate("() => document.fonts.ready")
    for document in (response.text(), page.content()):
        _assert_guest_privacy(document, dataset)
        assert_no_private_account_controls(document)


def _assert_guest_privacy(document: str, dataset: CedarDataset) -> None:
    """Check actual HTML or browser DOM without reporting private sentinels.

    :param document: Actual guest content. Example: DOM after tooltip dismissal.
    :param dataset: Source of private Cedar addresses and real account identities.
    :return: None once private addresses, credentials and mail destinations are absent.
    :raises AssertionError: If a sentinel is missing or the guest receives it.
    """
    emails = tuple(
        user.email for user in dataset.users_by_username.values() if user.email
    )
    tokens = tuple(Token.objects.values_list("key", flat=True))
    assert emails and tokens, "Expected private Cedar email and token sentinels"
    surface = unquote(unescape(document)).casefold()
    if "mailto:" in surface or any(
        secret.casefold() in surface for secret in (*emails, *tokens)
    ):
        pytest.fail(
            "The guest document displayed a private account value or mail destination"
        )


def _assert_guest_auth_actions(
    page: Page, activation: Literal["hover", "keyboard"]
) -> None:
    """Verify the visible guest banner and both usable authentication links.

    :param page: Anonymous production Design list.
    :param activation: Input mode. Example: keyboard starts at the beginning of the document.
    :return: None once both named links are reachable without activation.
    :raises AssertionError: If a link is absent, obstructed or takes the wrong route.
    """
    assert_guest_auth_banner(page.content())
    banner = page.get_by_test_id("guest-auth-banner")
    expect(banner).to_be_visible()
    for route, name in (("login", "Sign In"), ("register", "Register")):
        link = banner.get_by_test_id(f"experts-guest-{route}")
        expect(link).to_have_role("link")
        expect(link).to_have_accessible_name(name)
        expect(link).to_have_attribute("href", reverse(route))
        if activation == "keyboard":
            tab_to_guest_control(page, link)
        else:
            link.click(trial=True, timeout=_ACTION_TIMEOUT_MS)


def _assert_category_layout(page: Page) -> None:
    """Check all category labels and horizontal bounds under the current viewport.

    :param page: Public Design list at one IA viewport. Example: 360×800.
    :return: None once category links wrap within the tabs and the page fits.
    :raises AssertionError: If navigation is clipped, lost or incorrectly selected.
    """
    tabs = page.get_by_test_id("experts-category-tabs")
    expect(tabs.get_by_role("link")).to_have_text(list(_CATEGORY_LABELS))
    expect(tabs.locator('[aria-current="page"]')).to_have_text("Design")
    assert tabs.evaluate("""tabs => {
            const bounds = tabs.getBoundingClientRect();
            return Array.from(tabs.querySelectorAll('a')).every(link => {
                const rect = link.getBoundingClientRect();
                return rect.width > 0 && rect.left >= bounds.left && rect.right <= bounds.right;
            });
        }"""), "A category link is clipped beyond the wrapped navigation"
    assert page.evaluate(
        "document.documentElement.scrollWidth === document.documentElement.clientWidth"
    )


def _assert_guest_card(page: Page, username: str) -> None:
    """Check a named profile anchor and the corresponding native disabled action.

    :param page: Actual anonymous Design list.
    :param username: Expected expert account. Example: "mrodriguez".
    :return: None when both initial browser actions meet the guest contract.
    :raises AssertionError: If the card offers contact or no usable profile action.
    """
    card = page.get_by_test_id(f"experts-card-{username}")
    profile = card.get_by_test_id(f"experts-view-profile-{username}")
    expect(profile).to_have_role("link")
    expect(profile).to_have_accessible_name("View profile")
    expect(profile).to_have_attribute("href", f"/experts/{username}/")
    expect(profile).to_have_js_property("tabIndex", 0)
    expect(profile).to_be_visible()
    expect(profile).to_be_enabled()
    expect(card.get_by_role("link")).to_have_count(1)
    wrapper = guest_contact_wrapper(page, f"experts-card-{username}")
    expect(wrapper).to_have_attribute(
        "aria-describedby", f"reach-explanation-{username}"
    )
    expect(wrapper).to_have_accessible_description(GUEST_CONTACT_EXPLANATION)
    expect(wrapper.locator("a, form")).to_have_count(0)
    button = wrapper.get_by_test_id(f"experts-reach-out-disabled-{username}")
    expect(button).to_have_js_property("tagName", "BUTTON")
    expect(button).to_have_js_property("disabled", True)
    expect(button).to_have_text("Reach out")
    expect(button).to_be_disabled()
    expect(button).to_be_visible()


def _assert_design_cards(page: Page, usernames: tuple[str, ...]) -> None:
    """Check the five independently expected cards in their displayed order.

    :param page: Actual anonymous Design list.
    :param usernames: Ordered Cedar oracle. Example: Sofia then Maria.
    :return: None once every card meets the guest contact contract.
    :raises AssertionError: If card order, identity or actions differ.
    """
    assert len(usernames) == _DESIGN_CARD_COUNT
    cards = page.get_by_test_id("experts-leaderboard").get_by_role("article")
    expect(cards).to_have_count(_DESIGN_CARD_COUNT)
    for position, username in enumerate(usernames):
        expect(cards.nth(position)).to_have_attribute(
            "data-testid", f"experts-card-{username}"
        )
        _assert_guest_card(page, username)
    maria_card = page.get_by_test_id(f"experts-card-{_MARIA}")
    expect(
        maria_card.get_by_role("heading", name="Maria Rodriguez", exact=True)
    ).to_be_visible()


def _dismiss_tooltip(
    page: Page,
    wrapper: Locator,
    tooltip: Locator,
    activation: Literal["hover", "keyboard"],
) -> None:
    """Dismiss the overlay with the same actual input that exposed it.

    :param page: Browser showing Maria's real explanation on Design.
    :param wrapper: Maria's trigger, focused in the keyboard case.
    :param tooltip: Active tooltip located by the wrapper's description ID.
    :param activation: Input mode. Example: actual Tab blurs Maria's trigger.
    :return: None once the tooltip disappears naturally.
    :raises AssertionError: If focus fails to advance or explanation gets stuck.
    """
    if activation == "keyboard":
        page.keyboard.press("Tab")
        expect(
            page.get_by_test_id(f"experts-view-profile-{_AFTER_MARIA}")
        ).to_be_focused()
    else:
        page.mouse.move(0, 0)
    expect(wrapper).not_to_be_focused()
    expect(tooltip).to_be_hidden(timeout=_ACTION_TIMEOUT_MS)
    expect(
        page.get_by_role("tooltip").filter(has_text=GUEST_CONTACT_EXPLANATION)
    ).to_have_count(0)


def _assert_actions_reachable(page: Page, usernames: tuple[str, ...]) -> None:
    """Reach each action cluster through ordinary document scrolling.

    :param page: Production Design list after the tooltip has closed.
    :param usernames: Ordered independent Cedar oracle for the five cards.
    :return: None after each profile link accepts pointer input and the disabled action is visible.
    :raises AssertionError: If an action is occluded or only an inner scroller reveals the list.
    """
    last_wrapper = guest_contact_wrapper(page, f"experts-card-{usernames[-1]}")
    below_initial_viewport = last_wrapper.evaluate(
        "element => element.getBoundingClientRect().bottom + scrollY > innerHeight"
    )
    for username in usernames:
        profile = page.get_by_test_id(f"experts-view-profile-{username}")
        profile.click(trial=True, timeout=_ACTION_TIMEOUT_MS)
        wrapper = guest_contact_wrapper(page, f"experts-card-{username}")
        wrapper.scroll_into_view_if_needed(timeout=_ACTION_TIMEOUT_MS)
        expect(wrapper).to_be_in_viewport(ratio=1)
        assert wrapper.evaluate("""element => {
                const box = element.getBoundingClientRect();
                return element.contains(document.elementFromPoint(
                    box.left + box.width / 2, box.top + box.height / 2
                ));
            }"""), f"The contact control is covered on the {username} card"
    if below_initial_viewport:
        assert page.evaluate("scrollY > 0"), (
            "The final card requires document scrolling"
        )
