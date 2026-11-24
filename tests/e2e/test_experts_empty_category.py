from __future__ import annotations

import re

import pytest
from e2e_helpers import login
from playwright.sync_api import Locator, Page, expect

from tests.support.experts_data import CEDAR_PASSWORD, CedarDataset

OTHER_EMPTY_MESSAGE = "No experts in Other yet — release a playbook to be the first"
LAYOUT_TOLERANCE_PX = 1


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize(
    ("width", "height"),
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
def test_experts_other_with_responsive_viewport_shows_empty_state(
    cedar_dataset: CedarDataset,
    page: Page,
    live_server_url: str,
    width: int,
    height: int,
) -> None:
    """Certify the production empty category at every IA viewport.

    :param cedar_dataset: Real Cedar history and verified accounts, including Elena.
    :param page: Existing isolated browser page. Example: pytest page fixture.
    :param live_server_url: Real Django server origin. Example: "http://localhost:8081".
    :param width: CSS viewport width. Example: 360.
    :param height: CSS viewport height. Example: 800.
    :return: None after visible text, zero cards, current tab and overflow checks.
    :raises AssertionError: If production browser behavior violates the contract.
    """
    page.set_viewport_size({"width": width, "height": height})
    elena = cedar_dataset.users_by_username["esvensson"]
    login(page, live_server_url, elena.username, CEDAR_PASSWORD)
    page.goto(f"{live_server_url}/experts/")

    tabs = page.get_by_test_id("experts-category-tabs")
    other = tabs.get_by_test_id("experts-category-other")
    expect(other).to_have_accessible_name("Other")
    other.click()

    expect(page).to_have_url(f"{live_server_url}/experts/?category=other")
    expect(page.get_by_test_id("user-display")).to_have_text(elena.username)
    expect(other).to_have_attribute("aria-current", "page")
    leaderboard = page.get_by_test_id("experts-leaderboard")
    expect(leaderboard.get_by_test_id(re.compile(r"^experts-card-"))).to_have_count(0)
    message = leaderboard.get_by_test_id("experts-empty")
    expect(message).to_have_text(OTHER_EMPTY_MESSAGE, use_inner_text=True)
    expect(message).to_be_visible()
    page.evaluate("document.fonts.ready")
    assert page.evaluate(
        "document.documentElement.scrollWidth === document.documentElement.clientWidth"
    ), "The Experts page scrolls horizontally"
    _assert_message_is_readable(message)


def _assert_message_is_readable(message: Locator) -> None:
    """Check the actual text line boxes and overlays in the live browser.

    :param message: The rendered Experts empty alert. Example: experts-empty locator.
    :return: None once every line fits and can be read.
    :raises AssertionError: If the viewport clips the message or another element covers it.
    """
    expect(message).to_be_in_viewport(ratio=1)
    problems = message.evaluate(
        """(element, tolerance) => {
            const range = document.createRange();
            range.selectNodeContents(element);
            const bounds = element.getBoundingClientRect();
            return Array.from(range.getClientRects()).flatMap(line => {
                if (line.left < bounds.left - tolerance || line.right > bounds.right + tolerance ||
                    line.top < bounds.top - tolerance || line.bottom > bounds.bottom + tolerance) {
                    return [{clippedLine: line.toJSON(), messageBox: bounds.toJSON()}];
                }
                const y = (line.top + line.bottom) / 2;
                const points = [line.left + tolerance, (line.left + line.right) / 2, line.right - tolerance];
                return points.flatMap(x => {
                    const top = document.elementFromPoint(x, y);
                    return element.contains(top) ? [] : [{
                        x, y, line: line.toJSON(),
                        covering: top?.getAttribute('aria-label') || top?.tagName,
                        coveringBox: top?.getBoundingClientRect().toJSON(),
                    }];
                });
            });
        }""",
        LAYOUT_TOLERANCE_PX,
    )
    assert not problems, f"Empty Other text is clipped or obscured: {problems}"
