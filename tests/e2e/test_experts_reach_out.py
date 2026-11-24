"""S14 production browser destination certification."""

from __future__ import annotations

import pytest
from e2e_helpers import login
from playwright.sync_api import Locator, Page, expect

from methodology.models import ExpertProfile
from tests.support.experts_data import CEDAR_PASSWORD, CedarDataset

MARIA_USERNAME = "mrodriguez"
MARIA_NAME = "Maria Rodriguez"
MARIA_DETAIL_PATH = f"/experts/{MARIA_USERNAME}/"
REACH_OUT_TEST_ID = f"experts-reach-out-{MARIA_USERNAME}"
MARIA_MAILTO = "mailto:maria.rodriguez@example.com"


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
def test_reach_out_with_authenticated_browser_exposes_exact_destination(
    page: Page, live_server_url: str, cedar_dataset: CedarDataset
) -> None:
    """Inspect actual list/detail mailto anchors without opening a mail client.

    :param page: Existing real browser page fixture. Example: fresh Chromium page.
    :param live_server_url: Existing Django live-server URL. Example: localhost.
    :param cedar_dataset: Real imported Cedar history containing Elena and Maria.
    :return: None. Example: both hrefs match and no availability claim appears.
    :raises AssertionError: If navigation, contact actions or public prose differ.
    """
    maria = cedar_dataset.users_by_username[MARIA_USERNAME]
    stored_summary = ExpertProfile.objects.get(user=maria).contribution_summary
    assert stored_summary

    login(page, live_server_url, "esvensson", CEDAR_PASSWORD)
    response = page.goto(f"{live_server_url}/experts/")
    assert response is not None and response.ok
    design_tab = page.get_by_test_id("experts-category-design")
    design_tab.click()
    expect(page).to_have_url(f"{live_server_url}/experts/?category=design")
    expect(design_tab).to_have_attribute("aria-current", "page")
    expect(page.get_by_test_id("user-display")).to_have_text("esvensson")
    maria_card = page.get_by_test_id(f"experts-card-{MARIA_USERNAME}")
    expect(
        maria_card.get_by_role("heading", name=MARIA_NAME, exact=True)
    ).to_be_visible()
    _assert_maria_reach_out(maria_card.get_by_test_id(REACH_OUT_TEST_ID))

    view_profile = maria_card.get_by_test_id(f"experts-view-profile-{MARIA_USERNAME}")
    expect(view_profile).to_have_accessible_name("View profile")
    view_profile.click()
    expect(page).to_have_url(f"{live_server_url}{MARIA_DETAIL_PATH}")
    expect(page.get_by_test_id("expert-name")).to_have_text(MARIA_NAME)
    summary = page.get_by_test_id("expert-contribution-summary")
    expect(summary).to_be_visible()
    assert summary.inner_text() == stored_summary
    expect(summary).to_have_css("-webkit-line-clamp", "none")
    contact_toolbar = page.get_by_role("toolbar", name="Expert contact", exact=True)
    _assert_maria_reach_out(contact_toolbar.get_by_test_id(REACH_OUT_TEST_ID))


def _assert_maria_reach_out(action: Locator) -> None:
    """Require the exact address and discussion wording on a scoped visible link.

    :param action: Maria's Reach out locator in the card or detail toolbar.
    :return: None when the action is a visible, enabled email link.
    :raises AssertionError: If the destination or action text differs.
    """
    expect(action).to_be_visible()
    expect(action).to_be_enabled()
    expect(action).to_have_role("link")
    expect(action).to_have_accessible_name("Reach out")
    expect(action).to_have_text("Reach out")
    expect(action).to_have_attribute("href", MARIA_MAILTO)
    # Bootstrap moves title into data-bs-original-title when it initializes.
    tooltip = action.get_attribute("data-bs-original-title") or action.get_attribute(
        "title"
    )
    assert tooltip == f"Start an email discussion with {MARIA_NAME}"
