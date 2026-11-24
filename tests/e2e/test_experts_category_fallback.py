from __future__ import annotations

from http import HTTPStatus

import pytest
from django.core.mail import EmailMessage
from playwright.sync_api import Locator, Page, Response, expect

from methodology.models import AgentInteraction, ExpertProfile, KarmaAward
from tests.support.experts_data import CedarDataset

pytestmark = [pytest.mark.e2e, pytest.mark.django_db(transaction=True)]

_CATEGORY_PATH = "/experts/?category="
_CATEGORIES = ("Product", "Development", "Research", "Design", "Other")
_DEVELOPMENT_RANKING = (
    ("mchen", "Mike Chen", "12,450"),
    ("jlee", "Jordan Lee", "6,100"),
)
_GUEST_EXPLANATION = "You need to be logged in to reach out to the expert"
_LAYOUT_TOLERANCE_PX = 1


@pytest.mark.parametrize(
    "viewport_size",
    (
        pytest.param((1280, 800), id="wide-low"),
        pytest.param((1920, 1080), id="large-desktop"),
        pytest.param((1512, 982), id="laptop"),
        pytest.param((768, 1024), id="tablet-portrait"),
        pytest.param((1024, 768), id="tablet-landscape"),
        pytest.param((390, 844), id="phone"),
        pytest.param((360, 800), id="minimum-phone"),
    ),
)
def test_experts_list_with_unknown_category_survives_browser_refresh(
    page: Page,
    live_server_url: str,
    cedar_dataset: CedarDataset,
    viewport_size: tuple[int, int],
    mailoutbox: list[EmailMessage],
) -> None:
    """Certify the production fallback through the existing fresh guest page.

    :param page: Existing fresh browser page. Example: Chromium Page.
    :param live_server_url: Actual Django server origin. Example: "http://localhost:8081".
    :param cedar_dataset: Shared function-scoped ORM baseline. Example: Elena and Mike.
    :param viewport_size: Section H viewport row. Example: (390, 844).
    :param mailoutbox: Local capture for any unexpected mail. Example: [].
    :return: None. Example: successful browser assertions return None.
    :raises AssertionError: If recovery, refresh, reachability, or read-only behavior fails.
    """
    width, height = viewport_size
    page.set_viewport_size({"width": width, "height": height})
    assert {"mchen", "jlee", "mrodriguez"}.issubset(cedar_dataset.users_by_username)
    observed_models = (KarmaAward, ExpertProfile, AgentInteraction)
    before = [list(model.objects.order_by("pk").values()) for model in observed_models]
    before_mail = tuple(mailoutbox)

    unknown_url = f"{live_server_url}{_CATEGORY_PATH}unrecognized"
    _assert_get(page, page.goto(unknown_url), unknown_url)
    _assert_development(page)
    _assert_get(page, page.reload(), unknown_url)
    _assert_development(page)
    _assert_reachable_layout(page)

    _visit_category(page, live_server_url, "Design")
    expect(page.get_by_test_id("experts-card-mrodriguez")).to_be_visible()
    expect(page.get_by_test_id("experts-card-mchen")).to_have_count(0)
    _visit_category(page, live_server_url, "Development")
    _assert_development(page)

    assert [
        list(model.objects.order_by("pk").values()) for model in observed_models
    ] == before, (
        "Browser GETs changed the Experts ledger, profiles, or model interactions"
    )
    assert tuple(mailoutbox) == before_mail, "Browser GETs sent mail"


def _assert_get(page: Page, response: Response | None, url: str) -> None:
    """Verify an exact successful GET and allow the real visual assets to settle.

    :param page: Browser displaying the completed GET. Example: Chromium Page.
    :param response: Actual navigation response. Example: page.reload().
    :param url: Expected unchanged URL. Example: "http://localhost/experts/?category=unrecognized".
    :return: None once the response, location, and fonts are ready.
    :raises AssertionError: If the navigation redirected or returned an error.
    """
    assert response is not None and response.status == HTTPStatus.OK
    assert response.request.method == "GET" and response.request.redirected_from is None
    assert response.url == url
    expect(page).to_have_url(url)
    page.evaluate("() => document.fonts.ready.then(() => true)")


def _assert_category_links(page: Page, current_label: str) -> None:
    """Check real links and the single accessible current category.

    :param page: Browser displaying the list. Example: Chromium Page.
    :param current_label: Expected category name. Example: "Development".
    :return: None once category navigation matches the requested state.
    :raises AssertionError: If link labels, destinations, or current state differ.
    """
    tabs = page.get_by_test_id("experts-category-tabs")
    expect(tabs.get_by_role("link")).to_have_text(list(_CATEGORIES))
    expect(tabs.locator("[aria-current]")).to_have_text([current_label])
    for label in _CATEGORIES:
        link = tabs.get_by_test_id(f"experts-category-{label.lower()}")
        expect(link).to_have_accessible_name(label)
        expect(link).to_have_attribute("href", f"{_CATEGORY_PATH}{label.lower()}")
    expect(tabs.get_by_role("link", name=current_label, exact=True)).to_have_attribute(
        "aria-current", "page"
    )


def _assert_development(page: Page) -> None:
    """Prove the list contains the exact Development cards across all reloads.

    :param page: Browser showing a Development response. Example: Chromium Page.
    :return: None after checking the rank order and formatted totals.
    :raises AssertionError: If any visible category, card, or score differs.
    """
    expect(page.get_by_role("heading", name="Experts", exact=True)).to_be_visible()
    _assert_category_links(page, "Development")
    leaderboard = page.get_by_test_id("experts-leaderboard")
    cards = leaderboard.get_by_role("article")
    expect(cards).to_have_count(len(_DEVELOPMENT_RANKING))
    for index, (username, name, total) in enumerate(_DEVELOPMENT_RANKING):
        card = cards.nth(index)
        expect(card).to_have_attribute("data-testid", f"experts-card-{username}")
        expect(card.get_by_test_id("expert-card-rank")).to_have_text(str(index + 1))
        expect(card.get_by_test_id("expert-card-name")).to_have_text(name)
        expect(card.get_by_test_id("expert-card-karma")).to_have_text(total)
        expect(card.get_by_test_id("expert-card-category")).to_have_text("Development")
    expect(leaderboard.get_by_test_id("experts-card-mrodriguez")).to_have_count(0)


def _visit_category(page: Page, live_server_url: str, label: str) -> None:
    """Follow the actual category link and inspect its HTTP destination.

    :param page: Browser displaying the category links. Example: Chromium Page.
    :param live_server_url: Existing Django origin. Example: "http://localhost:8081".
    :param label: Category link label. Example: "Design".
    :return: None once the destination is selected and ready.
    :raises AssertionError: If the link, HTTP response, or selected category differs.
    """
    url = f"{live_server_url}{_CATEGORY_PATH}{label.lower()}"
    with page.expect_response(url) as navigation:
        page.get_by_test_id(f"experts-category-{label.lower()}").click()
    page.wait_for_load_state("load")
    _assert_get(page, navigation.value, url)
    _assert_category_links(page, label)


def _assert_reachable_layout(page: Page) -> None:
    """Check category wrap and card controls with normal document scrolling.

    :param page: Browser showing the refreshed fallback. Example: Chromium Page.
    :return: None after checking readable text and guest-action reachability.
    :raises AssertionError: If a required control is clipped, covered, or unreachable.
    """
    assert page.evaluate(
        "() => document.documentElement.scrollWidth <= document.documentElement.clientWidth"
    ), "The fallback page scrolls horizontally"
    for test_id in ("experts-guest-login", "experts-guest-register"):
        page.get_by_test_id(test_id).click(trial=True)
    tabs = page.get_by_test_id("experts-category-tabs")
    links = tabs.get_by_role("link").all()
    links[0].focus()
    for index, link in enumerate(links):
        if index:
            page.keyboard.press("Tab")
        expect(link).to_be_focused()
        _assert_readable_text(link)
        link.click(trial=True)
    for username, name, _ in _DEVELOPMENT_RANKING:
        _assert_card_actions(page, username, name)


def _assert_card_actions(page: Page, username: str, name: str) -> None:
    """Verify each recovered card's visible evidence and guest action cluster.

    :param page: Browser showing the fallback leaderboard. Example: Chromium Page.
    :param username: Card identity. Example: "mchen".
    :param name: Display name. Example: "Mike Chen".
    :return: None once the visible controls and keyboard focus work.
    :raises AssertionError: If evidence or either action is clipped or inaccessible.
    """
    card = page.get_by_test_id(f"experts-card-{username}")
    for test_id in (
        "expert-card-rank",
        "expert-card-name",
        "expert-card-karma",
        "expert-card-category",
    ):
        _assert_readable_text(card.get_by_test_id(test_id))
    profile = card.get_by_test_id(f"experts-view-profile-{username}")
    expect(profile).to_have_accessible_name("View profile")
    expect(profile).to_have_attribute("href", f"/experts/{username}/")
    _assert_readable_text(profile)
    profile.click(trial=True)
    contact = card.get_by_test_id(f"experts-reach-out-disabled-{username}")
    expect(contact).to_be_disabled()
    expect(contact).to_have_accessible_name(f"Reach out to {name}")
    expect(card.get_by_role("link")).to_have_count(1)
    explanation = card.get_by_test_id("experts-reach-out-guest-tooltip")
    expect(explanation).to_have_accessible_description(_GUEST_EXPLANATION)
    _assert_readable_text(contact)
    page.keyboard.press("Tab")
    expect(profile).to_be_focused()
    page.keyboard.press("Tab")
    expect(explanation).to_be_focused()


def _assert_readable_text(control: Locator) -> None:
    """Measure rendered line boxes while the control is in the document viewport.

    :param control: Visible text, link, or button. Example: expert-card-karma locator.
    :return: None once the real text lines are visible and unobstructed.
    :raises AssertionError: If the lines extend outside the control or are covered.
    """
    expect(control).to_be_visible()
    assert control.evaluate(
        """(element, tolerance) => {
            element.scrollIntoView({block: 'center', inline: 'nearest', behavior: 'instant'});
            const bounds = element.getBoundingClientRect();
            // Bootstrap's disabled button delegates pointer events to its tooltip wrapper.
            const hitTarget = element.matches('button:disabled') ? element.parentElement : element;
            const text = document.createTreeWalker(element, NodeFilter.SHOW_TEXT);
            const range = document.createRange();
            const lines = [];
            while (text.nextNode()) {
                if (!text.currentNode.textContent.trim()) continue;
                range.selectNodeContents(text.currentNode);
                lines.push(...range.getClientRects());
            }
            return lines.length > 0 && lines.every(line => {
                const y = (line.top + line.bottom) / 2;
                return line.left >= bounds.left - tolerance && line.right <= bounds.right + tolerance &&
                    line.top >= bounds.top - tolerance && line.bottom <= bounds.bottom + tolerance &&
                    [line.left + tolerance, (line.left + line.right) / 2, line.right - tolerance]
                        .every(x => hitTarget.contains(document.elementFromPoint(x, y)));
            });
        }""",
        _LAYOUT_TOLERANCE_PX,
    ), f"Clipped or covered text at {control.get_attribute('data-testid')}"
