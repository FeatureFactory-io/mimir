"""Actual-browser certification of Maria's View profile handoff."""

from __future__ import annotations

from http import HTTPStatus

import pytest
from e2e_helpers import login
from playwright.sync_api import Locator, Page, expect

from methodology.models import ExpertProfile
from tests.support.experts_data import CEDAR_PASSWORD, CedarDataset

_DESIGN_PATH = "/experts/?category=design"
_ELENA_USERNAME = "esvensson"
_MARIA_USERNAME = "mrodriguez"
_MARIA_NAME = "Maria Rodriguez"
_MARIA_PATH = f"/experts/{_MARIA_USERNAME}/"
_MARIA_LINK = f'a[data-testid="experts-view-profile-{_MARIA_USERNAME}"]'
_MARIA_KARMA = "8,200"
_CEDAR_SENTENCE_COUNT = 9


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
def test_maria_profile_handoff_with_browser_click_displays_full_paragraph(
    page: Page, live_server_url: str, cedar_dataset: CedarDataset
) -> None:
    """Click Maria's real control and read her complete stored paragraph.

    :param page: Existing fresh Playwright page. Example: Chromium page.
    :param live_server_url: Live-server origin. Example: "http://localhost:8081".
    :param cedar_dataset: Imported Cedar accounts and independent fixture oracle.
    :return: None. Example: visible summary equals the full Cedar paragraph.
    :raises AssertionError: If the link, response, identity or public prose differs.
    """
    maria = cedar_dataset.users_by_username[_MARIA_USERNAME]
    stored = ExpertProfile.objects.get(user=maria).contribution_summary
    people = cedar_dataset.oracle["people"]
    oracle = {person["username"]: person["summary"] for person in people}
    assert stored == oracle[_MARIA_USERNAME]
    assert stored.count(".") == _CEDAR_SENTENCE_COUNT
    login(page, live_server_url, _ELENA_USERNAME, CEDAR_PASSWORD)
    listing = page.goto(f"{live_server_url}{_DESIGN_PATH}")
    assert listing is not None and listing.status == HTTPStatus.OK
    expect(page.get_by_test_id("user-display")).to_have_text(_ELENA_USERNAME)
    design_tab = page.get_by_test_id("experts-category-design")
    expect(design_tab).to_have_attribute("aria-current", "page")
    card = page.get_by_test_id(f"experts-card-{_MARIA_USERNAME}")
    profile_link = card.locator(_MARIA_LINK)
    expect(profile_link).to_have_accessible_name("View profile")
    expect(profile_link).to_have_attribute("href", _MARIA_PATH)
    _follow_maria_profile(page, profile_link, f"{live_server_url}{_MARIA_PATH}")
    name = page.get_by_test_id("expert-name")
    expect(name.and_(page.get_by_text(_MARIA_NAME, exact=True))).to_be_visible()
    karma = page.locator('[data-testid="expert-karma-total"]:visible')
    expect(karma).to_have_text(_MARIA_KARMA)
    reading = page.get_by_test_id("expert-read-column")
    summary = reading.locator('p[data-testid="expert-contribution-summary"]:visible')
    assert summary.inner_text() == stored
    expect(summary).to_have_css("-webkit-line-clamp", "none")


def _follow_maria_profile(page: Page, profile_link: Locator, detail_url: str) -> None:
    """Verify that clicking Maria's anchor loads the expected document directly.

    :param page: Existing authenticated Chromium page on Design.
    :param profile_link: Maria's rendered View profile anchor.
    :param detail_url: Expected local URL. Example: http://localhost:8081/experts/mrodriguez/.
    :return: None after the clicked link opens the expected URL.
    :raises AssertionError: The response is unsuccessful, redirected or not a document.
    """
    with page.expect_response(detail_url) as navigation:
        profile_link.click()
    detail = navigation.value
    request = detail.request
    assert detail.status == HTTPStatus.OK and request.redirected_from is None
    assert request.method == "GET" and request.resource_type == "document"
    assert request.is_navigation_request() and request.frame == page.main_frame
    expect(page).to_have_url(detail_url)
