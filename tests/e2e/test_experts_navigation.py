from __future__ import annotations

import re

import pytest
from e2e_helpers import login
from playwright.sync_api import Page, expect

from tests.support.experts_data import CEDAR_PASSWORD, CedarDataset


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
def test_experts_navigation_with_sidebar_click_opens_default_page(
    page: Page, live_server_url: str, cedar_dataset: CedarDataset
) -> None:
    """Certify actual login and sidebar navigation to default Experts.

    :param page: Fresh Playwright page. Example: Chromium page at 1280x720.
    :param live_server_url: Real Django server URL. Example: "http://localhost:8081".
    :param cedar_dataset: Real Cedar history and login accounts, including Elena.
    :return: None. Example: None.
    :raises AssertionError: If navigation or rendered default state differs.
    """
    elena = cedar_dataset.users_by_username["esvensson"]
    login(page, live_server_url, elena.username, CEDAR_PASSWORD)
    sidebar = page.get_by_test_id("app-sidebar")
    collaborate = sidebar.get_by_role("list", name="Collaborate", exact=True)
    experts = collaborate.get_by_test_id("nav-experts")
    expect(experts).to_have_text("Experts")
    expect(experts).to_have_attribute("href", "/experts/")
    experts.click()

    expect(page).to_have_url(f"{live_server_url}/experts/")
    expect(page).to_have_title("Experts")
    expect(
        page.get_by_role("heading", name="Experts", level=1, exact=True)
    ).to_be_visible()
    expect(
        page.get_by_text("Top contributors by playbook category", exact=True)
    ).to_be_visible()
    realm_navbar = page.get_by_test_id("realm-navbar")
    expect(realm_navbar.get_by_test_id("user-display")).to_have_text(elena.username)
    expect(experts).to_have_attribute("aria-current", "page")
    expect(experts).to_have_class(re.compile(r"\bactive\b"))
    development = page.get_by_test_id("experts-category-development")
    expect(development).to_have_text("Development")
    expect(development).to_have_attribute("aria-current", "page")

    cards = page.get_by_test_id("experts-leaderboard").get_by_role("article")
    expect(cards).to_have_count(2)
    for position, name in enumerate(("Mike Chen", "Jordan Lee")):
        card = cards.nth(position)
        expect(card.get_by_role("heading", name=name, exact=True)).to_be_visible()
        expect(card.get_by_test_id("expert-card-rank")).to_have_text(str(position + 1))
