"""Actual browser navigation, reload and history proof for EXPERTS-LIST-02."""

from __future__ import annotations

import pytest
from e2e_helpers import login
from playwright.sync_api import Page, expect

from tests.support.experts_data import CEDAR_PASSWORD, CedarDataset

pytestmark = [pytest.mark.e2e, pytest.mark.django_db(transaction=True)]

CATEGORY_LABELS = ["Product", "Development", "Research", "Design", "Other"]


def test_category_navigation_with_reload_and_history_preserves_query(
    page: Page, live_server_url: str, cedar_dataset: CedarDataset
) -> None:
    """Prove category links retain Design through browser reload and history.

    :param page: Existing isolated browser page. Example: Chromium page.
    :param live_server_url: Existing real Django server URL.
        Example: "http://localhost:51327".
    :param cedar_dataset: Real Cedar history with Elena's login account.
    :return: None. Example: actual Design URL and ARIA state verified.
    :raises AssertionError: If navigation, reload or history lose the URL or current link.
    """
    elena = cedar_dataset.users_by_username["esvensson"]
    login(page, live_server_url, elena.username, CEDAR_PASSWORD)
    list_url = f"{live_server_url}/experts/"
    design_url = f"{list_url}?category=design"
    development_url = f"{list_url}?category=development"
    page.goto(list_url)

    tabs = page.get_by_test_id("experts-category-tabs")
    links = tabs.get_by_role("link")
    current_link = links.and_(tabs.locator('[aria-current="page"]'))
    tabs.get_by_test_id("experts-category-design").click()
    expect(page).to_have_url(design_url)
    expect(links).to_have_text(CATEGORY_LABELS)
    expect(current_link).to_have_text(["Design"])

    page.reload()
    expect(page).to_have_url(design_url)
    expect(links).to_have_text(CATEGORY_LABELS)
    expect(current_link).to_have_text(["Design"])

    tabs.get_by_test_id("experts-category-development").click()
    expect(page).to_have_url(development_url)
    expect(current_link).to_have_text(["Development"])
    page.go_back()
    expect(page).to_have_url(design_url)
    expect(current_link).to_have_text(["Design"])
    page.go_forward()
    expect(page).to_have_url(development_url)
    expect(current_link).to_have_text(["Development"])
